#!/usr/bin/env python3
import copy
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("build_static_content_snapshot.py")
SPEC = importlib.util.spec_from_file_location("build_static_content_snapshot", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class StaticContentSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = mod.build_report()

    def test_exact_counts(self):
        self.assertEqual(cls_counts := self.report["counts"], {
            "static_pages": 88,
            "indexable_pages": 84,
            "supporting_pages": 4,
            "local_dependencies": 63,
            "external_dependencies": 0,
            "cta_sku_occurrences": 47,
            "unknown_skus": 0,
        })
        self.assertEqual(sum(cls_counts.values()) > 0, True)

    def test_byte_determinism(self):
        self.assertEqual(mod.encoded(mod.build_report()), mod.encoded(mod.build_report()))

    def test_normalization_is_narrow(self):
        raw = "<h1>Цена 1 990 ₽ &amp; CTA</h1><script>remove me</script>"
        value = mod.normalize_visible(raw)
        self.assertEqual(value, "Цена 1 990 ₽ & CTA")
        self.assertNotIn("remove me", value)

    def test_dependency_escape_fails_closed(self):
        with self.assertRaises(mod.SnapshotError):
            mod.resolve_dependency("../../secret", "index.html")

    def test_unknown_sku_fails_closed(self):
        with self.assertRaises(mod.SnapshotError):
            mod.validate_skus({"06": 1}, {"p1", "t1"})

    def test_missing_page_fails_closed(self):
        expected = {page["source_path"] for page in self.report["pages"]}
        actual = set(expected)
        actual.pop()
        with self.assertRaises(mod.SnapshotError):
            mod.validate_exact_paths(actual, expected, "static pages")

    def test_extra_page_fails_closed(self):
        expected = {page["source_path"] for page in self.report["pages"]}
        with self.assertRaises(mod.SnapshotError):
            mod.validate_exact_paths(expected | {"archive/old.html"}, expected, "static pages")

    def test_dependency_omission_fails_closed(self):
        expected = {item["path"] for item in self.report["dependencies"]}
        actual = set(expected)
        actual.pop()
        with self.assertRaises(mod.SnapshotError):
            mod.validate_exact_paths(actual, expected, "dependencies")

    def test_canonical_contract(self):
        missing = sorted(
            page["source_path"] for page in self.report["pages"]
            if page["canonical"] is None
        )
        self.assertEqual(missing, mod.CANONICAL_EXCEPTIONS)
        with self.assertRaises(mod.SnapshotError):
            mod.validate_canonical("article.html", "indexable_page", None)

    def test_acceptance_limits_remain_closed(self):
        limits = self.report["acceptance_limits"]
        self.assertTrue(limits["static_source_snapshot_accepted"])
        for key in (
            "browser_render_accepted",
            "substantive_content_quality_accepted",
            "legal_accepted",
            "deploy_accepted",
            "release_accepted",
        ):
            self.assertFalse(limits[key])

    def test_report_lists_exact_derived_dependencies(self):
        derived = {
            path
            for page in self.report["pages"]
            for path in page["local_dependency_paths"]
        }
        recorded = {item["path"] for item in self.report["dependencies"]}
        mod.validate_exact_paths(recorded, derived, "dependencies")



class RegistryIdentityProjectionTests(unittest.TestCase):
    def accepted(self):
        import json
        return json.loads(mod.read_source(mod.CONTENT_SOURCE_COMMIT,"products-storage/ARTIFACT-REGISTRY.json"))

    def test_history_only_append_preserves_static_identity(self):
        data=self.accepted();new=copy.deepcopy(data);new["change_history"]={"added":"audit only"}
        mod.validate_registry_identity(new,data)

    def test_changed_nomination_fails_with_history_present(self):
        data=self.accepted();new=copy.deepcopy(data);new["change_history"]={};new["artifacts"][0]["sha256"]="0"*64
        with self.assertRaises(mod.SnapshotError):mod.validate_registry_identity(new,data)

    def test_changed_portfolio_decision_still_fails(self):
        data=self.accepted();new=copy.deepcopy(data);new["change_history"]={};new["portfolio_decision"]["target_product_count"]=12
        with self.assertRaises(mod.SnapshotError):mod.validate_registry_identity(new,data)

    def test_extra_non_history_key_still_fails(self):
        data=self.accepted();new=copy.deepcopy(data);new["unexpected_release_override"]=True
        with self.assertRaises(mod.SnapshotError):mod.validate_registry_identity(new,data)


if __name__ == "__main__":
    unittest.main()
