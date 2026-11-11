#!/usr/bin/env python3
"""Independent read-only gate: exact P1 numeric fixtures, native facts, and scoped history.
No fixture creation and no Office, model, network, or product-file writes.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET
import copy, hashlib, io, json, re, zipfile

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'tools/candidates/p1-395-native-numeric-20261013/index.json'
SOURCE=ROOT/'tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx'
SHA='8ec79d20d15a8d4888b2ae69130f374d1a8c6039cfdf2ba71044d7010ff5ce34'
NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def load_zip(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None and len(z.namelist())==len(set(z.namelist())), 'ZIP_INTEGRITY'
        return {n:z.read(n) for n in z.namelist()}
def evidence_bytes(ref):
    p=(ROOT/ref['archive_path']).resolve()
    assert ROOT in p.parents and p.is_file(), 'EVIDENCE_MISSING_OR_ESCAPE'
    raw=p.read_bytes()
    assert digest(raw)==ref['sha256'] and len(raw)==ref['bytes'], 'EVIDENCE_HASH_DRIFT'
    return raw

def fixture_delta(source,fixture,edits):
    assert list(source)==list(fixture) and len(source)==15, 'PACKAGE_MEMBER_DRIFT'
    assert {n for n in source if source[n]!=fixture[n]}=={'xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml'}, 'PACKAGE_DIFF_SCOPE'
    for n in ('xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml'):
        reconstructed=fixture[n].decode('utf-8')
        for edit in edits:
            if edit['part']!=n:continue
            before=ET.fromstring(edit['before_xml']);after=ET.fromstring(edit['after_xml'])
            assert before.attrib==after.attrib and before.get('r')==edit['address'] and len(before)==0, 'NONBLANK_OR_STYLE_EDIT'
            assert len(after)==1 and after[0].tag=='v' and Decimal(after[0].text)==Decimal(edit['value']), 'NOT_NUMERIC_VALUE_ONLY'
            assert reconstructed.count(edit['after_xml'])==1, 'INPUT_NODE_NOT_UNIQUE'
            reconstructed=reconstructed.replace(edit['after_xml'],edit['before_xml'],1)
        assert reconstructed.encode('utf-8')==source[n], 'NONINPUT_OR_FORMULA_MUTATION'
    assert sum(len(list(ET.fromstring(v).iter(NS+'f'))) for n,v in fixture.items() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n))==251, 'FORMULA_COUNT'

def value_matches(actual,want):
    if want['kind']=='number':return abs(Decimal(str(actual))-Decimal(want['value']))<=Decimal('0.0000001')
    if want['kind']=='blank':return actual in (None,'','<null>')
    return actual==want['value']

def native_values(report,tag,spec,fixture_sha):
    assert report.get('status')=='PASS' and report.get('excel_version')=='16.0' and report.get('excel_build')=='4324', 'NATIVE_STATUS_OR_ENVIRONMENT'
    all_checks=report.findall('check');assert len(all_checks)==58
    checks={c.get('name'):c for c in all_checks if c.get('name','').startswith(tag+':')}
    assert len(checks)==len(spec['expected_calc'])+4, 'NATIVE_CHECK_COUNT'
    assert all(c.get('pass')=='True' for c in checks.values()), 'FAILED_NATIVE_CHECK'
    assert checks[tag+':input_sha'].get('actual')==checks[tag+':source_unchanged'].get('actual')==fixture_sha, 'NATIVE_INPUT_MISMATCH'
    assert checks[tag+':sheet_protected'].get('actual')==checks[tag+':sheet_protected'].get('expected')=='False', 'PROTECTION_EXPECTATION'
    for address,want in spec['expected_calc'].items():
        c=checks[tag+':'+spec['id']+':'+address]
        assert c.get('expected')==want['kind']+':'+want['value'], 'NATIVE_EXPECTED_VALUE_CHANGED'
        actual=c.get('actual');actual=actual.split(':',1)[1] if actual and actual.startswith('System.') else actual
        assert value_matches(actual,want), 'NATIVE_ACTUAL_VALUE_NOT_EQUAL'

def cached_values(raw,spec):
    parts=load_zip(raw)
    ss=[''.join(e.itertext()) for e in ET.fromstring(parts['xl/sharedStrings.xml'])] if 'xl/sharedStrings.xml' in parts else []
    count=0
    for part,expected in [('xl/worksheets/sheet2.xml',spec['expected_calc']),('xl/worksheets/sheet3.xml',spec['expected_result'])]:
        cells={c.get('r'):c for c in ET.fromstring(parts[part]).iter(NS+'c')}
        for address,want in expected.items():
            c=cells[address];v=c.find(NS+'v');actual=v.text if v is not None else ''
            assert c.get('t')!='e', 'NATIVE_EXCEL_ERROR_VALUE'
            if c.get('t')=='s':actual=ss[int(actual)]
            elif c.get('t')=='inlineStr':actual=''.join(c.find(NS+'is').itertext())
            assert value_matches(actual,want), 'CACHED_OUTPUT_MISMATCH'
            count+=1
    return count

def reject(fn,label):
    try:fn()
    except (AssertionError,ValueError,KeyError):return
    raise AssertionError('NEGATIVE_CASE_UNDETECTED:'+label)

def run():
    index=json.loads(INDEX.read_text());registry=json.loads((ROOT/'products-storage/ARTIFACT-REGISTRY.json').read_text())
    assert index['status']=='PASS_FOUR_DERIVED_NATIVE_NUMERIC_FIXTURES_ONLY' and index['source_sha256']==digest(SOURCE.read_bytes())==SHA
    assert index['product_g1_g8']=='OPEN' and index['release']=='BLOCKED'
    rows=[r for r in registry['change_history']['records'] if r['record_id'] in index['records']]
    assert len(rows)==4 and [r['record_sha256'] for r in rows]==index['record_hashes'], 'HISTORY_OR_RECORD_SCOPE'
    plan=json.loads((ROOT/index['plan_archive']).read_text());report=ET.fromstring((ROOT/index['native_report_archive']).read_bytes())
    assert report.get('job')==index['job_id'] and len(plan['fixtures'])==4
    counts=0
    for row,spec in zip(rows,plan['fixtures']):
        assert row['role']=='report_evidence_not_nominated' and row['release_status']=='BLOCKED' and row['resume']['g1_g8_status']=='OPEN', 'FALSE_PRODUCT_NOMINATION'
        assert row['input']['sha256']==SHA
        source=load_zip(evidence_bytes(row['input']));fixture_raw=evidence_bytes(row['output']);fixture=load_zip(fixture_raw)
        fixture_delta(source,fixture,row['delta']['addresses'])
        refs={e['evidence_id']:e for e in row['evidence']}
        for e in refs.values():evidence_bytes(e)
        assert evidence_bytes(refs['native'])==(ROOT/index['native_report_archive']).read_bytes()
        gate=row['gates'][0];assert gate['gate_id']=='native_numeric_fixture' and gate['status']=='PASS' and gate['subject_sha256']==row['output']['sha256'] and gate['accepted_scope_only'] is True
        assert gate['contract']['expected_calc']==spec['expected_calc'] and gate['contract']['expected_result']==spec['expected_result'], 'SCOPE_EXPECTATION_DRIFT'
        native_values(report,row['execution']['tag'],spec,row['output']['sha256'])
        counts+=cached_values(evidence_bytes(refs['filled-xlsx']),spec)
        for o in spec['oracle']:
            calculated=(Decimal(o['principal'])*Decimal(o['rate_percent'])*Decimal(o['days'])/(100*Decimal(o['year_days']))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            assert calculated==Decimal(o['rounded_interest']), 'DECIMAL_ORACLE'
        if spec['oracle']:
            assert sum(Decimal(o['rounded_interest']) for o in spec['oracle'])==Decimal(spec['expected_calc']['G45']['value']), 'ORACLE_TOTAL'
    assert counts==66, 'CACHED_ASSERTION_COUNT'
    first=rows[0];s=plan['fixtures'][0];tag=first['execution']['tag'];fsha=first['output']['sha256']
    bad=copy.deepcopy(report);bad.set('status','FAIL');reject(lambda:native_values(bad,tag,s,fsha),'false_report_status')
    bad=copy.deepcopy(report);next(c for c in bad.findall('check') if c.get('name')==tag+':'+s['id']+':G4').set('actual','System.Double:1');reject(lambda:native_values(bad,tag,s,fsha),'wrong_actual_kept_true')
    wrong=copy.deepcopy(s);wrong['expected_calc']['G4']['value']='1';reject(lambda:native_values(report,tag,wrong,fsha),'wrong_expected')
    reject(lambda:native_values(report,tag,s,'0'*64),'wrong_fixture_sha')
    source=load_zip(evidence_bytes(first['input']));fixture=load_zip(evidence_bytes(first['output']));fixture['xl/worksheets/sheet2.xml']=fixture['xl/worksheets/sheet2.xml'].replace(b'<f>',b'<f>1+',1);reject(lambda:fixture_delta(source,fixture,first['delta']['addresses']),'formula_modified')
    print('P1_NATIVE_NUMERIC_EVIDENCE_PASS: 4 derived fixtures; 58 native checks; 66 cached checks (not additive); 5 negative cases; no native replay or G1-G8 claim')
    return 0

if __name__=='__main__':raise SystemExit(run())
