#!/usr/bin/env python3
"""Build a read-only source/client inventory for excluded dynamic endpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

EXPECTED_REPORT_SHA256 = "029e2d0763775a05afd8f6fa86c01a6c9fe94af67e597602e4b3779edfaeecbb"
EXPECTED_ENDPOINTS = (
    "app-script.php",
    "check-payment.php",
    "contact.php",
    "download.php",
    "event.php",
    "get/index.php",
    "ig-webhook.php",
    "lead.php",
    "payment.php",
    "webhook.php",
)
CLASSIFICATION = {
    "app-script.php": "render_dependency",
    "check-payment.php": "payment_status",
    "contact.php": "contact_intake",
    "download.php": "download_delivery",
    "event.php": "telemetry",
    "get/index.php": "download_delivery",
    "ig-webhook.php": "webhook",
    "lead.php": "lead_intake",
    "payment.php": "payment_initiation",
    "webhook.php": "webhook",
}
INDICATORS = {
    "environment_access": ("getenv(", "$_ENV", "$_SERVER"),
    "request_input": ("$_GET", "$_POST", "php://input"),
    "response_header": ("header(",),
    "filesystem_write": ("file_put_contents(", "fwrite(", "unlink(", "rename("),
    "filesystem_read": ("readfile(", "file_get_contents(", "fopen("),
    "outbound_http": ("curl_", "file_get_contents('http", 'file_get_contents("http'),
    "email": ("mail(",),
    "database": ("PDO(", "mysqli_"),
    "signature_check": ("hash_hmac(", "signature", "сигнатур"),
}
TEXT_SUFFIXES = {".html", ".htm", ".js", ".php", ".css", ".json", ".md"}


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


def validate_source_report(raw: bytes) -> dict:
    digest = sha256_bytes(raw)
    if digest != EXPECTED_REPORT_SHA256:
        raise ValueError(f"source report SHA256 {digest}, expected {EXPECTED_REPORT_SHA256}")
    report = json.loads(raw)
    endpoints = tuple(report.get("excluded_dynamic_endpoints", ()))
    if endpoints != EXPECTED_ENDPOINTS:
        raise ValueError(f"dynamic endpoint set/order changed: {endpoints!r}")
    return report


def source_indicators(text: str) -> dict[str, list[int]]:
    lines = text.splitlines()
    result: dict[str, list[int]] = {}
    for name, needles in INDICATORS.items():
        matched = [
            number
            for number, line in enumerate(lines, start=1)
            if any(needle.lower() in line.lower() for needle in needles)
        ]
        if matched:
            result[name] = matched
    return result


def infer_method(lines: list[str], line_index: int) -> str:
    window = "\n".join(lines[max(0, line_index - 5):line_index + 6]).lower()
    if "method" in window and "post" in window:
        return "POST"
    if "method" in window and "put" in window:
        return "PUT"
    return "UNSPECIFIED"


def client_call_sites(root: Path, endpoints: tuple[str, ...]) -> list[dict]:
    endpoint_set = set(endpoints)
    sites = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if relative in endpoint_set or relative.startswith("tools/reports/"):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines):
            for endpoint in endpoints:
                if endpoint in line:
                    sites.append({
                        "endpoint": endpoint,
                        "source_path": relative,
                        "line": index + 1,
                        "method": infer_method(lines, index),
                    })
    return sites


def build_inventory(root: Path, source_report_path: Path) -> dict:
    raw = source_report_path.read_bytes()
    validate_source_report(raw)
    endpoints = []
    for relative in EXPECTED_ENDPOINTS:
        path = root / relative
        payload = path.read_bytes()
        text = payload.decode("utf-8")
        endpoints.append({
            "path": relative,
            "classification": CLASSIFICATION[relative],
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "static_indicators": source_indicators(text),
        })
    return {
        "schema_version": 1,
        "status": "PASS_SOURCE_INVENTORY_ONLY",
        "source_report": {
            "path": source_report_path.relative_to(root).as_posix(),
            "sha256": sha256_bytes(raw),
        },
        "counts": {
            "endpoints": len(endpoints),
            "client_call_sites": 0,
        },
        "endpoints": endpoints,
        "client_call_sites": [],
        "acceptance_limits": {
            "source_inventory_accepted": True,
            "runtime_behavior_accepted": False,
            "payment_accepted": False,
            "webhook_accepted": False,
            "security_accepted": False,
            "legal_accepted": False,
            "deploy_accepted": False,
            "release_accepted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    source_report = args.source_report if args.source_report.is_absolute() else root / args.source_report
    output = args.output if args.output.is_absolute() else root / args.output
    report = build_inventory(root, source_report)
    sites = client_call_sites(root, EXPECTED_ENDPOINTS)
    report["client_call_sites"] = sites
    report["counts"]["client_call_sites"] = len(sites)
    atomic_json(output / "report.json", report)
    receipt = {
        "status": report["status"],
        "report_sha256": sha256_bytes((output / "report.json").read_bytes()),
        "checkpoint_policy": "verified_only",
        "model_calls": 0,
        "paid_api_calls": 0,
    }
    atomic_json(output / "receipt.json", receipt)
    print(json.dumps(report["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
