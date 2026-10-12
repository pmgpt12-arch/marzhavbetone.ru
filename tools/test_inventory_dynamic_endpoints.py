#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import inventory_dynamic_endpoints as target


class InventoryTests(unittest.TestCase):
    def source_report(self):
        return {"excluded_dynamic_endpoints": list(target.EXPECTED_ENDPOINTS)}

    def test_exact_endpoint_contract(self):
        raw = json.dumps(self.source_report()).encode()
        with mock.patch.object(target, "EXPECTED_REPORT_SHA256", hashlib.sha256(raw).hexdigest()):
            self.assertEqual(
                tuple(target.validate_source_report(raw)["excluded_dynamic_endpoints"]),
                target.EXPECTED_ENDPOINTS,
            )

    def test_rejects_changed_endpoint_contract(self):
        value = self.source_report()
        value["excluded_dynamic_endpoints"].pop()
        raw = json.dumps(value).encode()
        with mock.patch.object(target, "EXPECTED_REPORT_SHA256", hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError, "endpoint set/order changed"):
                target.validate_source_report(raw)

    def test_indicators_record_line_numbers_not_values(self):
        result = target.source_indicators("<?php\n$x = $_POST['email'];\nheader('X: y');\n")
        self.assertEqual(result["request_input"], [2])
        self.assertEqual(result["response_header"], [3])
        self.assertNotIn("email", json.dumps(result))

    def test_client_source_references_add_hint_without_excerpt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.js").write_text(
                "fetch('/event.php', {\n  method: 'POST',\n  body: '{}'\n});\n",
                encoding="utf-8",
            )
            sites = target.client_source_references(root, target.EXPECTED_ENDPOINTS)
            self.assertEqual(sites, [{
                "endpoint": "event.php",
                "source_path": "app.js",
                "line": 1,
                "nearby_method_hint": "POST",
            }])
            self.assertNotIn("body", json.dumps(sites))

    def test_client_source_references_ignore_evidence_and_product_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.js").write_text("fetch('/event.php')\n", encoding="utf-8")
            (root / "tools").mkdir()
            (root / "tools" / "note.php").write_text("event.php\n", encoding="utf-8")
            (root / "products-storage").mkdir()
            (root / "products-storage" / "note.html").write_text("event.php\n", encoding="utf-8")
            self.assertEqual(target.client_source_references(root, target.EXPECTED_ENDPOINTS), [{
                "endpoint": "event.php",
                "source_path": "app.js",
                "line": 1,
                "nearby_method_hint": "UNSPECIFIED",
            }])

    def test_server_references_are_not_client_call_sites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.php").write_text("<?php $x = 'webhook.php';\n", encoding="utf-8")
            self.assertEqual(target.client_source_references(root, target.EXPECTED_ENDPOINTS), [])
            self.assertEqual(target.server_source_references(root, target.EXPECTED_ENDPOINTS), [{
                "endpoint": "webhook.php",
                "source_path": "config.php",
                "line": 1,
                "nearby_method_hint": "UNSPECIFIED",
            }])

    def test_comment_is_only_a_source_reference_not_a_call_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "attribution.js").write_text("// sends to event.php\n", encoding="utf-8")
            references = target.client_source_references(root, target.EXPECTED_ENDPOINTS)
            self.assertEqual(references[0]["endpoint"], "event.php")
            self.assertNotIn("call", json.dumps(references))

    def test_execution_environment_records_exact_evidence_head(self):
        with mock.patch.dict("os.environ", {"EVIDENCE_HEAD_SHA": "abc123"}, clear=True):
            self.assertEqual(target.execution_environment(), {"evidence_head_sha": "abc123"})

    def test_atomic_json_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            target.atomic_json(path, {"status": "PASS"})
            self.assertEqual(json.loads(path.read_text()), {"status": "PASS"})
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_write_evidence_hashes_report_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {
                "status": "PASS_SOURCE_INVENTORY_ONLY",
                "source_report": {"path": "source.json", "sha256": "a" * 64},
                "endpoints": [{"path": "event.php", "bytes": 3, "sha256": "b" * 64}],
                "client_source_references": [],
                "server_source_references": [],
            }
            target.write_evidence(output, report)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(
                receipt["report_sha256"],
                hashlib.sha256((output / "report.json").read_bytes()).hexdigest(),
            )
            self.assertEqual(
                receipt["manifest_sha256"],
                hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest(),
            )
            self.assertFalse(list(output.glob("*.tmp")))

    def test_failure_evidence_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out"
            with mock.patch(
                "sys.argv",
                [
                    "inventory_dynamic_endpoints.py",
                    "--root", str(root),
                    "--source-report", "missing.json",
                    "--output", str(output),
                ],
            ):
                self.assertEqual(target.main(), 2)
            report = json.loads((output / "report.json").read_text())
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(report["status"], "FAIL_NOT_VERIFIED")
            self.assertEqual(receipt["status"], "FAIL_NOT_VERIFIED")
            self.assertFalse(report["acceptance_limits"]["source_inventory_accepted"])
            self.assertTrue((output / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
