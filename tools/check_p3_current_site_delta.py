#!/usr/bin/env python3
"""Exact current P3 exception for immutable 2026-10-12 site snapshots.

The historical reports are never rewritten. Only the nominated P3 tree and
four reviewed HTML/PHP blobs may differ from the accepted source.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "03ce64f607c43bd6a1443ad2d1088c07697c22ba"
SNAPSHOT_ACCEPTED = "181cda7b7a128eb9f5ead1d1bc13a6f87322da77"
NOMINATION_REF = "790ea772fc716d6c322c5f020eb63d01fb93bfed"
NOMINATION_PATH = "tools/candidates/p3-owner-approval-nomination-20261015/nomination.json"
NOMINATION_SHA256 = "9d5cd455167973fa532d512f447b2e02270c6ad636c85f26c6984f6f21105cc8"
ZIP_SHA256 = "955e6e0ee686f5f9e03a0dc8141c021db5667e35f195c3886f630555acd2a5b1"
P3_TREE = "00aca2f4e4163f39e329f4dd14e5b23a813d448e"
P3_BYTES = 397571
P3_ROOT = "products-storage/05-ks-bez-vozvrata"
EXPECTED_HTML_PHP = {
    "download.php": ("public_endpoint", "8c90c5abf5900d1ab7e14d663a584e304fcf9ef8e37a953a4ac5b231e1b6ec55"),
    "products-config.php": ("non_route_module", "1fd10f9d5961432ba5ad5fcffaf22ba36761af0fd49867ab72ca6f184636f299"),
    "products/p3-shablony-ks2-ks3.html": ("indexable_page", "16d576dc3aebe609d6b53ddc7f7bbda5dd2ddaab571ed82582c3a7af90fc067d"),
    "tools/test_delivery_one_hour.php": ("test_fixture", "4bdae0c79bf1336af424d5d0a479b37616b10d910dfb89cc138429b94584d6ef"),
}
HISTORICAL_REPORTS = (
    "tools/reports/site-route-discovery-20261012/report.json",
    "tools/reports/site-static-content-snapshot-20261012/report.json",
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=15)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_blob(path: str) -> bytes:
    data = (ROOT / path).read_bytes()
    if git("show", "HEAD:" + path) != data:
        raise ValueError("working-tree vs HEAD bytes differ: " + path)
    return data


def validate_html_deltas(changed: set[str], hashes: dict[str, str]) -> None:
    expected = set(EXPECTED_HTML_PHP)
    if changed != expected:
        raise ValueError("unapproved HTML/PHP delta: missing=%r extra=%r" %
                         (sorted(expected - changed), sorted(changed - expected)))
    for path, (_, expected_sha) in EXPECTED_HTML_PHP.items():
        if hashes.get(path) != expected_sha:
            raise ValueError("changed or unpinned HTML/PHP blob: " + path)


def validate_registry_projection(baseline: dict, current: dict) -> None:
    """Allow only bytes/tree for the one P3 root; not prices, identities or roles."""
    expected = copy.deepcopy({k: v for k, v in baseline.items() if k != "change_history"})
    actual = {k: v for k, v in current.items() if k != "change_history"}
    roots = [row for row in expected["product_sources"] if row["runtime_sku"] == "p3"]
    if len(roots) != 1:
        raise ValueError("baseline does not identify exactly one P3 root")
    roots[0]["git_tree_sha"] = P3_TREE
    roots[0]["bytes"] = P3_BYTES
    if actual != expected:
        raise ValueError("unapproved product registry identity drift beyond P3 tree/bytes")
    if not any(row["runtime_sku"] == "p3" and
               row["release_status"] == "EXISTING_CATALOG_NOT_TARGET_RELEASE" and
               row["role"] == "historical_mirror"
               for row in current["product_sources"]):
        raise ValueError("P3 historical/non-released identity altered")


def validate_current_p3_delta() -> dict:
    """Read-only acceptance of a pinned scope, never a release acceptance."""
    changed = set(git("diff", "--name-only", BASE, "HEAD", "--", "*.php", "*.html").decode().splitlines())
    fingerprints = {path: sha(checked_blob(path)) for path in EXPECTED_HTML_PHP}
    validate_html_deltas(changed, fingerprints)

    for path in HISTORICAL_REPORTS:
        if checked_blob(path) != git("show", SNAPSHOT_ACCEPTED + ":" + path):
            raise ValueError("historical snapshot mutated: " + path)
    if checked_blob("sitemap.xml") != git("show", BASE + ":sitemap.xml"):
        raise ValueError("historical sitemap changed")

    route = json.loads(checked_blob(HISTORICAL_REPORTS[0]))
    classes = {row["source_path"]: row["route_class"] for row in route["entries"]}
    for path, (kind, _) in EXPECTED_HTML_PHP.items():
        if not path.startswith("tools/") and classes.get(path) != kind:
            raise ValueError("P3 route class differs from historical source: " + path)

    nomination_data = checked_blob(NOMINATION_PATH)
    if sha(nomination_data) != NOMINATION_SHA256 or nomination_data != git("show", NOMINATION_REF + ":" + NOMINATION_PATH):
        raise ValueError("nomination SHA or trusted source changed")
    nomination = json.loads(nomination_data)
    if (nomination.get("runtime_sku") != "p3" or nomination.get("target_sku") != "P3"
            or nomination["candidate_archive"]["sha256"] != ZIP_SHA256
            or nomination["candidate_archive"]["file_count"] != 11
            or nomination["candidate_archive"]["release_status"] != "HOLD"):
        raise ValueError("P3 nomination identity or release gate changed")

    archive_path = nomination["candidate_archive"]["relative_path"]
    archive = checked_blob(archive_path)
    if sha(archive) != ZIP_SHA256:
        raise ValueError("nominated ZIP SHA mismatch")
    members = nomination["member_artifacts"]
    names = [row["member"] for row in members]
    if len(names) != 11 or len(set(names)) != 11 or any("/" in name or "\\" in name or name.startswith(".") for name in names):
        raise ValueError("invalid nominated member inventory")

    actual_root_names = {path.name for path in (ROOT / P3_ROOT).iterdir() if path.is_file()}
    if actual_root_names != set(names) | {"MANIFEST.md"}:
        raise ValueError("P3 runtime root contains missing/extra files")
    with zipfile.ZipFile(ROOT / archive_path) as zip_file:
        if set(zip_file.namelist()) != set(names) or zip_file.testzip() is not None:
            raise ValueError("nominated ZIP inventory or CRC drift")
        for row in members:
            name = row["member"]
            raw = checked_blob(P3_ROOT + "/" + name)
            if sha(raw) != row["sha256"] or len(raw) != row["bytes"] or sha(zip_file.read(name)) != row["sha256"]:
                raise ValueError("nominated buyer member differs: " + name)

    tree = git("rev-parse", "HEAD:" + P3_ROOT).decode().strip()
    if tree != P3_TREE:
        raise ValueError("P3 current Git tree differs from approved candidate")
    baseline = json.loads(git("show", BASE + ":products-storage/ARTIFACT-REGISTRY.json"))
    current = json.loads(checked_blob("products-storage/ARTIFACT-REGISTRY.json"))
    validate_registry_projection(baseline, current)
    if sum(p.stat().st_size for p in (ROOT / P3_ROOT).iterdir() if p.is_file()) != P3_BYTES:
        raise ValueError("P3 root byte count changed")

    return {
        "verdict": "PASS_CURRENT_P3_SITE_DELTA_ONLY",
        "head": git("rev-parse", "HEAD").decode().strip(),
        "historical_snapshot_preserved": True,
        "changed_php_html": {p: {"class": EXPECTED_HTML_PHP[p][0], "sha256": fingerprints[p]}
                             for p in sorted(EXPECTED_HTML_PHP)},
        "candidate_11_of_11": True,
        "current_registry_p3_tree": tree,
        "g4": "OPEN",
        "g8": "HOLD",
        "scope": "Exactly pinned P3 route/registry/ZIP delta; historical reports unchanged; no release",
    }


def main() -> int:
    try:
        print(json.dumps(validate_current_p3_delta(), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, AssertionError, KeyError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print("P3_CURRENT_SITE_DELTA_FAIL " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
