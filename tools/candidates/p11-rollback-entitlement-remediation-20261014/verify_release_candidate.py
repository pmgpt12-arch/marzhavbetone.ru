#!/usr/bin/env python3
"""Bounded offline acceptance for the P11 release/rollback candidate."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

BASE = "03ebb0f1970a295d69fc6e8bc175d9e1d5191f76"
HERE = Path(__file__).resolve().parent
ZIP_PATH = (
    "tools/candidates/portfolio-owner-pdf-20261013/"
    "p11-t6-consolidated-gold-20261014/p11-t6-eight-files-gold-candidate.zip"
)
LETTER_PATH = (
    "tools/candidates/portfolio-owner-pdf-20261013/"
    "19-kvartiry-vmesto-deneg/00-PISMO-POSLE-POKUPKI.txt"
)
ZIP_SHA = "f365039ef568dbbe9c661a6e1f553d21ddd0b086c9172f1e5a4340fb7dfe7f70"
LETTER_SHA = "c8f9d78cf2335f2acf52ab8d12258e4e3e799c9c87e3447edcc17c7f0f507ea5"
EDITION = {
    "kind": "p11-t6-gold-20261014",
    "zip": "p11-" + ZIP_SHA + ".zip",
    "sha256": ZIP_SHA,
    "letter": "p11-letter-" + LETTER_SHA + ".txt",
    "letter_sha256": LETTER_SHA,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_builder():
    path = HERE / "build_release_candidate.py"
    spec = importlib.util.spec_from_file_location("p11_release_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load release builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provider_stub() -> str:
    return r"""<?php
