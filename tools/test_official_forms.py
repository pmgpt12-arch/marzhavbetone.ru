#!/usr/bin/env python3
"""Stop release when an official-form label loses its source fields or mirror."""
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def body(data):
    with ZipFile(BytesIO(data)) as z:
        root=ET.fromstring(z.read('word/document.xml'))
    text=' '.join((e.text or '') for e in root.iter(W+'t'))
    tables=[len(row.findall(W+'tc')) for tbl in root.iter(W+'tbl') for row in tbl.findall(W+'tr')]
    return text,tables

def check():
    specs={
      '01-zakrytie-rabot':(19,['01-ks-2.docx','02-ks-3.docx'],'tools/reports/p1-final-delivery-20261008/p1-value-edition.zip'),
      '02-dopraboty-bez-poter':(15,['04-akt-skrytyh-rabot.docx'],'tools/reports/official-forms-20261009/p2-delivery.zip')}
    for slug,(count,forms,reference) in specs.items():
        base=ROOT/'products-storage'/slug
        mirror=ROOT/'products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety'/slug
        excluded={'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'}
        files={p.name:p.read_bytes() for p in base.iterdir() if p.is_file() and p.name not in excluded}
        assert len(files)==count,(slug,len(files))
        for name in files:
            assert (mirror/name).read_bytes()==files[name],(slug,name,'mirror')
        with ZipFile(ROOT/reference) as z:
            assert set(z.namelist())==set(files)
            for name,content in files.items():assert z.read(name)==content,(slug,name,'archive')
        for name in forms:
            text,tables=body(files[name])
            if name.startswith('01-ks'):
                assert '0322005' in text and 8 in tables and 'единичной расценки' in text
            elif name.startswith('02-ks'):
                assert '0322001' in text and 6 in tables and 'отчетный период' in text
            else:
                assert '344/пр' in text and 'Рекомендуемый образец' in text
                assert all(f'{i}. ' in text for i in range(1,8))
                assert 'Приложения' in text and 'Подписи представителей' in text
    print('official form structure, inventory, mirrors and archives: PASS')

if __name__=='__main__':check()
