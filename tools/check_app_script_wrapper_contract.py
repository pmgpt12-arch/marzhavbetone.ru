#!/usr/bin/env python3
"""Verify the source-only contract of app-script.php without executing PHP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
from pathlib import Path

EXPECTED_INVENTORY_REPORT_SHA256 = "be4181ebd84b78f2fa83b7feb7df27f7f0bd955faaebf6b1de55cc719c72cf48"
EXPECTED_SOURCES = {
    "app-script.php": {
        "bytes": 239,
        "sha256": "7ba0130cbe199fe0018da9c5cf5794ef35b968906fa6b007d86b8640bd0e5461",
    },
    "app.js": {
        "bytes": 17061,
        "sha256": "365806f60b6cda2c00c93e11d66f653654b75b7e6192dc701c7da56439d6b187",
    },
}
EXPECTED_WRAPPER_LINES = (
    "declare(strict_types=1);",
    "header('Content-Type: application/javascript; charset=UTF-8');",
    "header('Cache-Control: no-cache, no-store, must-revalidate');",
    "header('Pragma: no-cache');",
    "header('Expires: 0');",
    "readfile(__DIR__ . '/app.js');",
)
FORBIDDEN_CONSTRUCTS = (
    "$_GET",
    "$_POST",
    "$_REQUEST",
    "$_SERVER",
    "$_ENV",
    "getenv(",
    "curl_",
    "file_put_contents(",
    "fwrite(",
    "unlink(",
    "rename(",
    "include ",
    "require ",
    "eval(",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def execution_environment() -> dict[str, str]:
    names = (
        "EVIDENCE_HEAD_SHA",
        "GITHUB_SHA",
        "GITHUB_REF",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
    )
    return {name.lower(): os.environ[name] for name in names if os.environ.get(name)}


def source_record(path: Path, root: Path) -> dict:
    payload = path.read_bytes()
    expected = EXPECTED_SOURCES[path.relative_to(root).as_posix()]
    actual = {"bytes": len(payload), "sha256": sha256_bytes(payload)}
    if actual != expected:
        raise ValueError(
            f"source fingerprint changed for {path.relative_to(root).as_posix()}: "
            f"{actual!r}, expected {expected!r}"
        )
    return {"path": path.relative_to(root).as_posix(), **actual}


def nonblank_wrapper_lines(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "<?php":
        raise ValueError("wrapper must begin with <?php")
    return tuple(line.strip() for line in lines[1:] if line.strip())


def verify_wrapper(text: str) -> dict:
    lines = nonblank_wrapper_lines(text)
    if lines != EXPECTED_WRAPPER_LINES:
        raise ValueError(f"wrapper statement contract changed: {lines!r}")
    forbidden = [needle for needle in FORBIDDEN_CONSTRUCTS if needle.lower() in text.lower()]
    if forbidden:
        raise ValueError(f"forbidden wrapper constructs: {forbidden!r}")
    physical = text.splitlines()
    delegation_line = next(
        index for index, line in enumerate(physical, start=1) if "readfile(" in line
    )
    header_lines = [
        index for index, line in enumerate(physical, start=1) if line.strip().startswith("header(")
    ]
    return {
        "strict_types": True,
        "header_count": len(header_lines),
        "header_lines": header_lines,
        "delegation": {"target": "app.js", "line": delegation_line},
        "forbidden_construct_count": 0,
    }


def build_report(root: Path, inventory_report_sha256: str) -> dict:
    if inventory_report_sha256 != EXPECTED_INVENTORY_REPORT_SHA256:
        raise ValueError(
            f"inventory lineage changed: {inventory_report_sha256}, "
            f"expected {EXPECTED_INVENTORY_REPORT_SHA256}"
        )
    sources = [source_record(root / name, root) for name in EXPECTED_SOURCES]
    wrapper_text = (root / "app-script.php").read_text(encoding="utf-8")
    return {
        "schema_version": 1,
        "status": "PASS_WRAPPER_SOURCE_CONTRACT_ONLY",
        "execution_environment": execution_environment(),
        "lineage": {"accepted_inventory_report_sha256": inventory_report_sha256},
        "sources": sources,
        "wrapper_contract": verify_wrapper(wrapper_text),
        "acceptance_limits": {
            "source_wrapper_contract_accepted": True,
            "http_runtime_equivalence_accepted": False,
            "php_configuration_accepted": False,
            "cache_behavior_accepted": False,
            "reachability_accepted": False,
            "security_accepted": False,
            "deploy_accepted": False,
            "publication_accepted": False,
            "delivery_accepted": False,
            "release_accepted": False,
        },
    }


def build_manifest(report: dict) -> dict:
    return {
        "schema_version": 1,
        "status": report["status"],
        "lineage": report.get("lineage"),
        "sources": report.get("sources", []),
        "wrapper_contract": report.get("wrapper_contract"),
    }


def write_evidence(output: Path, report: dict) -> None:
    atomic_json(output / "report.json", report)
    atomic_json(output / "manifest.json", build_manifest(report))
    receipt = {
        "status": report["status"],
        "report_sha256": sha256_bytes((output / "report.json").read_bytes()),
        "manifest_sha256": sha256_bytes((output / "manifest.json").read_bytes()),
        "checkpoint_policy": "verified_only",
        "endpoint_execution": False,
        "model_calls": 0,
        "paid_api_calls": 0,
    }
    atomic_json(output / "receipt.json", receipt)


def interrupted(signum: int, _frame: object) -> None:
    raise InterruptedError(f"signal {signum}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--inventory-report-sha256",
        default=EXPECTED_INVENTORY_REPORT_SHA256,
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    previous_handlers = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.signal(signum, interrupted)
    try:
        report = build_report(root, args.inventory_report_sha256)
        write_evidence(output, report)
    except BaseException as error:
        failure = {
            "schema_version": 1,
            "status": "FAIL_NOT_VERIFIED",
            "error": {"class": type(error).__name__, "message": str(error)},
            "execution_environment": execution_environment(),
            "lineage": {"accepted_inventory_report_sha256": args.inventory_report_sha256},
            "sources": [],
            "wrapper_contract": None,
            "acceptance_limits": {
                "source_wrapper_contract_accepted": False,
                "http_runtime_equivalence_accepted": False,
                "php_configuration_accepted": False,
                "cache_behavior_accepted": False,
                "reachability_accepted": False,
                "security_accepted": False,
                "deploy_accepted": False,
                "publication_accepted": False,
                "delivery_accepted": False,
                "release_accepted": False,
            },
        }
        write_evidence(output, failure)
        print(json.dumps(failure["error"], ensure_ascii=False))
        return 2
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    print(json.dumps({"status": report["status"], "sources": len(report["sources"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
