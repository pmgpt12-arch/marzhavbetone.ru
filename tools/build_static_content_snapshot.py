#!/usr/bin/env python3
"""Build the deterministic static HTML source snapshot for issue #603.

The snapshot is intentionally source-bound.  It hashes accepted static HTML
and the local render dependencies those pages reference.  It does not claim
browser-render, substantive-content, legal, deploy, or release acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "tools/reports/site-static-content-snapshot-20261012/report.json"
RECEIPT = ROOT / "tools/reports/site-static-content-snapshot-20261012/receipt.json"
ROUTE_REPORT = ROOT / "tools/reports/site-route-discovery-20261012/report.json"
ARTIFACT_REGISTRY = ROOT / "products-storage/ARTIFACT-REGISTRY.json"

CONTENT_SOURCE_COMMIT = "03ce64f607c43bd6a1443ad2d1088c07697c22ba"
CONTENT_SOURCE_TREE = "e9a7e8cb6cbf91f1a1c21c5e0cf468970d70c5e4"
ACCEPTED_DISCOVERY_MERGE = "4c93fe4ae680c88f2ca82a65ec6fd380b0248af6"
ROUTE_REPORT_BLOB = "5f779a82995515b3a2b1c687771823c82439130d"
ROUTE_REPORT_SHA256 = "37febeca4e5c6c8a4f21e5d7ec1534b5fe61bd8a9ba994cd93bc0bf7e71933cb"
ARTIFACT_REGISTRY_BLOB = "5a431138f4d157ed42fbd6ff034c40c515c4422b"
ARTIFACT_REGISTRY_SHA256 = "080238747ee7e32fe72efaa9a62f911f670ad76354f0e972482a8fa4602195fc"
SNAPSHOT_DATE = "2026-10-12"
CANONICAL_EXCEPTIONS = ["404.html", "fail.html", "success.html", "test-pokupka.html"]

ATTR_RE = re.compile(
    r"""([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>\x60]+))"""
)
ENTITY_RE = re.compile(r"&(#x?[0-9a-f]+|amp|nbsp);", re.I)
BLOCK_RE = re.compile(
    r"<(script|style|template|noscript|svg)\b[\s\S]*?</\1\s*>", re.I
)


class SnapshotError(RuntimeError):
    pass


def git(*args: str, text: bool = True, check: bool = True) -> str | bytes:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=text, timeout=30
    )
    if check and proc.returncode:
        err = proc.stderr.strip() if text else proc.stderr.decode(errors="replace").strip()
        raise SnapshotError(err or f"git {' '.join(args)} failed")
    return proc.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_tree(commit: str) -> dict[str, dict[str, object]]:
    raw = git("ls-tree", "-r", "-z", "--long", commit, text=False)
    assert isinstance(raw, bytes)
    out: dict[str, dict[str, object]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, path_b = record.split(b"\t", 1)
        mode, kind, blob, size = meta.decode().split()
        if kind == "blob":
            out[path_b.decode()] = {
                "mode": mode, "blob": blob, "bytes": int(size)
            }
    return out


def read_source(commit: str, path: str) -> bytes:
    raw = git("show", f"{commit}:{path}", text=False)
    assert isinstance(raw, bytes)
    return raw


def assert_accepted_ancestry() -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ACCEPTED_DISCOVERY_MERGE, "HEAD"],
        cwd=ROOT, capture_output=True, timeout=30
    )
    if proc.returncode:
        raise SnapshotError("HEAD is not descended from accepted route-discovery merge")


def assert_pinned_input(path: Path, expected_blob: str, expected_sha256: str) -> bytes:
    data = path.read_bytes()
    rel = path.relative_to(ROOT).as_posix()
    blob = str(git("rev-parse", f"HEAD:{rel}")).strip()
    if blob != expected_blob:
        raise SnapshotError(f"pinned input blob drift: {rel}")
    if sha256(data) != expected_sha256:
        raise SnapshotError(f"pinned input SHA-256 drift: {rel}")
    return data


def decode_entity(match: re.Match[str]) -> str:
    token = match.group(1).lower()
    if token == "amp":
        return "&"
    if token == "nbsp":
        return "\u00a0"
    if token.startswith("#x"):
        return chr(int(token[2:], 16))
    return chr(int(token[1:], 10))


def normalize_visible(fragment: str) -> str:
    value = re.sub(r"<!--[\s\S]*?-->", " ", fragment)
    value = BLOCK_RE.sub(" ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = ENTITY_RE.sub(decode_entity, value)
    value = unicodedata.normalize("NFC", value)
    return re.sub(r"\s+", " ", value).strip()


def attributes(tag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag):
        out[match.group(1).lower()] = next(
            value for value in match.groups()[1:] if value is not None
        )
    return out


def resolve_dependency(url: str, source_path: str) -> tuple[str, str | None]:
    if not url or re.match(r"^(?:data:|#|mailto:|tel:|javascript:)", url, re.I):
        return "ignore", None
    value = url.strip()
    if re.match(r"^https?://", value, re.I):
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if host != "marzhavbetone.ru" and not host.endswith(".marzhavbetone.ru"):
            return "external", value
        value = parsed.path
    value = value.split("#", 1)[0].split("?", 1)[0]
    if not value:
        return "ignore", None
    base = source_path.rsplit("/", 1)[0] + "/" if "/" in source_path else ""
    parts: list[str] = []
    for part in (value[1:] if value.startswith("/") else base + value).split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not parts:
                raise SnapshotError(f"dependency escapes repository root: {source_path}: {url}")
            parts.pop()
        else:
            parts.append(part)
    return "local", "/".join(parts)


def analyze_html(source_path: str, html: str) -> dict[str, object]:
    title_match = re.search(r"<title\b[^>]*>([\s\S]*?)</title>", html, re.I)
    title = normalize_visible(title_match.group(1)) if title_match else None
    h1 = [
        normalize_visible(match.group(1))
        for match in re.finditer(r"<h1\b[^>]*>([\s\S]*?)</h1>", html, re.I)
    ]
    canonical = None
    for match in re.finditer(r"<link\b[^>]*>", html, re.I):
        attrs = attributes(match.group(0))
        if "canonical" in attrs.get("rel", "").lower().split() and attrs.get("href"):
            canonical = attrs["href"]
            break

    sku_counts: dict[str, int] = {}
    sku_re = re.compile(
        r"""\bdata-sku\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))""", re.I
    )
    for match in sku_re.finditer(html):
        sku = next(value for value in match.groups() if value is not None).strip()
        sku_counts[sku] = sku_counts.get(sku, 0) + 1

    local: set[str] = set()
    external: set[str] = set()
    for match in re.finditer(r"<(link|script|img|source)\b[^>]*>", html, re.I):
        kind = match.group(1).lower()
        attrs = attributes(match.group(0))
        urls: list[str] = []
        if kind == "link":
            rel = attrs.get("rel", "").lower().split()
            if any(token in {"stylesheet", "icon", "preload", "modulepreload"} for token in rel):
                if attrs.get("href"):
                    urls = [attrs["href"]]
        elif kind == "script" and attrs.get("src"):
            urls = [attrs["src"]]
        elif kind == "img" and attrs.get("src"):
            urls = [attrs["src"]]
        elif kind == "source":
            if attrs.get("src"):
                urls.append(attrs["src"])
            if attrs.get("srcset"):
                urls.extend(
                    item.strip().split()[0]
                    for item in attrs["srcset"].split(",") if item.strip()
                )
        for url in urls:
            disposition, resolved = resolve_dependency(url, source_path)
            if disposition == "local" and resolved is not None:
                local.add(resolved)
            elif disposition == "external" and resolved is not None:
                external.add(resolved)

    visible = normalize_visible(html)
    return {
        "title": title,
        "h1": h1,
        "canonical": canonical,
        "sku_counts": dict(sorted(sku_counts.items())),
        "local": sorted(local),
        "external": sorted(external),
        "visible": visible,
    }


def validate_skus(bindings: dict[str, int], valid_skus: set[str]) -> None:
    unknown = sorted(set(bindings) - valid_skus)
    if unknown:
        raise SnapshotError(f"unknown runtime SKU bindings: {unknown}")


def validate_exact_paths(actual: set[str], expected: set[str], label: str) -> None:
    if actual != expected:
        raise SnapshotError(
            f"{label} drift: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def validate_canonical(path: str, route_class: str, canonical: str | None) -> None:
    if route_class == "indexable_page" and not canonical:
        raise SnapshotError(f"indexable page lacks canonical: {path}")
    if route_class == "supporting_page":
        expected_missing = path in CANONICAL_EXCEPTIONS
        if expected_missing != (canonical is None):
            raise SnapshotError(f"supporting canonical exception drift: {path}")


def build_report() -> dict[str, object]:
    assert_accepted_ancestry()
    actual_tree = str(git("rev-parse", f"{CONTENT_SOURCE_COMMIT}^{{tree}}")).strip()
    if actual_tree != CONTENT_SOURCE_TREE:
        raise SnapshotError("content source tree drift")

    route_bytes = assert_pinned_input(
        ROUTE_REPORT, ROUTE_REPORT_BLOB, ROUTE_REPORT_SHA256
    )
    registry_bytes = assert_pinned_input(
        ARTIFACT_REGISTRY, ARTIFACT_REGISTRY_BLOB, ARTIFACT_REGISTRY_SHA256
    )
    route_report = json.loads(route_bytes)
    registry = json.loads(registry_bytes)
    if route_report["source_commit"] != CONTENT_SOURCE_COMMIT:
        raise SnapshotError("route-report source commit drift")
    if route_report["source_tree"] != CONTENT_SOURCE_TREE:
        raise SnapshotError("route-report source tree drift")

    entries = sorted(
        (
            entry for entry in route_report["entries"]
            if entry["route_class"] in {"indexable_page", "supporting_page"}
        ),
        key=lambda entry: entry["source_path"],
    )
    if len(entries) != 88:
        raise SnapshotError(f"static page count drift: {len(entries)}")
    if len({entry["source_path"] for entry in entries}) != len(entries):
        raise SnapshotError("duplicate static source path")
    if len({entry["route_registry_id"] for entry in entries}) != len(entries):
        raise SnapshotError("duplicate route registry id")
    if len({entry["public_route"] for entry in entries}) != len(entries):
        raise SnapshotError("duplicate static public route")

    source_meta = source_tree(CONTENT_SOURCE_COMMIT)
    valid_skus = sorted({
        item["runtime_sku"] for item in registry["product_sources"]
        if item.get("runtime_sku")
    })
    valid_sku_set = set(valid_skus)
    pages: list[dict[str, object]] = []
    dependency_refs: dict[str, set[str]] = {}
    all_external: set[str] = set()

    for entry in entries:
        path = entry["source_path"]
        raw = read_source(CONTENT_SOURCE_COMMIT, path)
        meta = source_meta.get(path)
        if not meta:
            raise SnapshotError(f"static source missing: {path}")
        if meta["blob"] != entry["source_blob"] or meta["bytes"] != entry["source_bytes"]:
            raise SnapshotError(f"route/source fingerprint drift: {path}")
        head_raw = (ROOT / path).read_bytes()
        if head_raw != raw:
            raise SnapshotError(f"HEAD static source drift: {path}")

        html = raw.decode("utf-8")
        info = analyze_html(path, html)
        validate_skus(info["sku_counts"], valid_sku_set)
        validate_canonical(path, entry["route_class"], info["canonical"])
        for dependency in info["local"]:
            dependency_refs.setdefault(dependency, set()).add(path)
        all_external.update(info["external"])
        visible = info["visible"]
        pages.append({
            "route_registry_id": entry["route_registry_id"],
            "public_route": entry["public_route"],
            "route_class": entry["route_class"],
            "role": entry["role"],
            "source_path": path,
            "source_commit": entry["source_commit"],
            "source_blob": entry["source_blob"],
            "source_bytes": entry["source_bytes"],
            "source_sha256": sha256(raw),
            "normalized_visible_sha256": sha256(visible.encode()),
            "normalized_visible_bytes": len(visible.encode()),
            "normalized_visible_words": len(visible.split()) if visible else 0,
            "title": info["title"],
            "h1": info["h1"],
            "canonical": info["canonical"],
            "canonical_exception": info["canonical"] is None,
            "cta_sku_bindings": info["sku_counts"],
            "local_dependency_paths": info["local"],
            "external_dependency_urls": info["external"],
        })

    dependencies: list[dict[str, object]] = []
    for path in sorted(dependency_refs):
        meta = source_meta.get(path)
        if not meta:
            raise SnapshotError(f"local dependency missing from source tree: {path}")
        raw = read_source(CONTENT_SOURCE_COMMIT, path)
        if len(raw) != meta["bytes"]:
            raise SnapshotError(f"dependency size drift: {path}")
        head_path = ROOT / path
        if not head_path.is_file() or head_path.read_bytes() != raw:
            raise SnapshotError(f"HEAD dependency drift: {path}")
        dependencies.append({
            "path": path,
            "source_commit": CONTENT_SOURCE_COMMIT,
            "source_blob": meta["blob"],
            "source_bytes": meta["bytes"],
            "source_sha256": sha256(raw),
            "referenced_by": sorted(dependency_refs[path]),
        })

    excluded = sorted(
        entry["source_path"] for entry in route_report["entries"]
        if entry["route_class"] == "public_endpoint"
    )
    counts = {
        "static_pages": len(pages),
        "indexable_pages": sum(p["route_class"] == "indexable_page" for p in pages),
        "supporting_pages": sum(p["route_class"] == "supporting_page" for p in pages),
        "local_dependencies": len(dependencies),
        "external_dependencies": len(all_external),
        "cta_sku_occurrences": sum(
            sum(page["cta_sku_bindings"].values()) for page in pages
        ),
        "unknown_skus": 0,
    }
    if counts != {
        "static_pages": 88,
        "indexable_pages": 84,
        "supporting_pages": 4,
        "local_dependencies": 63,
        "external_dependencies": 0,
        "cta_sku_occurrences": 47,
        "unknown_skus": 0,
    }:
        raise SnapshotError(f"snapshot count drift: {counts}")

    return {
        "schema_version": 1,
        "status": "PASS_STATIC_SOURCE_SNAPSHOT_ONLY",
        "scope": "accepted_static_html_source_and_local_render_dependencies",
        "snapshot_date": SNAPSHOT_DATE,
        "lineage": {
            "accepted_route_discovery_merge_commit": ACCEPTED_DISCOVERY_MERGE,
            "content_source_commit": CONTENT_SOURCE_COMMIT,
            "content_source_tree": CONTENT_SOURCE_TREE,
            "route_report": {
                "path": ROUTE_REPORT.relative_to(ROOT).as_posix(),
                "git_blob": ROUTE_REPORT_BLOB,
                "sha256": ROUTE_REPORT_SHA256,
            },
            "artifact_registry": {
                "path": ARTIFACT_REGISTRY.relative_to(ROOT).as_posix(),
                "git_blob": ARTIFACT_REGISTRY_BLOB,
                "sha256": ARTIFACT_REGISTRY_SHA256,
            },
        },
        "counts": counts,
        "normalization_contract": {
            "version": 1,
            "operations": [
                "remove HTML comments",
                "remove script/style/template/noscript/svg blocks",
                "strip remaining tags",
                "decode numeric plus amp/nbsp entities",
                "Unicode NFC",
                "collapse Unicode whitespace",
            ],
            "non_operations": [
                "no price removal",
                "no CTA removal",
                "no title/H1/canonical removal",
                "no link or structured-data rewriting",
            ],
        },
        "valid_runtime_skus": valid_skus,
        "canonical_exceptions": CANONICAL_EXCEPTIONS,
        "excluded_dynamic_endpoints": excluded,
        "acceptance_limits": {
            "static_source_snapshot_accepted": True,
            "browser_render_accepted": False,
            "substantive_content_quality_accepted": False,
            "legal_accepted": False,
            "deploy_accepted": False,
            "release_accepted": False,
        },
        "pages": pages,
        "dependencies": dependencies,
    }


def encoded(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def build_receipt(report: dict[str, object], report_sha: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "PASS_STATIC_SOURCE_SNAPSHOT_ONLY",
        "report_path": REPORT.relative_to(ROOT).as_posix(),
        "report_sha256": report_sha,
        "source_commit": CONTENT_SOURCE_COMMIT,
        "accepted_route_discovery_merge_commit": ACCEPTED_DISCOVERY_MERGE,
        "counts": report["counts"],
        "model_calls": 0,
        "paid_api_calls": 0,
        "next_step": (
            "independent review, exact-head CI, then browser-render confirmation "
            "as a separate unit"
        ),
        "acceptance_limits": report["acceptance_limits"],
    }


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report()
        report_data = encoded(report)
        report_sha = sha256(report_data)
        receipt_data = encoded(build_receipt(report, report_sha))
        if args.check:
            if REPORT.read_bytes() != report_data:
                raise SnapshotError("report drift")
            if RECEIPT.read_bytes() != receipt_data:
                raise SnapshotError("receipt drift")
            print(
                "SITE_STATIC_CONTENT_SNAPSHOT_PASS "
                f"pages=88 dependencies=63 sha256={report_sha}"
            )
            return 0
        atomic_write(REPORT, report_data)
        atomic_write(RECEIPT, receipt_data)
        print(
            "SITE_STATIC_CONTENT_SNAPSHOT_WRITTEN "
            f"pages=88 dependencies=63 sha256={report_sha}"
        )
        return 0
    except Exception as exc:
        print(f"SITE_STATIC_CONTENT_SNAPSHOT_FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
