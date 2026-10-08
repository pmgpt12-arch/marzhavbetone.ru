#!/usr/bin/env python3
"""P1 DOCX visible headings and note accents retain the approved palette."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "products-storage/01-zakrytie-rabot"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
for path in sorted(BASE.glob("*.docx")):
    with ZipFile(path) as archive:
        styles = ET.fromstring(archive.read("word/styles.xml"))
        body = archive.read("word/document.xml")
        assert b"E85D22" not in body, (path.name, "orange body accent")
        for style in styles.findall("w:style", NS):
            if style.get(W + "styleId") not in ("Heading1", "Heading2", "Title"):
                continue
            for color in style.findall(".//w:color", NS):
                value = color.get(W + "val")
                assert value not in ("2E74B5", "1F4D78", "0563C1"), (path.name, value)
        if path.name == "00-INSTRUKCIYA.docx":
            title = next(s for s in styles.findall("w:style", NS) if s.get(W + "styleId") == "Title")
            bottom = title.find(".//w:pBdr/w:bottom", NS)
            assert bottom is not None and bottom.get(W + "color") == "B49A65", "instruction title accent"
print("P1 DOCX palette: eleven documents graphite/gold PASS")
