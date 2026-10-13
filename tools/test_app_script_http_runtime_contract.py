#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import tempfile
import unittest
from unittest import mock

from tools import check_app_script_http_runtime_contract as target


HEADERS = [
    ("Content-Type", "application/javascript; charset=UTF-8"),
    ("Cache-Control", "no-cache, no-store, must-revalidate"),
    ("Pragma", "no-cache"),
    ("Expires", "0"),
]
WRAPPER = """<?php
declare(strict_types=1);

header('Content-Type: application/javascript; charset=UTF-8');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

readfile(__DIR__ . '/app.js');
"""


class HttpRuntimeContractTests(unittest.TestCase):
    def fixtures(self, root: Path, body: bytes = b"const ok = true;\n") -> None:
        (root / "app-script.php").write_bytes(b"<?php readfile(__DIR__ . '/app.js');\n")
        (root / "app.js").write_bytes(body)

    def expected_sources(self, root: Path) -> dict:
        return {
            name: {
                "bytes": (root / name).stat().st_size,
                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
            }
            for name in ("app-script.php", "app.js")
        }

    def sample(self, index: int = 1, body: bytes = b"js\n", headers=HEADERS) -> dict:
        return target.validate_http_sample(index, 200, headers, body, body)

    def test_exact_http_sample(self):
        sample = self.sample()
        self.assertEqual(sample["status"], 200)
        self.assertEqual(sample["body_sha256"], hashlib.sha256(b"js\n").hexdigest())
        self.assertEqual(sample["headers"], target.EXPECTED_HEADERS)

    def test_headers_are_case_insensitive_but_values_are_exact(self):
        headers = [(name.swapcase(), value) for name, value in HEADERS]
        self.assertEqual(self.sample(headers=headers)["headers"], target.EXPECTED_HEADERS)

    def test_rejects_non_200_status(self):
        with self.assertRaisesRegex(ValueError, "status changed"):
            target.validate_http_sample(1, 404, HEADERS, b"js\n", b"js\n")

    def test_rejects_changed_body(self):
        with self.assertRaisesRegex(ValueError, "body changed"):
            target.validate_http_sample(1, 200, HEADERS, b"old\n", b"new\n")

    def test_rejects_missing_header(self):
        with self.assertRaisesRegex(ValueError, "header expires changed"):
            target.validate_http_sample(1, 200, HEADERS[:-1], b"js\n", b"js\n")

    def test_rejects_changed_header_value(self):
        headers = HEADERS[:-1] + [("Expires", "1")]
        with self.assertRaisesRegex(ValueError, "header expires changed"):
            target.validate_http_sample(1, 200, headers, b"js\n", b"js\n")

    def test_rejects_duplicate_contract_header(self):
        with self.assertRaisesRegex(ValueError, "duplicate response header"):
            target.validate_http_sample(1, 200, HEADERS + [("expires", "0")], b"js\n", b"js\n")

    def test_rejects_changed_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixtures(root)
            with mock.patch.object(target, "EXPECTED_SOURCES", self.expected_sources(root)):
                target.verify_sources(root)
                (root / "app.js").write_bytes(b"changed\n")
                with self.assertRaisesRegex(ValueError, "source fingerprint changed"):
                    target.verify_sources(root)

    def test_rejects_changed_predecessor_lineage(self):
        with self.assertRaisesRegex(ValueError, "predecessor report changed"):
            target.verify_lineage("0" * 64)

    def test_build_report_requires_exactly_two_samples(self):
        with self.assertRaisesRegex(ValueError, "sample count changed"):
            target.build_report(
                target.EXPECTED_PREDECESSOR_REPORT_SHA256,
                [],
                {},
                [self.sample()],
            )

    def test_report_limits_local_acceptance(self):
        report = target.build_report(
            target.EXPECTED_PREDECESSOR_REPORT_SHA256,
            [],
            {"local_http_requests": 2},
            [self.sample(1), self.sample(2)],
        )
        limits = report["acceptance_limits"]
        self.assertTrue(limits["local_php_http_status_body_accepted"])
        self.assertTrue(limits["local_php_response_headers_accepted"])
        self.assertFalse(limits["production_php_or_proxy_accepted"])
        self.assertFalse(limits["release_accepted"])

    def test_write_evidence_has_atomic_hash_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {
                "status": "PASS_LOCAL_HTTP_RUNTIME_CONTRACT_ONLY",
                "lineage": {},
                "sources": [],
                "samples": [self.sample(1), self.sample(2)],
                "acceptance_limits": {},
            }
            target.write_evidence(output, report, 0)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["report_sha256"], hashlib.sha256((output / "report.json").read_bytes()).hexdigest())
            self.assertEqual(receipt["manifest_sha256"], hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest())
            self.assertEqual(receipt["exit_code_sha256"], hashlib.sha256(b"0\n").hexdigest())
            self.assertFalse(list(output.glob("*.tmp")))

    def test_failure_evidence_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out"
            with mock.patch("sys.argv", ["check", "--root", str(root), "--output", str(output)]):
                self.assertEqual(target.main(), 2)
            report = json.loads((output / "report.json").read_text())
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(report["status"], "FAIL_NOT_VERIFIED")
            self.assertEqual(receipt["status"], "FAIL_NOT_VERIFIED")
            self.assertEqual((output / "exit.code").read_text(), "2\n")
            self.assertTrue(all(value is False for value in report["acceptance_limits"].values()))

    def test_signal_handler_raises_for_failure_path(self):
        with self.assertRaisesRegex(InterruptedError, str(signal.SIGTERM)):
            target.interrupted(signal.SIGTERM, None)

    def test_environment_records_exact_head_only_when_present(self):
        with mock.patch.dict(os.environ, {"EVIDENCE_HEAD_SHA": "abc123"}, clear=True):
            self.assertEqual(target.execution_environment(), {"evidence_head_sha": "abc123"})

    @unittest.skipUnless(shutil.which("php"), "PHP runtime is required for the localhost integration")
    def test_local_php_integration_two_gets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = b"const integration = true;\n"
            (root / "app-script.php").write_text(WRAPPER, encoding="utf-8")
            (root / "app.js").write_bytes(body)
            runtime, samples = target.run_http_contract(root, root / "out", body, 3.0, 3.0)
            self.assertEqual(runtime["bind_host"], "127.0.0.1")
            self.assertEqual(runtime["local_http_requests"], 2)
            self.assertEqual(len(samples), 2)
            self.assertTrue(all(sample["body_sha256"] == hashlib.sha256(body).hexdigest() for sample in samples))


if __name__ == "__main__":
    unittest.main()
