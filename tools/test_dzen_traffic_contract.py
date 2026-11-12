#!/usr/bin/env python3
"""Regression checks for Dzen reader-to-site links and brand identity."""
import re
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import build_rss as feed

TARGETS = {
    "zakazchik-ne-oplachivaet-vypolnennye-raboty": "dengi",
    "proverka-ks-2-pered-sdachey": "vozvrat-ks",
    "dopolnitelnye-raboty-v-stroitelstve": "dop-raboty",
    "vozvrat-garantiynogo-uderzhaniya": "uderzhaniya",
}
NS = "{http://purl.org/rss/1.0/modules/content/}encoded"

def item(slug):
    return {
        "title": "Проверенный материал",
        "link": f"{feed.SITE}/articles/{slug}.html",
        "date": datetime(2026, 11, 12, tzinfo=timezone.utc),
        "category": "Практика",
        "description": "Проверка документов подрядчика",
        "body": "<p>Самостоятельный практический разбор.</p>",
        "image": None,
        "image_type": "",
    }

class DzenTrafficContract(unittest.TestCase):
    def test_channel_brand(self):
        root = ET.fromstring(feed.build([item("example")]))
        self.assertEqual(root.findtext("channel/title"), "На стороне подрядчика")

    def test_four_topic_links_and_stable_identifiers(self):
        for slug, target in TARGETS.items():
            with self.subTest(slug=slug):
                source = item(slug)
                result = ET.fromstring(feed.build([source])).find("channel/item")
                body = result.findtext(NS)
                self.assertIn(f'href="{feed.SITE}/materialy/{target}.html"', body)
                self.assertNotIn("Марже в бетоне", body)
                self.assertEqual(result.findtext("link"), source["link"])
                self.assertEqual(result.findtext("guid"), source["link"])
                self.assertNotIn("utm_", body)
                self.assertTrue((feed.ROOT / "materialy" / f"{target}.html").is_file())

    def test_unmapped_article_uses_its_own_page(self):
        source = item("another-topic")
        result = ET.fromstring(feed.build([source])).find("channel/item")
        body = result.findtext(NS)
        self.assertIn(f'href="{source["link"]}"', body)
        self.assertNotIn(f'href="{feed.SITE}/"', body)
        self.assertNotIn("Марже в бетоне", body)

    def test_relative_links_resolve_against_source_article(self):
        html = '<main><p>Разбор <a href="../materialy/dengi.html?utm_source=old&amp;section=proof">проверки</a> и <a href="#documents">документов</a>.</p></main>'
        origin = f"{feed.SITE}/articles/source.html"
        result = feed.article_body(html, origin)
        self.assertIn(f'href="{feed.SITE}/materialy/dengi.html?section=proof"', result)
        self.assertIn(f'href="{origin}#documents"', result)
        self.assertNotIn("utm_", result)
        self.assertFalse(re.search(r'href="(?:/|\.\.?/|#)', result))

if __name__ == "__main__":
    unittest.main()
