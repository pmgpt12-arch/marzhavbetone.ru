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

    def test_client_call_sites_infer_post_without_excerpt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.js").write_text(
                "fetch('/event.php', {\n  method: 'POST',\n  body: '{}'\n});\n",
                encoding="utf-8",
            )
            sites = target.client_call_sites(root, target.EXPECTED_ENDPOINTS)
            self.assertEqual(sites, [{
                "endpoint": "event.php",
                "source_path": "app.js",
                "line": 1,
                "method": "POST",
            }])
            self.assertNotIn("body", json.dumps(sites))

    def test_atomic_json_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            target.atomic_json(path, {"status": "PASS"})
            self.assertEqual(json.loads(path.read_text()), {"status": "PASS"})
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
