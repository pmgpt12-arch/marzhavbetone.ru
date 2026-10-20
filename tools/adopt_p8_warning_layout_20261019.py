#!/usr/bin/env python3
"""Adopt only the visually reviewed P8 row-height/page-break correction."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
from lxml import etree as E
import argparse, copy, json, shutil

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
OUT = BASE / 'evidence/native-final-20261019'
NAME = '09-raschet-otrabotannoy-chasti-avansa.xlsx'
OLD = 'cd7d962bdfd2f83c1469ba12b8877596876d3a7203aa5674bb6aecd9791dfff7'
NEW = '9ed4b9af3d1bc1d51bf8be93846c931972843eb7d2446074b29f7bb91b277ab4'
NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def digest(p): return sha256(p.read_bytes()).hexdigest()
def canon(x): return E.tostring(x, method='c14n')
def save(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def run(candidate, proofdir):
    target = BASE / 'checkpoint-working/P8' / NAME
    assert digest(target) == OLD and digest(candidate) == NEW
    visual = json.loads((OUT / 'p8-warning-layout-visual-review.json').read_text())
    assert visual['status'] == 'PASS_SCOPED_WARNING_LAYOUT_ONLY' and visual['source_sha256'] == NEW
    job = E.parse(str(proofdir / 'job.xml')).getroot()
    report = E.parse(str(proofdir / 'report.xml')).getroot()
    f = job.find("file[@tag='c07']")
    assert f is not None and f.get('sha256') == NEW
    assert report.get('status') == 'PASS' and report.get('job') == job.get('id')
    for name in ['input_sha', 'pdf_export', 'source_unchanged']:
        check = report.find("check[@name='c07:" + name + "']")
        assert check is not None and check.get('pass').lower() == 'true'
        if name != 'pdf_export': assert check.get('actual') == NEW
    changed = []
    with ZipFile(target) as a, ZipFile(candidate) as b:
        assert a.namelist() == b.namelist() and a.testzip() is None and b.testzip() is None
        for name in a.namelist():
            if a.read(name) == b.read(name): continue
            assert name in ['xl/worksheets/sheet3.xml', 'xl/worksheets/sheet4.xml'], name
            ra = E.fromstring(a.read(name)); rb = E.fromstring(b.read(name))
            last = 45 if name.endswith('3.xml') else 30
            aa = {int(r.get('r')): r for r in ra.findall('x:sheetData/x:row', NS)}
            bb = {int(r.get('r')): r for r in rb.findall('x:sheetData/x:row', NS)}
            assert set(aa) == set(bb)
            heights = []
            for row in aa:
                if aa[row].attrib == bb[row].attrib: continue
                assert 6 <= row <= last and float(bb[row].get('ht')) == 45
                before = dict(aa[row].attrib); after = dict(bb[row].attrib)
                for attr in ['ht', 'customHeight']: before.pop(attr, None); after.pop(attr, None)
                assert before == after
                heights.append(row)
                bb[row].attrib.clear(); bb[row].attrib.update(aa[row].attrib)
            assert heights == list(range(6, last + 1))
            for root in [ra, rb]:
                node = root.find('x:rowBreaks', NS)
                if node is not None: root.remove(node)
            assert canon(ra) == canon(rb), (name, 'change exceeds row heights and row breaks')
            changed.append({'part': name, 'height_pt': 45, 'rows': heights})
    assert len(changed) == 2
    proof = {'status': 'PASS', 'old_sha256': OLD, 'new_sha256': NEW,
             'scope': 'Only data-row heights and page breaks in two worksheets changed. All other package parts and canonical cell/formula/style/functional contents identical.',
             'changes': changed, 'current_source_opening_job': job.get('id'),
             'native_source_print': 'PENDING_WORKER_UPDATE', 'buyer_nomination': 'NOT_PERFORMED'}
    save(OUT / 'p8-warning-layout-preservation.json', proof)
    shutil.copyfile(candidate, target)
    checkpoint = BASE / 'evidence/working-checkpoint.json'
    data = json.loads(checkpoint.read_text())
    for row in data['inventory']:
        p = BASE / 'checkpoint-working' / row['sku'] / row['file']
        if row['sku'] == 'P8' and row['file'] == NAME:
            assert row['sha256'] == OLD
            row.update(sha256=NEW, bytes=p.stat().st_size)
        assert digest(p) == row['sha256'] and p.stat().st_size == row['bytes'], p
    assert len(data['inventory']) == 123
    data['native_office_final'] = '66 DOCX and 19 XLSX current exact SHAs opened/exported normally. Current scenario index recorded separately. Source print and original XLS qualification pending worker update.'
    save(checkpoint, data)
    save(BASE / 'staged-p8-warning-layout/STATUS.json', {
        'status': 'ADOPTED_WORKING_CANDIDATE_SOURCE_PRINT_PENDING', 'source_sha256': NEW,
        'files': ['P8/' + NAME], 'scope': 'Warning row heights and page breaks only; calculation and scoped message display PASS.',
        'buyer_acceptance': 'NOT_REQUESTED', 'publication': 'NOT_PERFORMED'})
    old_archive = BASE / 'owner-manual-review-20261019.json'
    data = json.loads(old_archive.read_text()); data['status'] = 'SUPERSEDED_NOT_FINAL'
    data['superseded_reason'] = 'Contains previous P13 row ordering and previous P8 warning row heights/page breaks. Never issue as the final candidate.'
    save(old_archive, data)
    print('ADOPTED_P8', NEW, target.stat().st_size, 'CHECKPOINT_123_HASHES_PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--opening-proof-directory', type=Path, required=True)
    args = parser.parse_args(); run(args.candidate, args.opening_proof_directory)
