#!/usr/bin/env python3
"""Build or verify the complete MB001 product-artifact SHA-256 inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ALLOWED_ROLES = {"canonical_master", "historical_mirror"}
EXPECTED_ROOTS = 19
EXPECTED_FILES = 219
EXPECTED_BYTES = 5_099_728


class InventoryError(ValueError):
    pass


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def git_text(repo: Path, *args: str) -> str:
    return git_bytes(repo, *args).decode("utf-8").strip()


def blob_sha256(repo: Path, blob: str) -> str:
    return hashlib.sha256(git_bytes(repo, "cat-file", "blob", blob)).hexdigest()


def ls_tree_files(repo: Path, commit: str, root: str) -> list[dict[str, object]]:
    raw = git_bytes(repo, "ls-tree", "-r", "-z", "--long", commit, "--", root)
    rows: list[dict[str, object]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        left, path_raw = record.split(b"\t", 1)
        mode, obj_type, blob, size_raw = left.decode("ascii").split()
        if obj_type != "blob" or mode == "160000":
            raise InventoryError(f"unsupported object in product root: {record!r}")
        path = path_raw.decode("utf-8")
        rows.append(
            {
                "relative_path": path,
                "git_blob": blob,
                "bytes": int(size_raw),
                "sha256": blob_sha256(repo, blob),
            }
        )
    return sorted(rows, key=lambda row: str(row["relative_path"]).encode("utf-8"))


def stable_id(runtime_sku: str, relative_path: str) -> str:
    path_id = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16].upper()
    return f"FILE-{runtime_sku.upper()}-{path_id}"


def build_inventory(registry: dict, repo: Path, source_commit: str) -> dict:
    sources = registry.get("product_sources", [])
    if len(sources) != EXPECTED_ROOTS:
        raise InventoryError(f"runtime root count mismatch: {len(sources)} != {EXPECTED_ROOTS}")

    nominated = {
        row["relative_path"]: row
        for row in registry.get("artifacts", [])
        if row.get("role") == "canonical_master"
    }
    files: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()

    for source in sorted(sources, key=lambda row: row["relative_root"].encode("utf-8")):
        root = source["relative_root"]
        tree_sha = git_text(repo, "rev-parse", f"{source_commit}:{root}")
        if tree_sha != source["git_tree_sha"]:
            raise InventoryError(f"root tree drift: {root}: {tree_sha} != {source['git_tree_sha']}")
        rows = ls_tree_files(repo, source_commit, root)
        if len(rows) != int(source["file_count"]):
            raise InventoryError(f"root file-count drift: {root}")
        if sum(int(row["bytes"]) for row in rows) != int(source["bytes"]):
            raise InventoryError(f"root byte-count drift: {root}")

        for facts in rows:
            path = str(facts["relative_path"])
            if path in seen_paths:
                raise InventoryError(f"duplicate path: {path}")
            seen_paths.add(path)
            nominated_row = nominated.get(path)
            if nominated_row:
                registry_id = nominated_row["registry_id"]
                role = "canonical_master"
                nomination_source = nominated_row["nomination_source"]
                content_status = nominated_row["content_status"]
                office_status = nominated_row["office_status"]
                release_status = nominated_row["release_status"]
            else:
                registry_id = stable_id(source["runtime_sku"], path)
                role = "historical_mirror"
                nomination_source = "issue:602"
                content_status = "OPEN"
                office_status = "OPEN"
                release_status = source["release_status"]
            if registry_id in seen_ids:
                raise InventoryError(f"duplicate registry_id: {registry_id}")
            seen_ids.add(registry_id)
            suffix = Path(path).suffix.lower().lstrip(".") or "none"
            files.append(
                {
                    "registry_id": registry_id,
                    "target_sku": source.get("target_sku"),
                    "runtime_sku": source["runtime_sku"],
                    "relative_path": path,
                    "commit": source_commit,
                    "git_blob": facts["git_blob"],
                    "sha256": facts["sha256"],
                    "bytes": facts["bytes"],
                    "format": suffix,
                    "role": role,
                    "nomination_source": nomination_source,
                    "content_status": content_status,
                    "office_status": office_status,
                    "release_status": release_status,
                }
            )

    files.sort(key=lambda row: str(row["relative_path"]).encode("utf-8"))
    total_bytes = sum(int(row["bytes"]) for row in files)
    target_skus = sorted({row["target_sku"] for row in files if row.get("target_sku")})
    if len(files) != EXPECTED_FILES or total_bytes != EXPECTED_BYTES:
        raise InventoryError(
            f"portfolio totals mismatch: files={len(files)} bytes={total_bytes}"
        )
    if len(target_skus) != 13:
        raise InventoryError(f"target SKU count mismatch: {len(target_skus)}")

    return {
        "schema_version": 1,
        "inventory_status": "HASH_SNAPSHOT_NOT_PRODUCT_ACCEPTANCE",
        "source_commit": source_commit,
        "registry_path": "products-storage/ARTIFACT-REGISTRY.json",
        "control_issue": 600,
        "execution_issue": 602,
        "coverage": {
            "target_skus": {"registered": len(target_skus), "expected": 13},
            "runtime_roots": {"registered": len(sources), "expected": EXPECTED_ROOTS},
            "files": {"registered": len(files), "expected": EXPECTED_FILES, "percent": 100.0},
            "bytes": {"registered": total_bytes, "expected": EXPECTED_BYTES},
        },
        "files": files,
    }



def validate_inventory(data: dict, registry: dict) -> None:
    if data.get("schema_version") != 1:
        raise InventoryError("unsupported schema_version")
    files = data.get("files")
    if not isinstance(files, list) or len(files) != EXPECTED_FILES:
        raise InventoryError(f"file count mismatch: {len(files) if isinstance(files, list) else 'invalid'}")
    paths = [row.get("relative_path") for row in files]
    ids = [row.get("registry_id") for row in files]
    if len(paths) != len(set(paths)) or any(not path for path in paths):
        raise InventoryError("missing or duplicate path")
    if len(ids) != len(set(ids)) or any(not registry_id for registry_id in ids):
        raise InventoryError("missing or duplicate registry_id")
    if paths != sorted(paths, key=lambda value: value.encode("utf-8")):
        raise InventoryError("inventory is not deterministically sorted")

    roots = [row["relative_root"] + "/" for row in registry.get("product_sources", [])]
    canonical_paths = {
        row["relative_path"]
        for row in registry.get("artifacts", [])
        if row.get("role") == "canonical_master"
    }
    required = {
        "registry_id", "target_sku", "runtime_sku", "relative_path", "commit",
        "git_blob", "sha256", "bytes", "format", "role", "nomination_source",
        "content_status", "office_status", "release_status",
    }
    for row in files:
        if set(row) != required:
            raise InventoryError(f"row schema drift: {row.get('relative_path')}")
        path = row["relative_path"]
        if path.startswith("tools/reports/"):
            raise InventoryError(f"report path is not a product-root file: {path}")
        if not any(path.startswith(root) for root in roots):
            raise InventoryError(f"path escapes registered roots: {path}")
        if row["role"] not in ALLOWED_ROLES:
            raise InventoryError(f"unknown role: {row['role']}")
        if row["role"] == "canonical_master" and path not in canonical_paths:
            raise InventoryError(f"unregistered canonical role: {path}")
        if row["role"] == "historical_mirror" and path in canonical_paths:
            raise InventoryError(f"canonical path downgraded: {path}")
        if not isinstance(row["bytes"], int) or row["bytes"] < 0:
            raise InventoryError(f"invalid bytes: {path}")
        if not isinstance(row["git_blob"], str) or len(row["git_blob"]) != 40:
            raise InventoryError(f"invalid git blob: {path}")
        if not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
            raise InventoryError(f"invalid sha256: {path}")

    total_bytes = sum(row["bytes"] for row in files)
    target_skus = {row["target_sku"] for row in files if row.get("target_sku")}
    expected_coverage = {
        "target_skus": {"registered": len(target_skus), "expected": 13},
        "runtime_roots": {"registered": len(registry.get("product_sources", [])), "expected": EXPECTED_ROOTS},
        "files": {"registered": len(files), "expected": EXPECTED_FILES, "percent": 100.0},
        "bytes": {"registered": total_bytes, "expected": EXPECTED_BYTES},
    }
    if data.get("coverage") != expected_coverage:
        raise InventoryError("coverage drift")
    if total_bytes != EXPECTED_BYTES:
        raise InventoryError(f"portfolio byte total mismatch: {total_bytes}")


def ensure_matches(actual: dict, expected: dict) -> None:
    if serialized(actual) != serialized(expected):
        raise InventoryError("inventory drift")


def validate_registry_reference(registry: dict, data: dict, text: str) -> None:
    reference = registry.get("file_inventory", {})
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    expected = {
        "path": "products-storage/ARTIFACT-INVENTORY.json",
        "source_commit": data["source_commit"],
        "sha256": digest,
        "files": EXPECTED_FILES,
        "bytes": EXPECTED_BYTES,
    }
    if reference != expected:
        raise InventoryError(f"registry inventory reference drift: {reference} != {expected}")

def serialized(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--registry", default="products-storage/ARTIFACT-REGISTRY.json")
    parser.add_argument("--inventory", default="products-storage/ARTIFACT-INVENTORY.json")
    parser.add_argument("--source-commit")
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    try:
        registry = json.loads((repo / args.registry).read_text(encoding="utf-8"))
        inventory_path = repo / args.inventory
        current = None
        if inventory_path.exists():
            current = json.loads(inventory_path.read_text(encoding="utf-8"))
        source_commit = args.source_commit or (current or {}).get("source_commit")
        if not source_commit:
            raise InventoryError("--source-commit is required before the first snapshot")
        data = build_inventory(registry, repo, source_commit)
        validate_inventory(data, registry)
        text = serialized(data)
        validate_registry_reference(registry, data, text)
        if args.emit:
            print("ARTIFACT_INVENTORY_JSON_BEGIN")
            print(text, end="")
            print("ARTIFACT_INVENTORY_JSON_END")
        elif args.check:
            if current is None:
                raise InventoryError(f"missing inventory: {args.inventory}")
            validate_inventory(current, registry)
            ensure_matches(current, data)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            print(
                f"ARTIFACT_INVENTORY_PASS files={len(data['files'])} "
                f"bytes={data['coverage']['bytes']['registered']} sha256={digest}"
            )
        else:
            atomic_write(inventory_path, text)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            print(
                f"ARTIFACT_INVENTORY_WRITTEN files={len(data['files'])} "
                f"bytes={data['coverage']['bytes']['registered']} sha256={digest}"
            )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, InventoryError) as exc:
        print(f"ARTIFACT_INVENTORY_FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
