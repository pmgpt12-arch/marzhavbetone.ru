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
    check_repackaged_forms()
    print('official form structure, inventory, mirrors and archives: PASS')


def normalized(text):
    import re
    return re.sub(r'\s+', ' ', text).strip()

def check_repackaged_forms():
    import json
    source_dir=ROOT/'tools/reports/repackage-20261010'
    official=normalized(' '.join(json.loads((source_dir/'aosr-source.json').read_text())))
    for slug,name in [('05-ks-bez-vozvrata','03-akt-skrytyh-rabot.docx'),('08-pto-bez-zamechaniy','31-pyat-aktov-skrytyh-rabot.docx')]:
        text,_=body((ROOT/'products-storage'/slug/name).read_bytes())
        text=normalized(text)
        assert text.count(official)==5,(slug,'five complete AOSR forms required')
        assert text.count('(фамилия, инициалы) (подпись)')==25,(slug,'signature blocks')
        assert 'Подписи всех трех сторон обязательны' not in text
        assert '[Шаблон' not in text
    path=ROOT/'products-storage/08-pto-bez-zamechaniy/35-obshiy-zhurnal-rabot.xlsx'
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(path) as z:
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        names=[x.attrib['name'] for x in wb.findall('s:sheets/s:sheet',ns)]
        assert names==['Титульный лист']+[f'Раздел {i}' for i in range(1,7)],names
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[normalized(''.join(x.itertext())) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        values=[]
        for filename in z.namelist():
            if not filename.startswith('xl/worksheets/sheet') or not filename.endswith('.xml'):continue
            xml=ET.fromstring(z.read(filename))
            for cell in xml.findall('.//s:c',ns):
                if cell.attrib.get('t')=='s':
                    v=cell.find('s:v',ns)
                    if v is not None:values.append(shared[int(v.text)])
                elif cell.attrib.get('t')=='str':
                    v=cell.find('s:v',ns)
                    if v is not None:values.append(normalized(v.text or ''))
                elif cell.attrib.get('t')=='inlineStr':
                    values.append(normalized(''.join(cell.find('s:is',ns).itertext())))
        source=json.loads((source_dir/'journal-source.json').read_text())
        for line,text in source:
            if ' | ' in text and text.lstrip().startswith('№'):
                for label in text.split('|'):
                    assert normalized(label) in values,('1026/pr missing header',line,label)
        assert any('1026/пр' in v for v in values)
        assert not any('Рабочий журнал производства работ' in v for v in values)

if __name__=='__main__':check()

