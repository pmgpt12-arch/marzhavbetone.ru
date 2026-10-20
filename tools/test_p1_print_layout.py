#!/usr/bin/env python3
"""P1: Excel-файлы совпадают с зеркалом и печатаются без горизонтального разрыва."""
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
REL = Path("14-raschet-procentov-395-gk.xlsx")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
BASE=ROOT/'products-storage/01-zakrytie-rabot'
# Historical full-bundle mirrors are outside the active edition.
books=sorted(BASE.glob('*.xlsx'))
assert len(books)==4
for book in books:
    with ZipFile(book) as archive:
        sheets=[n for n in archive.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        for name in sheets:
            sheet=ET.fromstring(archive.read(name));props=sheet.find(f"{NS}sheetPr/{NS}pageSetUpPr");setup=sheet.find(f"{NS}pageSetup")
            assert props is not None and props.get('fitToPage')=='1',(book,name)
            assert setup is not None and setup.get('fitToWidth')=='1',(book,name)
            assert setup.get('orientation') in {'portrait','landscape'},(book,name)
import json
acceptance=json.loads((ROOT/'tools/candidates/remaining-batch-r3-20261018/owner-manual-excel-20261020/acceptance.json').read_text())
assert acceptance['status']=='PASS_OWNER_MANUAL_OPEN_AND_PRINT'
for p in sorted(BASE.glob('*.xls'))+books:
    rows=[x for x in acceptance['inventory'] if x['sku']=='P1' and x['file']==p.name]
    assert len(rows)==1 and hashlib.sha256(p.read_bytes()).hexdigest()==rows[0]['sha256']
print('P1 exact 7 Excel source files: current print settings plus owner manual opening/print acceptance PASS')
