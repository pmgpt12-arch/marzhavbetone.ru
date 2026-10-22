#!/usr/bin/env python3
"""Accepted excerpts and full inventories fail closed on source drift."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_preview as b

ROOT = Path(__file__).resolve().parents[1]


class PreviewContract(unittest.TestCase):
    def test_accepted_excerpts_keep_copy_and_reject_bad_hash(self):
        path = ROOT / 'products/t2-peredacha-ispolnitelnoy-dokumentacii.html'
        text = path.read_text()
        self.assertEqual(b.render(path, b.catalog()), (text, ''))
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / path.name
            probe.write_text(text.replace('data-source-sha256="', 'data-source-sha256="0', 1))
            self.assertTrue(b.render(probe, b.catalog())[1])

    def test_full_inventory_rejects_missing_file(self):
        path = ROOT / 'products/t3-odnostoronniy-akt-i-zachet.html'
        text = path.read_text()
        self.assertEqual(b.render(path, b.catalog()), (text, ''))
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / path.name
            probe.write_text(text.replace('01-poryadok-deystviy.docx', '01-missing.docx'))
            self.assertIn('перечень файлов разошёлся', b.render(probe, b.catalog())[1])


if __name__ == '__main__':
    unittest.main()
