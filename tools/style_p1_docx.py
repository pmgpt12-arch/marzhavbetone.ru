#!/usr/bin/env python3
"""Bring P1 DOCX accents to graphite/gold without changing text or layout."""
from collections import Counter
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import hashlib
import shutil
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "products-storage/01-zakrytie-rabot"
MIRROR = ROOT / "products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety/01-zakrytie-rabot"
STYLE_COLORS = {b"2E74B5": b"34383B", b"1F4D78": b"34383B", b"0563C1": b"34383B"}
BODY_COLORS = {b"E85D22": b"B49A65"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def text_signature(blob):
    with ZipFile(BytesIO(blob)) as archive:
        return tuple(
            (name, tuple(node.text or "" for node in ET.fromstring(archive.read(name)).iter(f"{W}t")))
            for name in archive.namelist()
            if name.startswith("word/") and name.endswith(".xml")
        )

for path in sorted(BASE.glob("*.docx")):
    before = path.read_bytes()
    out = BytesIO()
    with ZipFile(BytesIO(before)) as original, ZipFile(out, "w") as rewritten:
        for entry in original.infolist():
            data = original.read(entry.filename)
            colors = STYLE_COLORS if entry.filename == "word/styles.xml" else BODY_COLORS if entry.filename == "word/document.xml" else {}
            for source, target in colors.items():
                data = data.replace(source, target)
            if entry.filename == "word/styles.xml":
                data = data.replace(b'w:bottom w:val="single" w:sz="8" w:space="4" w:color="4F81BD" w:themeColor="accent1"', b'w:bottom w:val="single" w:sz="8" w:space="4" w:color="B49A65"')
            rewritten.writestr(entry, data)
    after = out.getvalue()
    assert text_signature(before) == text_signature(after), path
    path.write_bytes(after)
    partner = MIRROR / path.name
    assert partner.is_file(), partner
    partner.write_bytes(after)
    print(path.name, hashlib.sha256(after).hexdigest()[:16])
