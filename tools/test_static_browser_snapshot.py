#!/usr/bin/env python3
import copy
import hashlib
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools import capture_static_browser_snapshot as target


def sample_report():
    pages = []
    for index in range(target.EXPECTED_PAGE_COUNT):
        pages.append({"public_route": f"/p{index}.html", "source_path": f"p{index}.html"})
    return {
        "status": "PASS_STATIC_SOURCE_SNAPSHOT_ONLY",
        "counts": {"static_pages": target.EXPECTED_PAGE_COUNT},
        "pages": pages,
        "excluded_dynamic_endpoints": [f"endpoint-{index}.php" for index in range(10)],
        "acceptance_limits": {"browser_render_accepted": False},
    }


class ContractTests(unittest.TestCase):
    def encoded(self, value):
        raw = json.dumps(value, sort_keys=True).encode()
        return raw, hashlib.sha256(raw).hexdigest()

    def test_accepts_exact_contract(self):
        raw, digest = self.encoded(sample_report())
        self.assertEqual(len(target.validate_source_report(raw, digest)["pages"]), 88)

    def test_rejects_duplicate_route(self):
        value = sample_report()
        value["pages"][1]["public_route"] = value["pages"][0]["public_route"]
        raw, digest = self.encoded(value)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            target.validate_source_report(raw, digest)

    def test_rejects_changed_dynamic_scope(self):
        value = sample_report()
        value["excluded_dynamic_endpoints"].pop()
        raw, digest = self.encoded(value)
        with self.assertRaisesRegex(ValueError, "exclusion contract"):
            target.validate_source_report(raw, digest)

    def test_atomic_json_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            target.atomic_json(path, {"status": "PASS"})
            self.assertEqual(json.loads(path.read_text()), {"status": "PASS"})
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_dynamic_scope_is_stubbed_except_render_dependency(self):
        excluded = {"/event.php", "/payment.php", "/app-script.php"}
        self.assertEqual(
            target.dynamic_disposition("/event.php", excluded),
            "inert_204_stub_not_executed",
        )
        self.assertEqual(
            target.dynamic_disposition("/app-script.php", excluded),
            "allowed_render_dependency_not_accepted",
        )
        self.assertEqual(target.dynamic_disposition("/styles.css", excluded), "not_dynamic")

    def test_invalid_source_still_leaves_failure_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "bad-report.json"
            report.write_text("{}", encoding="utf-8")
            output = root / "evidence"
            result, exit_code = target.capture(root, report, output)
            self.assertEqual(exit_code, 1)
            self.assertEqual(result["status"], "FAIL_BROWSER_RENDER_SNAPSHOT")
            self.assertTrue((output / "report.json").exists())
            self.assertTrue((output / "manifest.json").exists())
            self.assertTrue((output / "receipt.json").exists())
            self.assertEqual(
                json.loads((output / "receipt.json").read_text())["checkpoint_policy"],
                "verified_only",
            )

    def test_route_handler_uses_playwright_two_argument_contract(self):
        class Request:
            url = "http://127.0.0.1/event.php"
            method = "POST"

        class Route:
            continued = False
            fulfilled = None

            def continue_(self):
                self.continued = True

            def fulfill(self, **kwargs):
                self.fulfilled = kwargs

        observed = []
        route = Route()
        handler = target.make_dynamic_route_handler(
            {"/event.php", "/app-script.php"},
            observed,
        )
        handler(route, Request())
        self.assertFalse(route.continued)
        self.assertEqual(route.fulfilled["status"], 204)
        self.assertEqual(observed[0]["disposition"], "inert_204_stub_not_executed")

    def test_socket_failure_still_leaves_failure_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text("{}", encoding="utf-8")
            output = root / "evidence"
            with mock.patch.object(target, "validate_source_report", return_value=sample_report()):
                with mock.patch.object(target, "free_port", side_effect=OSError("no socket")):
                    result, exit_code = target.capture(root, report, output)
            self.assertEqual(exit_code, 1)
            self.assertEqual(result["status"], "FAIL_BROWSER_RENDER_SNAPSHOT")
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "FAIL_BROWSER_RENDER_SNAPSHOT")


if __name__ == "__main__":
    unittest.main()
