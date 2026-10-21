#!/usr/bin/env python3
"""Approved headers survive generation; wrong headers/targets fail closed."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
import build_nav
import check_nav
import link_audit

ROOT = Path(__file__).resolve().parents[1]


class NavigationContract(unittest.TestCase):
    def test_generator_preserves_every_published_header(self):
        data = yaml.safe_load(build_nav.ДАННЫЕ.read_text())
        for page in build_nav.страницы():
            rel = page.relative_to(ROOT).as_posix()
            header = build_nav.ШАПКА.search(page.read_text())[0]
            cart = build_nav.КОРЗИНА.search(header)
            generated = build_nav.собрать(data, rel, cart[0] if cart else None)
            self.assertEqual(header, generated, rel)

    def test_changed_home_header_and_missing_target_fail(self):
        original = (ROOT / 'index.html').read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / 'index.html'
            for content, targets, expected in (
                (original, True, 0),
                (original.replace('>Каталог</a>', '>Другой раздел</a>', 1), True, 1),
                (original, False, 1),
            ):
                page.write_text(content)
                with patch.object(check_nav, 'ROOT', root), \
                     patch.object(check_nav, 'страницы', return_value=[page]), \
                     patch.object(check_nav, 'цель_существует', return_value=targets), \
                     patch.object(sys, 'argv', ['check_nav']), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(check_nav.main(), expected)

    def test_evidence_html_is_outside_public_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tools' / 'evidence').mkdir(parents=True)
            (root / 'index.html').touch()
            (root / 'tools' / 'evidence' / 'old.html').touch()
            with patch.object(link_audit, 'ROOT', root):
                self.assertEqual(link_audit.site_html_files(), [root / 'index.html'])


if __name__ == '__main__':
    unittest.main()
