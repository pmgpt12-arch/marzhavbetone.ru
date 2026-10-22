#!/usr/bin/env python3
"""Exact current P3 exception for immutable 2026-10-12 site snapshots.

The historical reports are never rewritten. Only the nominated P3 tree and
its nine pinned price/route HTML/PHP blobs may differ from the accepted source.
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
    "diagnostika.html": ("indexable_page", "4faab63d319cc30492ae4c72e6f361a36ad9089ffb96a2cacb1410cbfc325c76"),
    "articles/proverka-ks-2-pered-sdachey.html": ("indexable_page", "77f39ba3fff5e81113fe5c57172be894411db4503ed5252ab3156888c5d674ec"),
    "articles/raboty-ne-prinyaty.html": ("indexable_page", "e17ea3d20bf70b328e080e96747142591e8d35cc07a726143370bf1552bf1100"),
    "index.html": ("indexable_page", "79b3f3461075fd2e93151752aee067f6875b101103d91e4e29165cf041fc1d12"),
    "katalog.html": ("indexable_page", "caa6dc33b5024ecc2232a4d066af3c3d055d23d44e82a096f0ec0850e95e3e0d"),
    "download.php": ("public_endpoint", "8c90c5abf5900d1ab7e14d663a584e304fcf9ef8e37a953a4ac5b231e1b6ec55"),
    "products-config.php": ("non_route_module", "b38d78f0f58a68c48f414684ff90eb6796f7ddabf6de78ebc6af1ade6ff6191f"),
    "products/p3-shablony-ks2-ks3.html": ("indexable_page", "bfc2eff2d5d4be76d110a8362fc57586096fdce4ea99011fd79167f5d6828e31"),
    "tools/test_delivery_one_hour.php": ("test_fixture", "4bdae0c79bf1336af424d5d0a479b37616b10d910dfb89cc138429b94584d6ef"),
}
HISTORICAL_REPORTS = (
    "tools/reports/site-route-discovery-20261012/report.json",
    "tools/reports/site-static-content-snapshot-20261012/report.json",
)

# A separately verified staging point, not a production release. Keep the
# historic P3 exception below intact; it cannot describe later site work.
CUSTOMER_ROUTE_SOURCE = "046e47009147b892b9efa87ed1c3e3136fd42ab5"
CUSTOMER_ROUTE_BASE = "c7e32ecc7ad5d8d4b0a3e425ccfe8eeccafe8433"


def verify_staging_source_scope(root: Path, reference: str) -> int:
    """Reject any public/product drift from a pinned Git object, including dirty files."""
    def run(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], timeout=15)

    def relevant(path):
        return not path.startswith(("tools/", ".github/", ".codex/"))

    def tree(ref):
        rows = run("ls-tree", "-r", "-z", "--full-tree", ref).split(b"\0")
        return {p.decode(): meta.decode() for row in rows if row
                for meta, p in [row.split(b"\t", 1)] if relevant(p.decode())}

    run("merge-base", "--is-ancestor", reference, "HEAD")
    expected, actual = tree(reference), tree("HEAD")
    if expected != actual:
        changed = sorted(p for p in expected.keys() | actual.keys()
                         if expected.get(p) != actual.get(p))
        raise ValueError("unreviewed staging source delta: " + repr(changed))
    dirty = [p for p in run("diff", "--name-only", "HEAD").decode().splitlines() if relevant(p)]
    extra = [p for p in run("ls-files", "--others", "--exclude-standard", "--",
                           "*.php", "*.html", "*.css", "*.js").decode().splitlines() if relevant(p)]
    if dirty or extra:
        raise ValueError("unreviewed staging worktree: " + repr(sorted(dirty + extra)))
    return len(expected)


def validate_current_customer_route_delta() -> dict:
    count = verify_staging_source_scope(ROOT, CUSTOMER_ROUTE_SOURCE)
    protected = ["payment.php", "webhook.php", "download.php", "lead.php",
                 "products-config.php", "config.php", ".htaccess", "products-storage", "downloads"]
    if git("diff", "--name-only", CUSTOMER_ROUTE_BASE, CUSTOMER_ROUTE_SOURCE, "--", *protected).strip():
        raise ValueError("staging reference changed protected payment/product source")
    # Neither a commit nor a dirty worktree may rewrite the old evidence.
    if git("diff", "--name-only", CUSTOMER_ROUTE_SOURCE, "HEAD", "--", "tools/reports").strip():
        raise ValueError("historical report tree changed")
    if git("diff", "--name-only", "HEAD", "--", "tools/reports").strip():
        raise ValueError("historical report worktree changed")
    return {"verdict": "PASS_PINNED_CUSTOMER_ROUTE_STAGING_ONLY",
            "head": git("rev-parse", "HEAD").decode().strip(),
            "source_ref": CUSTOMER_ROUTE_SOURCE, "source_paths": count,
            "historical_snapshot_preserved": True, "protected_product_payment_source_unchanged": True,
            "release_accepted": False, "publication_accepted": False}


def validate_known_site_delta() -> dict:
    try:
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
                        CUSTOMER_ROUTE_SOURCE, "HEAD"], check=True,
                       capture_output=True, timeout=15)
    except subprocess.CalledProcessError:
        return validate_current_p3_delta()
    return validate_current_customer_route_delta()


def staging_wrapper_sources(root: Path) -> tuple[dict, dict]:
    if root.resolve() != ROOT.resolve():
        raise ValueError("staging source scope requires this repository root")
    receipt = validate_current_customer_route_delta()
    expected = {}
    for name in ("app-script.php", "app.js"):
        raw = git("show", CUSTOMER_ROUTE_SOURCE + ":" + name)
        expected[name] = {"bytes": len(raw), "sha256": sha(raw)}
    return expected, receipt


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
        print(json.dumps(validate_known_site_delta(), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, AssertionError, KeyError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print("P3_CURRENT_SITE_DELTA_FAIL " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
