#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest import mock

from tools import check_app_script_wrapper_contract as target


WRAPPER = """<?php
declare(strict_types=1);

header('Content-Type: application/javascript; charset=UTF-8');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

readfile(__DIR__ . '/app.js');
"""


class WrapperContractTests(unittest.TestCase):
    def fixtures(self, root: Path, app: bytes = b"const x = 1;\n") -> None:
        (root / "app-script.php").write_text(WRAPPER, encoding="utf-8")
        (root / "app.js").write_bytes(app)

    def expected_sources(self, root: Path):
        return {
            name: {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name in ("app-script.php", "app.js")
            if (path := root / name)
        }

    def test_exact_wrapper_contract(self):
        contract = target.verify_wrapper(WRAPPER)
        self.assertTrue(contract["strict_types"])
        self.assertEqual(contract["header_count"], 4)
        self.assertEqual(contract["header_lines"], [4, 5, 6, 7])
        self.assertEqual(contract["delegation"], {"target": "app.js", "line": 9})
        self.assertEqual(contract["forbidden_construct_count"], 0)

    def test_rejects_extra_statement(self):
        with self.assertRaisesRegex(ValueError, "statement contract changed"):
            target.verify_wrapper(WRAPPER.replace("readfile", "$x = 1;\nreadfile"))

    def test_rejects_changed_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixtures(root)
            expected = self.expected_sources(root)
            with mock.patch.object(target, "EXPECTED_SOURCES", expected):
                target.build_report(root, target.EXPECTED_INVENTORY_REPORT_SHA256)
                (root / "app.js").write_text("changed\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "source fingerprint changed"):
                    target.build_report(root, target.EXPECTED_INVENTORY_REPORT_SHA256)

    def test_rejects_changed_inventory_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixtures(root)
            with self.assertRaisesRegex(ValueError, "inventory lineage changed"):
                target.build_report(root, "0" * 64)

    def test_report_has_source_only_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixtures(root)
            with mock.patch.object(target, "EXPECTED_SOURCES", self.expected_sources(root)):
                report = target.build_report(root, target.EXPECTED_INVENTORY_REPORT_SHA256)
            self.assertTrue(report["acceptance_limits"]["source_wrapper_contract_accepted"])
            self.assertTrue(all(
                value is False
                for key, value in report["acceptance_limits"].items()
                if key != "source_wrapper_contract_accepted"
            ))
            self.assertNotIn("source_body", json.dumps(report))

    def test_write_evidence_hash_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {
                "status": "PASS_WRAPPER_SOURCE_CONTRACT_ONLY",
                "lineage": {},
                "sources": [],
                "wrapper_contract": {},
            }
            target.write_evidence(output, report)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["report_sha256"], hashlib.sha256((output / "report.json").read_bytes()).hexdigest())
            self.assertEqual(receipt["manifest_sha256"], hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest())
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
            self.assertFalse(report["acceptance_limits"]["source_wrapper_contract_accepted"])

    def test_signal_handler_raises_for_failure_path(self):
        with self.assertRaisesRegex(InterruptedError, str(signal.SIGTERM)):
            target.interrupted(signal.SIGTERM, None)

    def test_environment_records_exact_head_only_when_present(self):
        with mock.patch.dict(os.environ, {"EVIDENCE_HEAD_SHA": "abc123"}, clear=True):
            self.assertEqual(target.execution_environment(), {"evidence_head_sha": "abc123"})


if __name__ == "__main__":
    unittest.main()
