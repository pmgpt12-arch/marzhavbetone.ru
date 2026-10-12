#!/usr/bin/env python3
import copy
import hashlib
import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
