#!/usr/bin/env python3
"""P1: Excel-файлы совпадают с зеркалом и печатаются без горизонтального разрыва."""
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
REL = Path("14-raschet-procentov-395-gk.xlsx")
COPIES = [ROOT / "products-storage/01-zakrytie-rabot" / REL,
          ROOT / "products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety/01-zakrytie-rabot" / REL]
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

assert all(p.is_file() for p in COPIES), "одна из копий P1 отсутствует"
assert len({hashlib.sha256(p.read_bytes()).hexdigest() for p in COPIES}) == 1, "копии P1 различаются"
for book in COPIES:
    with ZipFile(book) as archive:
        for index in range(1, 5):
            sheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{index}.xml"))
            props = sheet.find(f"{NS}sheetPr/{NS}pageSetUpPr")
            setup = sheet.find(f"{NS}pageSetup")
            assert props is not None and props.get("fitToPage") == "1", (book, index, "fitToPage")
            assert setup is not None and setup.get("fitToWidth") == "1", (book, index, "fitToWidth")
            assert setup.get("fitToHeight") == "0", (book, index, "fitToHeight")
            expected = "landscape" if index in (2, 4) else "portrait"
            assert setup.get("orientation") == expected, (book, index, "orientation")
for name in ("06-zhurnal-obemov.xlsx", "07-reestr-zamechaniy.xlsx", "08-reestr-peredachi.xlsx"):
    paths = [ROOT / "products-storage/01-zakrytie-rabot" / name,
             ROOT / "products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety/01-zakrytie-rabot" / name]
    assert all(p.is_file() for p in paths), (name, "missing")
    assert len({hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}) == 1, (name, "copies differ")
    with ZipFile(paths[0]) as archive:
        for index, orientation in ((1, "landscape"), (2, "portrait")):
            sheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{index}.xml"))
            props = sheet.find(f"{NS}sheetPr/{NS}pageSetUpPr")
            setup = sheet.find(f"{NS}pageSetup")
            assert props is not None and props.get("fitToPage") == "1", (name, index, "fitToPage")
            assert setup is not None and setup.get("fitToWidth") == "1", (name, index, "fitToWidth")
            assert setup.get("orientation") == orientation, (name, index, "orientation")
print("P1 print layout: four Excel files, both copies, one-page width PASS")
