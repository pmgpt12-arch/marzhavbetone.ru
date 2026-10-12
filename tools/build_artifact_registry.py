#!/usr/bin/env python3
"""Validate or refresh the MB001 artifact registry from an exact git checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EXPECTED_TARGETS = {"P1", "P2", "P3", "P4", "P5+P12", "P7", "P8", "P9", "P10", "P11", "P13", "T2", "T3"}
ALLOWED_ROLES = {"canonical_master", "nominated_candidate", "historical_mirror", "report_evidence_not_nominated"}


class RegistryError(ValueError):
    pass


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def root_facts(repo: Path, rel: str) -> dict[str, object]:
    tree_sha = git(repo, "rev-parse", f"HEAD:{rel}")
    output = git(repo, "ls-tree", "-r", "--long", "HEAD", "--", rel)
    rows = [line for line in output.splitlines() if line]
    sizes = []
    for row in rows:
        left, _path = row.split("\t", 1)
        size = left.split()[3]
        sizes.append(int(size) if size != "-" else 0)
    return {"git_tree_sha": tree_sha, "file_count": len(rows), "bytes": sum(sizes)}


def validate_shape(data: dict) -> None:
    if data.get("schema_version") != 1:
        raise RegistryError("unsupported schema_version")
    roles = set(data.get("allowed_roles", []))
    if roles != ALLOWED_ROLES:
        raise RegistryError("allowed_roles drift")
    targets = {row.get("target_sku") for row in data.get("product_sources", []) if row.get("target_sku")}
    if targets != EXPECTED_TARGETS:
        raise RegistryError(f"target coverage mismatch: {sorted(targets ^ EXPECTED_TARGETS)}")
    runtime = [row.get("runtime_sku") for row in data.get("product_sources", [])]
    if len(runtime) != len(set(runtime)):
        raise RegistryError("duplicate runtime_sku")
    ids = [row.get("registry_id") for row in data.get("artifacts", [])]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise RegistryError("missing or duplicate registry_id")
    for row in [*data.get("product_sources", []), *data.get("artifacts", [])]:
        if row.get("role") not in ALLOWED_ROLES:
            raise RegistryError(f"invalid role: {row.get('role')}")
    for artifact in data.get("artifacts", []):
        rel = artifact.get("relative_path", "")
        role = artifact.get("role")
        if role == "canonical_master" and not rel.startswith("products-storage/"):
            raise RegistryError(f"canonical artifact outside products-storage: {rel}")
        if rel.startswith("tools/reports/") and role not in {"nominated_candidate", "report_evidence_not_nominated"}:
            raise RegistryError(f"report artifact has executable role: {rel}")
        if role == "report_evidence_not_nominated":
            if artifact.get("release_status") != "BLOCKED" or artifact.get("content_status") != "NOT_NOMINATED":
                raise RegistryError(f"non-nominated report must fail closed: {rel}")


def reconcile(data: dict, repo: Path, check: bool) -> bool:
    changed = False
    head = git(repo, "rev-parse", "HEAD")
    if head != data["generated_from_commit"]:
        raise RegistryError(f"checkout {head} != registry commit {data['generated_from_commit']}")
    for source in data["product_sources"]:
        actual = root_facts(repo, source["relative_root"])
        for key, value in actual.items():
            if source.get(key) != value:
                if check:
                    raise RegistryError(f"source drift {source['runtime_sku']} {key}: {source.get(key)} != {value}")
                source[key] = value
                changed = True
    for artifact in data["artifacts"]:
        if artifact["commit"] != head:
            continue
        path = repo / artifact["relative_path"]
        if not path.is_file():
            raise RegistryError(f"missing artifact: {artifact['relative_path']}")
        actual = {
            "git_blob": git(repo, "hash-object", artifact["relative_path"]),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for key, value in actual.items():
            if artifact.get(key) != value:
                if check:
                    raise RegistryError(f"artifact drift {artifact['registry_id']} {key}: {artifact.get(key)} != {value}")
                artifact[key] = value
                changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="products-storage/ARTIFACT-REGISTRY.json")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    registry = (repo / args.registry).resolve()
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        validate_shape(data)
        changed = reconcile(data, repo, args.check)
        if changed:
            registry.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, RegistryError) as exc:
        print(f"ARTIFACT_REGISTRY_FAIL: {exc}", file=sys.stderr)
        return 1
    print("ARTIFACT_REGISTRY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
