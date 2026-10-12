#!/usr/bin/env python3
"""Verify app-script.php over a bounded localhost-only PHP HTTP server."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
from typing import Iterable


EXPECTED_PREDECESSOR_REPORT_SHA256 = "bea20349ede3700a51bd155b745ea2bc9749de2e35762105d0fd6474e6e8341a"
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
EXPECTED_HEADERS = {
    "content-type": "application/javascript; charset=UTF-8",
    "cache-control": "no-cache, no-store, must-revalidate",
    "pragma": "no-cache",
    "expires": "0",
}
REQUEST_COUNT = 2


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
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


def atomic_json(path: Path, value: object) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    atomic_bytes(path, payload)


def execution_environment() -> dict[str, str]:
    names = (
        "EVIDENCE_HEAD_SHA",
        "GITHUB_SHA",
        "GITHUB_REF",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
    )
    return {name.lower(): os.environ[name] for name in names if os.environ.get(name)}


def verify_lineage(value: str) -> None:
    if value != EXPECTED_PREDECESSOR_REPORT_SHA256:
        raise ValueError(
            f"predecessor report changed: {value}, expected {EXPECTED_PREDECESSOR_REPORT_SHA256}"
        )


def verify_sources(root: Path) -> tuple[list[dict], bytes]:
    records = []
    for name, expected in EXPECTED_SOURCES.items():
        payload = (root / name).read_bytes()
        actual = {"bytes": len(payload), "sha256": sha256_bytes(payload)}
        if actual != expected:
            raise ValueError(f"source fingerprint changed for {name}: {actual!r}, expected {expected!r}")
        records.append({"path": name, **actual})
    return records, (root / "app.js").read_bytes()


def normalized_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, value in headers:
        key = name.lower()
        if key in result:
            raise ValueError(f"duplicate response header: {key}")
        result[key] = value.strip()
    return result


def validate_http_sample(
    index: int,
    status: int,
    headers: Iterable[tuple[str, str]],
    body: bytes,
    expected_body: bytes,
) -> dict:
    if status != 200:
        raise ValueError(f"request {index} status changed: {status}, expected 200")
    actual_headers = normalized_headers(headers)
    for name, expected in EXPECTED_HEADERS.items():
        actual = actual_headers.get(name)
        if actual != expected:
            raise ValueError(
                f"request {index} header {name} changed: {actual!r}, expected {expected!r}"
            )
    if body != expected_body:
        raise ValueError(
            f"request {index} body changed: {sha256_bytes(body)}, expected {sha256_bytes(expected_body)}"
        )
    return {
        "index": index,
        "method": "GET",
        "path": "/app-script.php",
        "status": status,
        "body_bytes": len(body),
        "body_sha256": sha256_bytes(body),
        "headers": {name: actual_headers[name] for name in EXPECTED_HEADERS},
    }


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_for_loopback(port: int, process: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"PHP server exited during startup with code {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"PHP server did not bind to 127.0.0.1:{port} within {timeout}s")


def stop_process(process: subprocess.Popen, timeout: float = 5.0) -> int:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)
    return int(process.returncode)


def run_http_contract(
    root: Path,
    output: Path,
    expected_body: bytes,
    startup_timeout: float,
    request_timeout: float,
) -> tuple[dict, list[dict]]:
    output.mkdir(parents=True, exist_ok=True)
    stdout_path = output / "server.stdout.log"
    stderr_path = output / "server.stderr.log"
    port = free_loopback_port()
    command = ["php", "-n", "-S", f"127.0.0.1:{port}", "-t", str(root)]
    version = subprocess.run(
        ["php", "-n", "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=5,
    ).stdout.decode("utf-8", errors="replace").splitlines()[0]
    process: subprocess.Popen | None = None
    samples: list[dict] = []
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            wait_for_loopback(port, process, startup_timeout)
            for index in range(1, REQUEST_COUNT + 1):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=request_timeout)
                try:
                    connection.request("GET", "/app-script.php", headers={"Connection": "close"})
                    response = connection.getresponse()
                    body = response.read()
                    samples.append(
                        validate_http_sample(index, response.status, response.getheaders(), body, expected_body)
                    )
                finally:
                    connection.close()
        finally:
            server_exit = stop_process(process) if process is not None else None
            stdout.flush()
            stderr.flush()
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
    return {
        "executor": "php_builtin_server",
        "php_version": version,
        "command": command,
        "bind_host": "127.0.0.1",
        "port": port,
        "startup_timeout_seconds": startup_timeout,
        "request_timeout_seconds": request_timeout,
        "server_exit_after_bounded_termination": server_exit,
        "stdout_path": stdout_path.relative_to(root).as_posix(),
        "stderr_path": stderr_path.relative_to(root).as_posix(),
        "local_http_requests": len(samples),
        "outbound_network_requests": 0,
    }, samples


def build_report(
    predecessor_report_sha256: str,
    sources: list[dict],
    runtime: dict,
    samples: list[dict],
) -> dict:
    verify_lineage(predecessor_report_sha256)
    if len(samples) != REQUEST_COUNT:
        raise ValueError(f"HTTP sample count changed: {len(samples)}, expected {REQUEST_COUNT}")
    return {
        "schema_version": 1,
        "status": "PASS_LOCAL_HTTP_RUNTIME_CONTRACT_ONLY",
        "execution_environment": execution_environment(),
        "lineage": {"accepted_predecessor_report_sha256": predecessor_report_sha256},
        "sources": sources,
        "runtime": runtime,
        "samples": samples,
        "acceptance_limits": {
            "predecessor_source_contract_accepted": True,
            "local_php_http_status_body_accepted": True,
            "local_php_response_headers_accepted": True,
            "production_php_or_proxy_accepted": False,
            "public_reachability_accepted": False,
            "cdn_cache_behavior_accepted": False,
            "runtime_security_accepted": False,
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
        "samples": report.get("samples", []),
        "acceptance_limits": report.get("acceptance_limits", {}),
    }


def write_evidence(output: Path, report: dict, exit_code: int) -> None:
    atomic_json(output / "report.json", report)
    atomic_json(output / "manifest.json", build_manifest(report))
    atomic_bytes(output / "exit.code", f"{exit_code}\n".encode())
    log_hashes = {}
    for name in ("server.stdout.log", "server.stderr.log"):
        path = output / name
        if path.exists():
            log_hashes[name] = sha256_bytes(path.read_bytes())
    receipt = {
        "status": report["status"],
        "report_sha256": sha256_bytes((output / "report.json").read_bytes()),
        "manifest_sha256": sha256_bytes((output / "manifest.json").read_bytes()),
        "exit_code_sha256": sha256_bytes((output / "exit.code").read_bytes()),
        "log_sha256": log_hashes,
        "checkpoint_policy": "verified_only",
        "local_http_requests": len(report.get("samples", [])),
        "outbound_network_requests": 0,
        "model_calls": 0,
        "paid_api_calls": 0,
    }
    atomic_json(output / "receipt.json", receipt)


def interrupted(signum: int, _frame: object) -> None:
    raise InterruptedError(f"signal {signum}")


def failure_report(error: BaseException, predecessor_report_sha256: str) -> dict:
    return {
        "schema_version": 1,
        "status": "FAIL_NOT_VERIFIED",
        "error": {"class": type(error).__name__, "message": str(error)},
        "execution_environment": execution_environment(),
        "lineage": {"accepted_predecessor_report_sha256": predecessor_report_sha256},
        "sources": [],
        "runtime": None,
        "samples": [],
        "acceptance_limits": {
            "predecessor_source_contract_accepted": False,
            "local_php_http_status_body_accepted": False,
            "local_php_response_headers_accepted": False,
            "production_php_or_proxy_accepted": False,
            "public_reachability_accepted": False,
            "cdn_cache_behavior_accepted": False,
            "runtime_security_accepted": False,
            "deploy_accepted": False,
            "publication_accepted": False,
            "delivery_accepted": False,
            "release_accepted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--predecessor-report-sha256",
        default=EXPECTED_PREDECESSOR_REPORT_SHA256,
    )
    parser.add_argument("--startup-timeout", type=float, default=5.0)
    parser.add_argument("--request-timeout", type=float, default=5.0)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    previous_handlers = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.signal(signum, interrupted)
    try:
        verify_lineage(args.predecessor_report_sha256)
        sources, expected_body = verify_sources(root)
        runtime, samples = run_http_contract(
            root,
            output,
            expected_body,
            args.startup_timeout,
            args.request_timeout,
        )
        report = build_report(args.predecessor_report_sha256, sources, runtime, samples)
        write_evidence(output, report, 0)
    except BaseException as error:
        report = failure_report(error, args.predecessor_report_sha256)
        write_evidence(output, report, 2)
        print(json.dumps(report["error"], ensure_ascii=False))
        return 2
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    print(json.dumps({"status": report["status"], "samples": len(report["samples"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
