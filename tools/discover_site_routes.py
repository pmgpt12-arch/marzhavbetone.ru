#!/usr/bin/env python3
"""Build the deterministic route-discovery evidence for issue #603.

This is deliberately narrower than SITE-CONTENT-REGISTRY.json: it proves
which HTML/PHP blobs are public routes and which are not.  Rendered and
visible-content hashes remain a later gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "tools/reports/site-route-discovery-20261012/report.json"
SOURCE_COMMIT = "7fb747f73589c40b4b5a84b0b5a09e088456f095"
SOURCE_TREE = "78ca0c05ff23fb5bd298ae38c1143bd78710fa63"
SNAPSHOT_DATE = "2026-10-14"

SUPPORTING_PAGES = {"404.html", "fail.html", "success.html", "test-pokupka.html"}
PUBLIC_ENDPOINTS = {
    "app-script.php", "check-payment.php", "contact.php", "download.php",
    "event.php", "get/index.php", "ig-webhook.php", "lead.php",
    "payment.php", "webhook.php",
}
NON_ROUTE_MODULES = {"config.php", "products-config.php", "mvb_funnel.php"}
CLI_ONLY = {"mvb_funnel_health.php"}


class DiscoveryError(RuntimeError):
    pass


def git(*args: str, text: bool = True) -> str | bytes:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=text, timeout=30
    )
    if proc.returncode:
        raise DiscoveryError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def source_files(commit: str) -> dict[str, dict[str, object]]:
    raw = git("ls-tree", "-r", "-z", "--long", commit, text=False)
    assert isinstance(raw, bytes)
    result: dict[str, dict[str, object]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, path_b = record.split(b"\t", 1)
        mode, kind, sha, size = meta.decode().split()
        path = path_b.decode("utf-8")
        if kind == "blob" and path.endswith((".html", ".php")):
            result[path] = {"blob_sha": sha, "bytes": int(size), "mode": mode}
    return result


def assert_head_candidates_match_source(
    source: dict[str, dict[str, object]], head: dict[str, dict[str, object]]
) -> None:
    def fingerprint(files: dict[str, dict[str, object]]) -> dict[str, tuple[object, ...]]:
        return {
            path: (meta["blob_sha"], meta["bytes"], meta["mode"])
            for path, meta in files.items()
        }
    if fingerprint(source) != fingerprint(head):
        missing = sorted(set(source) - set(head))
        extra = sorted(set(head) - set(source))
        changed = sorted(
            path for path in set(source) & set(head)
            if fingerprint(source)[path] != fingerprint(head)[path]
        )
        raise DiscoveryError(
            f"HEAD candidate drift: missing={missing}, extra={extra}, changed={changed}"
        )


def read_source(commit: str, path: str) -> bytes:
    out = git("show", f"{commit}:{path}", text=False)
    assert isinstance(out, bytes)
    return out


def assert_source_tree(commit: str) -> None:
    actual = str(git("rev-parse", f"{commit}^{{tree}}")).strip()
    if actual != SOURCE_TREE:
        raise DiscoveryError(f"source tree drift: expected={SOURCE_TREE}, actual={actual}")


def assert_control_input_equal(name: str, source: bytes, head: bytes) -> None:
    if source != head:
        raise DiscoveryError(f"HEAD control-input drift: {name}")


def sitemap_routes(xml_bytes: bytes) -> dict[str, str]:
    root = ET.fromstring(xml_bytes)
    routes: dict[str, str] = {}
    for node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
        loc = node.findtext("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if not loc or not loc.startswith("https://marzhavbetone.ru/"):
            raise DiscoveryError(f"unexpected sitemap URL: {loc!r}")
        route = loc.removeprefix("https://marzhavbetone.ru")
        path = "index.html" if route == "/" else route.lstrip("/")
        if route.endswith("/") and route != "/":
            path += "index.html"
        if path in routes:
            raise DiscoveryError(f"duplicate sitemap source: {path}")
        routes[path] = route
    return routes


def classify(path: str, indexed: dict[str, str]) -> tuple[str, str | None, str]:
    if path in indexed:
        return "indexable_page", indexed[path], "canonical_live_candidate"
    if path in SUPPORTING_PAGES:
        return "supporting_page", "/" + path, "supporting_page"
    if path in PUBLIC_ENDPOINTS:
        route = "/get/" if path == "get/index.php" else "/" + path
        return "public_endpoint", route, "supporting_page"
    if path in NON_ROUTE_MODULES:
        return "non_route_module", None, "not_public_route"
    if path in CLI_ONLY:
        return "cli_only", None, "not_public_route"
    if path.startswith("tools/") and path.endswith(".php"):
        return "test_fixture", None, "not_public_route"
    raise DiscoveryError(f"unclassified HTML/PHP candidate: {path}")


def stable_id(path: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "-" for ch in path.lower())
    return "route-" + "-".join(part for part in normalized.split("-") if part)


def validate_entries(entries: list[dict[str, object]], candidates: set[str]) -> None:
    paths = [str(e["source_path"]) for e in entries]
    if len(paths) != len(set(paths)):
        raise DiscoveryError("duplicate source_path")
    ids = [str(e["route_registry_id"]) for e in entries]
    if len(ids) != len(set(ids)):
        raise DiscoveryError("duplicate route_registry_id")
    if set(paths) != candidates:
        missing = sorted(candidates - set(paths))
        extra = sorted(set(paths) - candidates)
        raise DiscoveryError(f"coverage drift: missing={missing}, extra={extra}")
    routes = [str(e["public_route"]) for e in entries if e["public_route"] is not None]
    if len(routes) != len(set(routes)):
        raise DiscoveryError("duplicate public_route")


def build_report(commit: str = SOURCE_COMMIT) -> dict[str, object]:
    assert_source_tree(commit)
    files = source_files(commit)
    assert_head_candidates_match_source(files, source_files("HEAD"))
    source_sitemap = read_source(commit, "sitemap.xml")
    assert_control_input_equal(
        "sitemap.xml", source_sitemap, read_source("HEAD", "sitemap.xml")
    )
    indexed = sitemap_routes(source_sitemap)
    missing = sorted(set(indexed) - set(files))
    if missing:
        raise DiscoveryError(f"sitemap source missing: {missing}")
    entries: list[dict[str, object]] = []
    for path in sorted(files):
        route_class, route, role = classify(path, indexed)
        meta = files[path]
        entries.append({
            "route_registry_id": stable_id(path),
            "source_path": path,
            "source_commit": commit,
            "source_blob": meta["blob_sha"],
            "source_bytes": meta["bytes"],
            "route_class": route_class,
            "public_route": route,
            "role": role,
            "dependency_discovery_status": (
                "pending_full_content_snapshot" if route is not None else "not_applicable"
            ),
        })
    validate_entries(entries, set(files))
    counts: dict[str, int] = {}
    for entry in entries:
        key = str(entry["route_class"])
        counts[key] = counts.get(key, 0) + 1
    public_count = sum(1 for e in entries if e["public_route"] is not None)
    return {
        "schema_version": 1,
        "scope": "route_discovery_only",
        "source_commit": commit,
        "source_tree": SOURCE_TREE,
        "snapshot_date": SNAPSHOT_DATE,
        "candidate_extensions": [".html", ".php"],
        "candidate_count": len(entries),
        "sitemap_route_count": len(indexed),
        "public_route_count": public_count,
        "non_route_count": len(entries) - public_count,
        "counts_by_class": dict(sorted(counts.items())),
        "acceptance_limits": {
            "content_accepted": False,
            "render_accepted": False,
            "legal_accepted": False,
            "deploy_accepted": False,
            "release_accepted": False,
        },
        "entries": entries,
    }


def encoded(report: dict[str, object]) -> bytes:
    return (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        data = encoded(build_report())
        digest = hashlib.sha256(data).hexdigest()
        if args.check:
            current = REPORT.read_bytes()
            if current != data:
                raise DiscoveryError("report drift")
            print(f"SITE_ROUTE_DISCOVERY_PASS candidates=117 public=98 sha256={digest}")
            return 0
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        tmp = REPORT.with_suffix(".tmp")
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            import os
            os.fsync(fh.fileno())
        tmp.replace(REPORT)
        dir_fd = __import__("os").open(REPORT.parent, __import__("os").O_DIRECTORY)
        try:
            __import__("os").fsync(dir_fd)
        finally:
            __import__("os").close(dir_fd)
        print(f"SITE_ROUTE_DISCOVERY_WRITTEN candidates=117 public=98 sha256={digest}")
        return 0
    except Exception as exc:
        print(f"SITE_ROUTE_DISCOVERY_FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
