#!/usr/bin/env python3
"""Strict current preview gates: sellable inventory, preview text, retired pages."""
import re
import tempfile
import unittest
from pathlib import Path
import build_preview as b

ROOT = Path(__file__).resolve().parents[1]


class PreviewContract(unittest.TestCase):
    def test_retired_product_pages_cannot_be_sold_or_previewed(self):
        for suffix in ("t2-peredacha-ispolnitelnoy-dokumentacii.html",
                       "t3-odnostoronniy-akt-i-zachet.html"):
            path = ROOT / "products" / suffix
            original = path.read_text(encoding="utf-8")
            self.assertNotIn("add-to-cart", original)
            self.assertIn("noindex,follow", original)
            self.assertEqual(b.render(path, b.catalog()), (original, ""))
            with tempfile.TemporaryDirectory() as directory:
                probe = Path(directory) / suffix
                probe.write_text(original.replace("Снят с продажи",
                                                  "add-to-cart Добавить в корзину", 1),
                                 encoding="utf-8")
                self.assertTrue(b.render(probe, b.catalog())[1],
                                f"{suffix}: stale buy control accepted")

    def test_sellable_full_inventory_rejects_missing_member(self):
        path = ROOT / "products/p7-dogovor-podryada.html"
        original = path.read_text(encoding="utf-8")
        self.assertEqual(b.render(path, b.catalog()), (original, ""))
        match = re.search(r"<code[^>]*>[^<]+\.(?:docx|xlsx|xls|pdf|txt)</code>",
                          original)
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / path.name
            probe.write_text(original.replace(match.group(0),
                                              "<code>unapproved-file.docx</code>", 1),
                             encoding="utf-8")
            self.assertIn("перечень файлов разошёлся", b.render(probe, b.catalog())[1])

    def test_sellable_preview_rejects_tampered_excerpt(self):
        path = ROOT / "products/p5-shtrafy-uderzhaniya.html"
        original = path.read_text(encoding="utf-8")
        self.assertEqual(b.render(path, b.catalog()), (original, ""))
        old = '<p class="preview-file">01-pretenziya-na-uderzhanie.docx</p>'
        self.assertIn(old, original)
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / path.name
            altered = original.replace(old,
                                       '<p class="preview-file">unapproved-file.docx</p>', 1)
            probe.write_text(altered, encoding="utf-8")
            candidate, reason = b.render(probe, b.catalog())
            self.assertTrue(reason or candidate != altered,
                            "forged live product excerpt was accepted")


if __name__ == "__main__":
    unittest.main()