declare(strict_types=1);
foreach ([
    'CURLOPT_POST' => 1, 'CURLOPT_POSTFIELDS' => 2, 'CURLOPT_RETURNTRANSFER' => 3,
    'CURLOPT_HTTPHEADER' => 4, 'CURLOPT_USERPWD' => 5, 'CURLOPT_CONNECTTIMEOUT' => 6,
    'CURLOPT_TIMEOUT' => 7, 'CURLINFO_HTTP_CODE' => 8
] as $name => $value) if (!defined($name)) define($name, $value);
function curl_init($url = null) { return ['url' => $url]; }
function curl_setopt_array(&$handle, $options) {
    $GLOBALS['fixture_curl_options'] = $options;
    return true;
}
function curl_exec($handle) {
    $files = glob(ORDERS_DIR . '/order_*.json') ?: [];
    $order = count($files) === 1 ? json_decode((string)file_get_contents($files[0]), true) : null;
    $post = json_decode((string)($GLOBALS['fixture_curl_options'][CURLOPT_POSTFIELDS] ?? ''), true);
    file_put_contents(__DIR__ . '/provider-state.json', json_encode([
        'url' => $handle['url'] ?? null,
        'order_count_before_provider' => count($files),
        'persisted_order_before_provider' => $order,
        'provider_request' => $post,
    ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    return json_encode([
        'id' => 'fixture-payment-id',
        'confirmation' => ['confirmation_url' => 'https://provider.fixture.invalid/pay'],
    ], JSON_UNESCAPED_UNICODE);
}
function curl_getinfo($handle, $option) { return 200; }
function curl_error($handle) { return ''; }
function curl_close($handle) {}
"""


def payment_wrapper() -> str:
    return r"""<?php
declare(strict_types=1);
register_shutdown_function(function () {
    file_put_contents(__DIR__ . '/http-code.txt', (string)(http_response_code() ?: 200));
});
$_SERVER['REQUEST_METHOD'] = 'POST';
require __DIR__ . '/payment.php';
"""


def config_text(enabled: bool) -> str:
    flag = "true" if enabled else "false"
    return f"""<?php
declare(strict_types=1);
define('ORDERS_DIR', __DIR__ . '/orders');
define('DELIVERY_DIR', __DIR__ . '/orders/delivery');
define('PRODUCTS_DIR', __DIR__ . '/masters');
define('SITE_URL', 'https://buyer.fixture.invalid');
define('ADMIN_EMAIL', 'admin@fixture.invalid');
define('YOOKASSA_SHOP_ID', 'fixture-shop');
define('YOOKASSA_SECRET_KEY', 'fixture-secret');
define('YOOKASSA_API_URL', 'https://provider.fixture.invalid/v3');
define('YOOKASSA_MODE', 'test');
define('MVB_P11_CANDIDATE_BINDING', {flag});
define('MVB_P11_CANDIDATE_SOURCE_DIR', __DIR__ . '/accepted');
"""


def run_payment_case(
    outputs: dict[str, bytes],
    archive: bytes,
    letter: bytes,
    *,
    enabled: bool,
    missing_archive: bool = False,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="p11-release-payment-") as td:
        root = Path(td)
        os.chmod(root, 0o700)
        for directory in ("orders/delivery", "masters", "accepted"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        for name, data in outputs.items():
            fixture_data = data
            if name == "payment.php":
                before = b"file_get_contents('php://input')"
                after = b"stream_get_contents(STDIN)"
                require(data.count(before) == 1, "payment input fixture anchor")
                fixture_data = data.replace(before, after, 1)
            (root / name).write_bytes(fixture_data)
        if not missing_archive:
            (root / "accepted/accepted.zip").write_bytes(archive)
        (root / "accepted/accepted-letter.txt").write_bytes(letter)
        (root / "config.php").write_text(config_text(enabled))
        (root / "provider-stub.php").write_text(provider_stub())
        (root / "wrapper.php").write_text(payment_wrapper())
        payload = {
            "items": [
                {
                    "sku": "p11",
                    "price": 1,
                    "name": "attacker name",
                    "edition": {"kind": "attacker-selected-edition"},
                }
            ],
            "email": "buyer@fixture.invalid",
            "phone": "",
            "attribution": {"first": {"source": "fixture"}},
        }
        php = [
            "php", "-d",
            "disable_functions=mail,exec,shell_exec,system,passthru,popen,proc_open,"
            "curl_init,curl_setopt_array,curl_exec,curl_getinfo,curl_error,curl_close",
            "-d", "allow_url_fopen=0",
            "-d", "display_errors=stderr",
            "-d", "open_basedir=" + str(root),
            "-d", "sys_temp_dir=" + str(root),
            "-d", "auto_prepend_file=" + str(root / "provider-stub.php"),
            str(root / "wrapper.php"),
        ]
        env = {k: v for k, v in os.environ.items() if k not in ("PHPRC", "PHP_INI_SCAN_DIR")}
        process = subprocess.run(
            php,
            input=json.dumps(payload, ensure_ascii=False).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=root,
            env=env,
            timeout=12,
        )
        orders = sorted((root / "orders").glob("order_*.json"))
        result = {
            "returncode": process.returncode,
            "stdout": process.stdout.decode(errors="replace"),
            "stderr": process.stderr.decode(errors="replace"),
            "http_code": int((root / "http-code.txt").read_text()),
            "orders": [json.loads(path.read_text()) for path in orders],
            "provider_state": json.loads((root / "provider-state.json").read_text())
            if (root / "provider-state.json").exists()
            else None,
            "staged_zip": (root / "orders/delivery" / EDITION["zip"]).read_bytes()
            if (root / "orders/delivery" / EDITION["zip"]).exists()
            else None,
            "staged_letter": (root / "orders/delivery" / EDITION["letter"]).read_bytes()
            if (root / "orders/delivery" / EDITION["letter"]).exists()
            else None,
        }
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    checks: dict[str, str] = {}
    report = {
        "schema_version": 1,
        "id": "P11-ROLLBACK-ENTITLEMENT-REMEDIATION-20261014",
        "status": "FAIL_NOT_VERIFIED",
        "base": BASE,
        "checks": checks,
        "model_calls": 0,
        "paid_api": False,
        "external_network": False,
        "live_changes": False,
    }

    def check(name: str, condition: bool) -> None:
        require(condition, name)
        checks[name] = "PASS"

    try:
        read = lambda path: subprocess.check_output(
            ["git", "-C", str(args.repo), "show", BASE + ":" + path], timeout=15
        )
        builder = load_builder()
        inputs = {name: read(name) for name in builder.EXPECTED_BLOBS}
        archive = read(ZIP_PATH)
        letter = read(LETTER_PATH)
        check("accepted_zip_sha256", sha256(archive) == ZIP_SHA)
        check("accepted_letter_sha256", sha256(letter) == LETTER_SHA)

        outputs, release_patch, rollback_patch = builder.build(args.repo, inputs)
        outputs2, release_patch2, rollback_patch2 = builder.build(args.repo, inputs)
        check(
            "deterministic_builder",
            outputs == outputs2
            and release_patch == release_patch2
            and rollback_patch == rollback_patch2,
        )
        check(
            "products_config_contains_decoupled_reader_validation",
            b"if (!is_array($edition)) return false;" in outputs["products-config.php"]
            and b"MVB_P11_CANDIDATE_BINDING" in outputs["products-config.php"],
        )
        check(
            "accepted_download_bytes_reused",
            sha256(outputs["download.php"])
            == builder.ACCEPTED_BINDING_OUTPUT_SHA256["download.php"],
        )
        check("only_three_runtime_outputs", sorted(outputs) == ["download.php", "payment.php", "products-config.php"])
        check("payment_http_input_anchor_unique", outputs["payment.php"].count(b"file_get_contents('php://input')") == 1)
        check("published_release_patch_matches", (HERE / "release-candidate.patch").read_bytes() == release_patch)
        check("published_rollback_patch_matches", (HERE / "rollback-candidate.patch").read_bytes() == rollback_patch)

        bad = copy.copy(inputs)
        bad["payment.php"] += b"\n"
        try:
            builder.build(args.repo, bad)
        except ValueError:
            check("source_drift_fails_closed", True)
        else:
            check("source_drift_fails_closed", False)

        for name, data in outputs.items():
            lint = subprocess.run(
                ["php", "-l"],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            check("php_lint_" + name, lint.returncode == 0)

        good = run_payment_case(outputs, archive, letter, enabled=True)
        check("enabled_payment_exit_zero", good["returncode"] == 0 and not good["stderr"])
        response = json.loads(good["stdout"])
        check("enabled_payment_returns_fixture_url", response.get("ok") is True and response.get("payment_url") == "https://provider.fixture.invalid/pay")
        check("one_order_persisted", len(good["orders"]) == 1)
        final_order = good["orders"][0]
        state = good["provider_state"]
        check("provider_called_once_after_order_persisted", state is not None and state["order_count_before_provider"] == 1)
        persisted = state["persisted_order_before_provider"]
        check("server_assigns_exact_edition_before_provider", persisted["items"][0]["edition"] == EDITION)
        check("client_edition_and_price_ignored", persisted["items"][0]["edition"]["kind"] != "attacker-selected-edition" and persisted["items"][0]["price"] != 1)
        check("provider_amount_matches_server_total", state["provider_request"]["amount"]["value"] == f"{persisted['total'] / 100:.2f}")
        check("provider_receipt_matches_server_item", state["provider_request"]["receipt"]["items"][0]["amount"]["value"] == f"{persisted['items'][0]['price'] / 100:.2f}")
        check("edition_persists_after_provider", final_order["items"][0]["edition"] == EDITION and final_order["payment_id"] == "fixture-payment-id")
        check("accepted_zip_staged_before_provider", good["staged_zip"] == archive)
        check("accepted_letter_staged_before_provider", good["staged_letter"] == letter)

        disabled = run_payment_case(outputs, archive, letter, enabled=False)
        check("disabled_refuses_before_side_effects", disabled["http_code"] == 503 and disabled["orders"] == [] and disabled["provider_state"] is None)
        missing = run_payment_case(outputs, archive, letter, enabled=True, missing_archive=True)
        check("missing_source_refuses_before_side_effects", missing["http_code"] == 503 and missing["orders"] == [] and missing["provider_state"] is None)

        with tempfile.TemporaryDirectory(prefix="p11-release-patch-") as td:
            root = Path(td)
            for name, data in inputs.items():
                (root / name).write_bytes(data)
            for patch, label in ((release_patch, "release"), (rollback_patch, "rollback")):
                patch_path = root / (label + ".patch")
                patch_path.write_bytes(patch)
                check_run = subprocess.run(
                    ["git", "apply", "--check", "--unidiff-zero", str(patch_path)],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=8,
                )
                check(label + "_patch_check", check_run.returncode == 0)
                apply_run = subprocess.run(
                    ["git", "apply", "--unidiff-zero", str(patch_path)],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=8,
                )
                check(label + "_patch_apply", apply_run.returncode == 0)
                expected = outputs if label == "release" else inputs
                check(
                    label + "_byte_equivalence",
                    all((root / name).read_bytes() == data for name, data in expected.items()),
                )

        report.update(
            {
                "status": "PASS_AUTHOR_RELEASE_ROLLBACK_CANDIDATE_ONLY",
                "checks_passed": len(checks),
                "checks_total": len(checks),
                "input_sha256": {name: sha256(data) for name, data in inputs.items()},
                "output_sha256": {name: sha256(data) for name, data in outputs.items()},
                "release_patch_sha256": sha256(release_patch),
                "rollback_patch_sha256": sha256(rollback_patch),
                "accepted_zip_sha256": ZIP_SHA,
                "accepted_letter_sha256": LETTER_SHA,
                "provider_fixture": {
                    "external_call": False,
                    "persisted_before_call": True,
                    "edition": EDITION,
                },
                "limits": [
                    "candidate-only; no root runtime or config changes",
                    "no production source nomination",
                    "no real checkout, provider, callback, SMTP, deploy or rollback",
                    "G1-G8 remains 0/13; release HOLD",
                ],
            }
        )
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["checks_passed"] = sum(value == "PASS" for value in checks.values())
        report["checks_total"] = len(checks)
        atomic_write(args.output, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({key: report.get(key) for key in ("status", "checks_passed", "checks_total", "error")}, ensure_ascii=False))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
