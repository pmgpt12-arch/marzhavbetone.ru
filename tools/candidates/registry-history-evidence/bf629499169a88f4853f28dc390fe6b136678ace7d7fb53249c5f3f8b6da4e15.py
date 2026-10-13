#!/usr/bin/env python3
"""Repair one OOXML row dimension after exact native PDF review. No formulas/cells/styles changed."""
from pathlib import Path
from xml.etree import ElementTree as E
import hashlib, json, os, zipfile
D = Path(__file__).resolve().parent
SOURCE = D/'14-raschet-procentov-395-gk-corexml-compat.xlsx'
OUT = D/'14-raschet-procentov-395-gk-native-header.xlsx'
RECEIPT = D/'native-header-candidate.json'
EXPECTED_SHA = '044d9aa899b2278c9fe6c525f4b54e3f8ea07d4b12d755a8df145741756ee8c2'
SHEET = 'xl/worksheets/sheet4.xml'
OLD = b'<row r="15" ht="38" customHeight="1">'
NEW = b'<row r="15" ht="54" customHeight="1">'
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def height_gate(payload):
    root = E.fromstring(payload)
    row = next(r for r in root.iter(NS+'row') if r.get('r') == '15')
    assert row.get('ht') == '54' and row.get('customHeight') == '1', 'NATIVE_HEADER_HEIGHT_REGRESSION'
    return True

def main():
    assert not OUT.exists() and not RECEIPT.exists(), 'DUPLICATE_STOP'
    assert sha(SOURCE) == EXPECTED_SHA, 'SOURCE_SHA_DRIFT'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None, 'SOURCE_ZIP_CRC'
        names = z.namelist(); before = {n:z.read(n) for n in names}
        assert len(names) == len(set(names)) == 15, 'SOURCE_MEMBERS'
        assert before[SHEET].count(OLD) == 1, 'EXACT_ROW_ANCHOR_DRIFT'
        patched = before[SHEET].replace(OLD, NEW, 1)
        assert patched.replace(NEW, OLD, 1) == before[SHEET], 'NON_ROW_CHANGE'
        height_gate(patched)
        try:
            height_gate(before[SHEET])
        except AssertionError:
            regression_detected = True
        else:
            raise AssertionError('OLD_CLIPPED_ROW_NOT_REJECTED')
        tmp = OUT.with_suffix('.tmp')
        assert not tmp.exists(), 'TEMP_EXISTS'
        with zipfile.ZipFile(tmp,'w') as dest:
            dest.comment = z.comment
            for info in z.infolist():
                dest.writestr(info,patched if info.filename == SHEET else before[info.filename])
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None and z.namelist() == names, 'OUTPUT_ZIP'
        after = {n:z.read(n) for n in names}
    changed = [n for n in names if before[n] != after[n]]
    assert changed == [SHEET], 'EXTRA_PART_CHANGE'
    for n in names:
        if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'):
            a = E.fromstring(before[n]); b = E.fromstring(after[n])
            if n == SHEET:
                next(r for r in b.iter(NS+'row') if r.get('r') == '15').set('ht','38')
            assert E.tostring(a) == E.tostring(b), 'NON_HEIGHT_XML_CHANGE'
    formulas = sum(len(list(E.fromstring(v).iter(NS+'f'))) for n,v in after.items() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'))
    assert formulas == 251 and sha(SOURCE) == EXPECTED_SHA, 'FORMULAS_OR_SOURCE_DRIFT'
    os.replace(tmp,OUT)
    record = {'status':'PASS_SINGLE_ROW_DIMENSION_REPAIR_ONLY','registry_id':'P1-CAND-395-NATIVE-HEADER-20261013','parent_registry_id':'P1-CAND-395-COREXML-20261013','source_path':str(SOURCE),'source_sha256':EXPECTED_SHA,'candidate_path':str(OUT),'candidate_sha256':sha(OUT),'candidate_bytes':OUT.stat().st_size,'defect':'Native Excel 2016 PDF page 5 clips top of example sheet G15 heading','source_native_pdf_sha256':'9e1f23e459fb2c4465c99e95fd2743f0ca6ff7f2400612f6fd4cb73165b146d0','changed_zip_parts':changed,'only_edit':{'worksheet':'Пример заполнения','row':15,'height_before_pt':38,'height_after_pt':54},'other_zip_payloads_identical':14,'all_cell_text_values_formulas_styles_validation_and_protection_unchanged':True,'formula_count':251,'negative_old_height_detected':regression_detected,'native_office':'PENDING_NEW_SHA','visual':'PENDING_NEW_SHA','normative_buyer_G1_G8':'OPEN','release':'BLOCKED','source_mutations':0}
    temp = RECEIPT.with_suffix('.tmp')
    with temp.open('x',encoding='utf-8') as f:
        json.dump(record,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp,RECEIPT)
    assert json.loads(RECEIPT.read_text()) == record
    print(json.dumps(record,ensure_ascii=False)); print('RECEIPT_SHA',sha(RECEIPT))
if __name__ == '__main__': main()
