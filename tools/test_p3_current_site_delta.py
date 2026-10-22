#!/usr/bin/env python3
"""Negative controls for the exact P3 exception to immutable site snapshots."""
import copy
import json
import unittest

from tools import check_p3_current_site_delta as gate


class P3LegacySnapshotBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(gate.git("show", gate.BASE + ":products-storage/ARTIFACT-REGISTRY.json"))
        # Negative controls for the historic P3 projection use its fixed
        # fixture; the actual site has since moved to a later staging scope.
        cls.current = copy.deepcopy(cls.baseline)
        p3 = next(row for row in cls.current["product_sources"] if row["runtime_sku"] == "p3")
        p3["git_tree_sha"], p3["bytes"] = gate.P3_TREE, gate.P3_BYTES

    def test_actual_known_site_scope(self):
        result = gate.validate_known_site_delta()
        self.assertIn(result["verdict"], {"PASS_CURRENT_P3_SITE_DELTA_ONLY", "PASS_PINNED_CUSTOMER_ROUTE_STAGING_ONLY"})
        self.assertTrue(result["historical_snapshot_preserved"])
        if result["verdict"] == "PASS_PINNED_CUSTOMER_ROUTE_STAGING_ONLY":
            self.assertFalse(result["release_accepted"])
            self.assertTrue(result["protected_product_payment_source_unchanged"])

    def test_exact_projected_registry(self):
        gate.validate_registry_projection(self.baseline, self.current)

    def test_append_only_history_does_not_change_identity(self):
        altered = copy.deepcopy(self.current)
        altered["change_history"] = {"audit": "new"}
        gate.validate_registry_projection(self.baseline, altered)

    def test_other_product_tree_drift_fails(self):
        altered = copy.deepcopy(self.current)
        next(row for row in altered["product_sources"] if row["runtime_sku"] == "p2")["bytes"] += 1
        with self.assertRaisesRegex(ValueError, "unapproved product registry"):
            gate.validate_registry_projection(self.baseline, altered)

    def test_p3_unapproved_file_bytes_fails(self):
        altered = copy.deepcopy(self.current)
        next(row for row in altered["product_sources"] if row["runtime_sku"] == "p3")["bytes"] += 1
        with self.assertRaisesRegex(ValueError, "unapproved product registry"):
            gate.validate_registry_projection(self.baseline, altered)

    def test_p3_role_or_release_fails(self):
        altered = copy.deepcopy(self.current)
        next(row for row in altered["product_sources"] if row["runtime_sku"] == "p3")["role"] = "live"
        with self.assertRaisesRegex(ValueError, "unapproved product registry"):
            gate.validate_registry_projection(self.baseline, altered)

    def test_unapproved_artifact_or_price_fails(self):
        altered = copy.deepcopy(self.current)
        altered["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "unapproved product registry"):
            gate.validate_registry_projection(self.baseline, altered)

    def test_unknown_extra_registry_key_fails(self):
        altered = copy.deepcopy(self.current)
        altered["unexpected_release_override"] = True
        with self.assertRaisesRegex(ValueError, "unapproved product registry"):
            gate.validate_registry_projection(self.baseline, altered)

    def test_unexpected_html_php_extra_fails(self):
        hashes = {path: value[1] for path, value in gate.EXPECTED_HTML_PHP.items()}
        with self.assertRaisesRegex(ValueError, "unapproved HTML/PHP delta"):
            gate.validate_html_deltas(set(hashes) | {"unrelated-page.html"}, hashes)

    def test_unexpected_html_php_missing_fails(self):
        hashes = {path: value[1] for path, value in gate.EXPECTED_HTML_PHP.items()}
        with self.assertRaisesRegex(ValueError, "unapproved HTML/PHP delta"):
            gate.validate_html_deltas(set(hashes) - {"download.php"}, hashes)

    def test_modified_p3_page_fails(self):
        hashes = {path: value[1] for path, value in gate.EXPECTED_HTML_PHP.items()}
        hashes["products/p3-shablony-ks2-ks3.html"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "changed or unpinned HTML/PHP blob"):
            gate.validate_html_deltas(set(hashes), hashes)

    def test_modified_payment_or_delivery_fails(self):
        for path in ["products-config.php", "download.php"]:
            hashes = {name: value[1] for name, value in gate.EXPECTED_HTML_PHP.items()}
            hashes[path] = "f" * 64
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "changed or unpinned"):
                gate.validate_html_deltas(set(hashes), hashes)


    def test_owner_approved_p3_price_is_consistent(self):
        import re
        from pathlib import Path
        root = gate.ROOT
        config = (root / "products-config.php").read_text(encoding="utf-8")
        p3 = re.search(r"'p3'\s*=>\s*\[(.*?)\],", config, flags=re.S)
        self.assertIsNotNone(p3)
        price = re.search(r"'price'\s*=>\s*(\d+)", p3.group(1))
        self.assertIsNotNone(price)
        self.assertEqual(int(price.group(1)), 1790000)
        diagnostic = (root / "diagnostika.html").read_text(encoding="utf-8")
        scenarios = json.loads(re.search(r'const SCENARIOS\s*=\s*(\[.*?\]);', diagnostic, re.S).group(1))
        prices = [offer['price'] for row in scenarios for offer in (row.get('core') or {}, row.get('entry') or {})
                  if offer.get('url') == '/products/p3-shablony-ks2-ks3.html']
        self.assertTrue(prices)
        self.assertTrue(all(price == 17900 for price in prices))
        pages = ("index.html", "katalog.html",
                 "products/p3-shablony-ks2-ks3.html",
                 "articles/proverka-ks-2-pered-sdachey.html",
                 "articles/raboty-ne-prinyaty.html")
        for name in pages:
            content = (root / name).read_text(encoding="utf-8")
            with self.subTest(page=name):
                self.assertIn("17 900 \u20bd", content)
                self.assertNotIn("1 990 \u20bd", content)
        for name in pages[:3]:
            content = (root / name).read_text(encoding="utf-8")
            self.assertIn('data-price="1790000"', content)
        for name in ("katalog.html", "products/p3-shablony-ks2-ks3.html"):
            self.assertIn('"price": "17900"', (root / name).read_text(encoding="utf-8"))



if __name__ == "__main__":
    unittest.main()
