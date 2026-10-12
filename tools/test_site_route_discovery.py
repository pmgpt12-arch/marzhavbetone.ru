#!/usr/bin/env python3
import copy
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("discover_site_routes.py")
SPEC = importlib.util.spec_from_file_location("discover_site_routes", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SiteRouteDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = mod.build_report()

    def test_exact_counts(self):
        self.assertEqual(self.report["candidate_count"], 116)
        self.assertEqual(self.report["sitemap_route_count"], 84)
        self.assertEqual(self.report["public_route_count"], 98)
        self.assertEqual(self.report["non_route_count"], 18)
        self.assertEqual(self.report["counts_by_class"], {
            "cli_only": 1,
            "indexable_page": 84,
            "non_route_module": 3,
            "public_endpoint": 10,
            "supporting_page": 4,
            "test_fixture": 14,
        })

    def test_byte_determinism(self):
        self.assertEqual(mod.encoded(mod.build_report()), mod.encoded(mod.build_report()))

    def test_unknown_candidate_fails_closed(self):
        with self.assertRaises(mod.DiscoveryError):
            mod.classify("archive/old.html", {})

    def test_head_candidate_drift_fails(self):
        source = {"index.html": {"blob_sha": "a", "bytes": 1, "mode": "100644"}}
        head = {"index.html": {"blob_sha": "b", "bytes": 1, "mode": "100644"}}
        with self.assertRaises(mod.DiscoveryError):
            mod.assert_head_candidates_match_source(source, head)

    def test_missing_candidate_fails(self):
        entries = copy.deepcopy(self.report["entries"])
        entries.pop()
        with self.assertRaises(mod.DiscoveryError):
            mod.validate_entries(entries, {e["source_path"] for e in self.report["entries"]})

    def test_extra_candidate_fails(self):
        entries = copy.deepcopy(self.report["entries"])
        entries.append({**entries[0], "source_path": "extra.html", "route_registry_id": "extra"})
        with self.assertRaises(mod.DiscoveryError):
            mod.validate_entries(entries, {e["source_path"] for e in self.report["entries"]})

    def test_duplicate_route_fails(self):
        entries = copy.deepcopy(self.report["entries"])
        routed = [e for e in entries if e["public_route"] is not None]
        routed[1]["public_route"] = routed[0]["public_route"]
        with self.assertRaises(mod.DiscoveryError):
            mod.validate_entries(entries, {e["source_path"] for e in entries})

    def test_direct_modules_are_not_routes(self):
        by_path = {e["source_path"]: e for e in self.report["entries"]}
        for path in mod.NON_ROUTE_MODULES | mod.CLI_ONLY:
            self.assertIsNone(by_path[path]["public_route"])

    def test_service_pages_are_kept(self):
        by_path = {e["source_path"]: e for e in self.report["entries"]}
        for path in mod.SUPPORTING_PAGES:
            self.assertEqual(by_path[path]["route_class"], "supporting_page")


if __name__ == "__main__":
    unittest.main()
