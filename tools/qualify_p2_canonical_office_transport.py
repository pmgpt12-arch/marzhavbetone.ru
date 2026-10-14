#!/usr/bin/env python3
"""Qualify transport and OOXML container integrity for two nominated P2 DOCX files.

This deliberately does not inspect document meaning, layout, legal correctness, or
native Microsoft Word behaviour.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


try:
    from tools.build_artifact_registry import registry_identity_sha256
except ModuleNotFoundError:
    from build_artifact_registry import registry_identity_sha256

EXPECTED_REGISTRY_IDENTITY_SHA256 = '0c13befa31baeef2638408053b65ae59ee5133d325cba00b5a09d3571cc56483'

STATUS_PASS = "PASS_TRANSPORT_AND_CONTAINER_INTEGRITY_ONLY"
STATUS_FAIL = "FAIL_NOT_VERIFIED"
REQUIRED_MEMBERS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
    "word/styles.xml",
    "docProps/core.xml",
    "docProps/app.xml",
}
FORBIDDEN_MEMBERS = {"EncryptedPackage", "EncryptionInfo", "word/vbaProject.bin"}
REGISTRY_PATH = "products-storage/ARTIFACT-REGISTRY.json"
EXPECTED_REGISTRY_BLOB = "5a431138f4d157ed42fbd6ff034c40c515c4422b"
INPUTS = (
    {
        "registry_id": "P2-CANON-00-INSTR-B85",
        "path": "products-storage/02-dopraboty-bez-poter/00-INSTRUKCIYA.docx",
        "nomination_commit": "b85a2e716d501cbc54c840f58027ecfd6a60964b",
        "bytes": 41800,
        "sha256": "a27ffb94bb47a66743fe01d188055813159a04117d09514db8f8aeef9c14f609",
        "git_blob": "6e7b67117feedb7d978c5971f142b5782fc097c8",
    },
    {
        "registry_id": "P2-CANON-03-UVD-B85",
        "path": "products-storage/02-dopraboty-bez-poter/03-uvedomlenie-o-doprabotah.docx",
        "nomination_commit": "b85a2e716d501cbc54c840f58027ecfd6a60964b",
        "bytes": 38881,
        "sha256": "7360634f99b3b7f288c394bc88140cc84f92d6a0a2786b7816d8c2bc23a5ae16",
        "git_blob": "e5f82e0d1220c82aaecd990cc011b7c0ca974491",
    },
)


def expected_registry_record(spec: dict[str, object]) -> dict[str, object]:
    return {
        "registry_id": spec["registry_id"],
        "target_sku": "P2",
        "runtime_sku": "p2",
        "relative_path": spec["path"],
        "commit": spec["nomination_commit"],
        "git_blob": spec["git_blob"],
        "sha256": spec["sha256"],
        "bytes": spec["bytes"],
        "format": "docx",
        "role": "canonical_master",
        "nomination_source": "issue:600",
        "content_status": "OPEN",
        "office_status": "OPEN",
        "release_status": "OPEN",
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def qualify_registry(root: Path) -> dict[str, object]:
    path = root / REGISTRY_PATH
    data = path.read_bytes()
    actual_blob = git_blob_sha1(data)
    registry = json.loads(data)
    if actual_blob != EXPECTED_REGISTRY_BLOB and registry_identity_sha256(registry) != EXPECTED_REGISTRY_IDENTITY_SHA256:
        raise ValueError("registry identity mismatch outside separately validated change_history")
    if registry.get("registry_status") != "ACTIVE_PARTIAL_SEED":
        raise ValueError(f"registry status mismatch: {registry.get('registry_status')}")
    artifacts = registry.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("registry artifacts must be a list")
    nominated = [
        item for item in artifacts
        if isinstance(item, dict) and item.get("target_sku") == "P2" and item.get("role") == "canonical_master"
    ]
    expected = [expected_registry_record(spec) for spec in INPUTS]
    if nominated != expected:
        raise ValueError("registry P2 canonical_master records do not exactly match the accepted nomination contract")
    return {
        "relative_path": REGISTRY_PATH,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "git_blob": actual_blob,
        "registry_status": registry["registry_status"],
        "record_count": len(nominated),
        "record_ids": [item["registry_id"] for item in nominated],
        "status": "PASS",
    }


def checked_out_head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


def qualify_docx(root: Path, spec: dict[str, object]) -> dict[str, object]:
    path = root / str(spec["path"])
    data = path.read_bytes()
    actual = {
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "git_blob": git_blob_sha1(data),
    }
    for key in ("bytes", "sha256", "git_blob"):
        if actual[key] != spec[key]:
            raise ValueError(f"{spec['registry_id']} {key} mismatch: {actual[key]} != {spec[key]}")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"{spec['registry_id']} duplicate ZIP members: {duplicates}")
        missing = sorted(REQUIRED_MEMBERS.difference(names))
        if missing:
            raise ValueError(f"{spec['registry_id']} missing OOXML members: {missing}")
        forbidden = sorted(FORBIDDEN_MEMBERS.intersection(names))
        if forbidden:
            raise ValueError(f"{spec['registry_id']} forbidden members: {forbidden}")
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"{spec['registry_id']} corrupt ZIP member: {bad_member}")
        xml_members = sorted(name for name in names if name.endswith((".xml", ".rels")))
        for name in xml_members:
            ElementTree.fromstring(archive.read(name))

    return {
        "registry_id": spec["registry_id"],
        "relative_path": spec["path"],
        "nomination_commit": spec["nomination_commit"],
        "expected": {key: spec[key] for key in ("bytes", "sha256", "git_blob")},
        "actual": actual,
        "zip_member_count": len(names),
        "xml_member_count": len(xml_members),
        "required_members_present": sorted(REQUIRED_MEMBERS),
        "duplicate_members": [],
        "forbidden_members_present": [],
        "zip_crc_check": "PASS",
        "xml_well_formed_check": "PASS",
        "status": "PASS",
    }


def write_evidence(out_dir: Path, report: dict[str, object], exit_code: int) -> None:
    report_bytes = canonical_json_bytes(report)
    atomic_write(out_dir / "report.json", report_bytes)
    manifest = {
        "schema_version": 1,
        "status": report["status"],
        "artifacts": {
            "report.json": {"bytes": len(report_bytes), "sha256": sha256_bytes(report_bytes)},
        },
    }
    manifest_bytes = canonical_json_bytes(manifest)
    atomic_write(out_dir / "manifest.json", manifest_bytes)
    exit_bytes = f"{exit_code}\n".encode()
    atomic_write(out_dir / "exit.code", exit_bytes)
    receipt = {
        "schema_version": 1,
        "status": report["status"],
        "checkpoint_policy": "verified_only",
        "hash_chain": {
            "report.json": sha256_bytes(report_bytes),
            "manifest.json": sha256_bytes(manifest_bytes),
            "exit.code": sha256_bytes(exit_bytes),
        },
        "model_calls": 0,
        "paid_api_calls": 0,
        "source_files_modified": 0,
    }
    atomic_write(out_dir / "receipt.json", canonical_json_bytes(receipt))


def run(root: Path, out_dir: Path, expected_head: str | None = None) -> int:
    started = datetime.now(timezone.utc).isoformat()
    report: dict[str, object] = {
        "schema_version": 1,
        "unit": "mb001-p2-canonical-office-transport-qualification-20261012",
        "status": STATUS_FAIL,
        "started_at": started,
        "checkpoint_policy": "verified_only",
        "source_nomination": {
            "registry": REGISTRY_PATH,
            "expected_registry_git_blob": EXPECTED_REGISTRY_BLOB,
            "registry_status": "ACTIVE_PARTIAL_SEED",
            "nomination_source": "issue:600",
            "record_count": 2,
        },
        "execution": {
            "github_event_sha": os.environ.get("GITHUB_SHA"),
            "checked_out_head": None,
            "expected_head": expected_head,
            "python": sys.version.split()[0],
            "model_calls": 0,
            "paid_api_calls": 0,
        },
        "checks": [],
        "acceptance": {
            "exact_registry_nomination_accepted": False,
            "github_binary_transport_accepted": False,
            "docx_container_integrity_accepted": False,
            "content_accepted": False,
            "legal_accepted": False,
            "native_word_accepted": False,
            "visual_accepted": False,
            "source_replacement_accepted": False,
            "deploy_accepted": False,
            "publication_accepted": False,
            "delivery_accepted": False,
            "release_accepted": False,
        },
        "limitations": [
            "transport and OOXML container integrity only",
            "no content, legal, visual, native Word, source replacement, deploy, publication, delivery, or release acceptance",
        ],
    }
    exit_code = 1
    try:
        if len(INPUTS) != 2 or len({item["registry_id"] for item in INPUTS}) != 2:
            raise ValueError("input contract must contain exactly two unique nominated records")
        registry_check = qualify_registry(root)
        report["registry_check"] = registry_check
        actual_head = checked_out_head(root) if expected_head else None
        execution = report["execution"]
        assert isinstance(execution, dict)
        execution["checked_out_head"] = actual_head
        if expected_head and expected_head != actual_head:
            raise ValueError(f"exact-head mismatch: {actual_head} != {expected_head}")
        report["checks"] = [qualify_docx(root, spec) for spec in INPUTS]
        report["status"] = STATUS_PASS
        acceptance = report["acceptance"]
        assert isinstance(acceptance, dict)
        acceptance["exact_registry_nomination_accepted"] = True
        acceptance["github_binary_transport_accepted"] = True
        acceptance["docx_container_integrity_accepted"] = True
        exit_code = 0
    except BaseException as exc:
        report["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_evidence(out_dir, report, exit_code)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--expected-head")
    args = parser.parse_args()
    return run(args.root.resolve(), args.out_dir.resolve(), args.expected_head)


if __name__ == "__main__":
    raise SystemExit(main())
