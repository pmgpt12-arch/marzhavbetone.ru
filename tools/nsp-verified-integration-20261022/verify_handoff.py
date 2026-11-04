#!/usr/bin/env python3
"""Read-only checks for the exact NSP handoff. Does not copy, deploy or resave products.
Python standard library only. Exit 0: requested checks passed. Exit 2: blocked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

MAX_FILE_BYTES = 20 * 1024 * 1024

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def blob_digest(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def classify(raw: bytes | None, item: dict) -> str:
    if raw is None:
        return "MISSING_RECONCILE"
    sha = digest(raw)
    if sha == item["accepted_sha256"]:
        return "ALREADY_ACCEPTED"
    if sha == item["previous_sha256"]:
        return "KNOWN_PREVIOUS_VERSION"
    return "DIVERGED_RECONCILE"

def safe_local(root: Path, rel: str) -> Path:
    pp = PurePosixPath(rel)
    if pp.is_absolute() or ".." in pp.parts:
        raise ValueError("Unsafe relative path: " + rel)
    base = root.resolve()
    path = (base / Path(*pp.parts)).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Path leaves root: " + rel)
    return path

def read_local(root: Path, rel: str) -> bytes | None:
    p = safe_local(root, rel)
    if not p.is_file():
        return None
    if p.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Unexpected file size: " + rel)
    return p.read_bytes()

def git_read(repo: Path, ref: str, rel: str) -> bytes:
    if not ref or ref.startswith("-"):
        raise ValueError("Invalid git ref")
    p = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{rel}"],
                       capture_output=True, timeout=12, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"Cannot read {ref}:{rel}; {p.stderr.decode(errors='replace')[:300]}")
    if len(p.stdout) > MAX_FILE_BYTES:
        raise ValueError("Unexpected git object size: " + rel)
    return p.stdout

def validate_source(raw: bytes | None, item: dict) -> bool:
    return (raw is not None and len(raw) == item["bytes"]
            and digest(raw) == item["accepted_sha256"]
            and blob_digest(raw) == item["accepted_git_blob"])

def self_test() -> dict:
    old, accepted = b"prior-version", b"accepted-version"
    item = dict(previous_sha256=digest(old), accepted_sha256=digest(accepted),
                accepted_git_blob=blob_digest(accepted), bytes=len(accepted))
    tests = [classify(old, item) == "KNOWN_PREVIOUS_VERSION",
             classify(accepted, item) == "ALREADY_ACCEPTED",
             classify(None, item) == "MISSING_RECONCILE",
             classify(accepted + b"changed", item) == "DIVERGED_RECONCILE",
             validate_source(accepted, item), not validate_source(old, item),
             not validate_source(None, item)]
    if not all(tests):
        raise AssertionError("Self-test failed")
    return {"self_test": "PASS", "checks": len(tests), "source_files_modified": False}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=Path(__file__).with_name("MANIFEST_VERIFIED_FILES.json"))
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--repo", type=Path, help="Read the pinned Git objects; no checkout or fetch is performed")
    src.add_argument("--source-root", type=Path, help="Read an existing byte-identical accepted snapshot")
    ap.add_argument("--target-root", type=Path, help="Inspect an existing workspace; it is never modified")
    ap.add_argument("--target-ref", help="Inspect a Git ref, with --repo, instead of a workspace")
    ap.add_argument("--phase", choices=("before", "after"), default="before")
    ap.add_argument("--sku", action="append", help="Limit target/archive checks to P5, P8, P9 or P11")
    ap.add_argument("--zip", action="append", default=[], metavar="SKU=PATH", help="Check only listed replacements inside an existing buyer ZIP")
    ap.add_argument("--report", type=Path, help="Optional JSON evidence file; use a QA folder, not a product path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        print(json.dumps(self_test()))
        return 0
    if not (args.repo or args.source_root):
        ap.error("Supply --repo or --source-root")
    if args.target_ref and (not args.repo or args.target_root):
        ap.error("--target-ref requires --repo and cannot be combined with --target-root")
    if args.phase == "after" and not (args.target_root or args.target_ref or args.zip):
        ap.error("--phase after requires a target or archive")
    m = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = m["files"]
    if len(entries) != 13 or len({i['path'] for i in entries}) != 13:
        raise ValueError("Manifest scope is not the fixed 13-file handoff")
    selected = set(args.sku or m["counts_by_sku"])
    if not selected <= set(m["counts_by_sku"]):
        raise ValueError("Unknown SKU")
    rows, errors, zips = [], [], []
    for item in entries:
        rel = item["path"]
        raw = git_read(args.repo, m["source_commit"], rel) if args.repo else read_local(args.source_root, rel)
        ok = validate_source(raw, item)
        row = {"sku": item["sku"], "path": rel, "source_exact": ok}
        if not ok:
            errors.append("SOURCE_MISMATCH: " + rel)
        if item["sku"] in selected and (args.target_root or args.target_ref):
            target = (git_read(args.repo, args.target_ref, rel) if args.target_ref
                      else read_local(args.target_root, rel))
            state = classify(target, item)
            row["target_state"] = state
            permitted = ("ALREADY_ACCEPTED",) if args.phase == "after" else ("ALREADY_ACCEPTED", "KNOWN_PREVIOUS_VERSION")
            if state not in permitted:
                errors.append("TARGET_" + state + ": " + rel)
        rows.append(row)
    for spec in args.zip:
        sku, sep, path = spec.partition("=")
        if not sep or sku not in selected:
            raise ValueError("Expected selected SKU=archive-path")
        matching = [i for i in entries if i["sku"] == sku]
        with zipfile.ZipFile(path) as z:
            crc_error = z.testzip()
            if crc_error:
                errors.append("ZIP_CRC: " + crc_error)
            members = [n for n in z.namelist() if not n.endswith("/")]
            for item in matching:
                found = [n for n in members if PurePosixPath(n.replace('\\', '/')).name == item["filename"]]
                if len(found) != 1:
                    errors.append(f"ZIP_MISSING_OR_DUPLICATE: {sku}:{item['filename']}")
                    continue
                info = z.getinfo(found[0])
                if info.file_size > MAX_FILE_BYTES:
                    raise ValueError("Oversized ZIP member")
                raw = z.read(info)
                ok = validate_source(raw, item)
                zips.append({"sku": sku, "archive": path, "member": found[0], "exact": ok})
                if not ok:
                    errors.append("ZIP_CONTENT_MISMATCH: " + found[0])
    result = {"status": "PASS" if not errors else "BLOCKED", "phase": args.phase,
              "source_commit": m["source_commit"], "source_files_checked": len(rows),
              "rows": rows, "archives": zips, "errors": errors, "read_only": True,
              "scope": "Exact replacement bytes only. Not acceptance of complete products, legal completeness, all archive members or deployment."}
    out = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        if 'products-storage' in args.report.parts:
            raise ValueError("Write reports to a QA directory, not products-storage")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(out, encoding="utf-8")
    print(out)
    return 0 if not errors else 2

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc), "read_only": True}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
