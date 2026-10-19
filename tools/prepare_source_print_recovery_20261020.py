#!/usr/bin/env python3
"""Preserve old-worker capability probe and prepare fresh source-print jobs."""
from pathlib import Path
import hashlib, json, shutil, urllib.request, xml.etree.ElementTree as E

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = REPO / 'tools/candidates/remaining-batch-r3-20261018/evidence/native-final-20261019'


def run():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = opener.open('http://192.168.1.72:8765/finish-office.ps1', timeout=10).read()
    assert data == (ROOT / 'finish-office.ps1').read_bytes()
    p = OUT / 'bootstrap-route-recovery-20261020.json'; result = json.loads(p.read_text())
    result.update(status='SERVICE_RESTART_AND_HTTP_SHA_PASS', helper_sha256=hashlib.sha256(data).hexdigest(), actual_peer_71_redownload='PENDING')
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('HELPER_HTTP_SHA_PASS', result['helper_sha256'])
    ident = 'r3i-source-print-preflight-20261019'; target = OUT / 'worker-capability-probe-20261020'; target.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'native' / ident / 'job.xml', target / 'job.xml')
    shutil.copyfile(ROOT / 'results/native' / ident / 'report.xml', target / 'report.xml')
    report = E.parse(target / 'report.xml').getroot(); assert report.get('status') == 'PASS'
    assert not any(c.get('name') == 'p1source:export_source_first' for c in report.findall('check'))
    assert not report.findall('print_preflight')
    (target / 'classification.json').write_text(json.dumps({
        'status': 'OPENING_PASS_CAPABILITIES_MISSING', 'classification': 'DEPENDENCY_RUNTIME_HARNESS',
        'missing': ['export_source_first check', 'print_preflight states'],
        'scope': 'Read-only probe confirms old worker ignores new opt-in attributes. Not a customer-file failure.'}, indent=2) + '\n')
    for old, new in [('r3i-source-print-preflight-20261019', 'r3n-source-print-preflight-20261020'),
                     ('r3i-original-xls-source-print-20261019', 'r3n-original-xls-source-print-20261020')]:
        source = ROOT / 'native' / old; destination = ROOT / 'native' / new
        job = E.parse(source / 'job.xml').getroot(); job.set('id', new)
        if destination.exists():
            assert E.tostring(E.parse(destination / 'job.xml').getroot()) == E.tostring(job)
        else:
            destination.mkdir()
            for file in job.findall('file'):
                shutil.copyfile(source / file.get('name'), destination / file.get('name'))
            E.ElementTree(job).write(destination / 'job.xml', encoding='utf-8', xml_declaration=True)
        out = OUT / 'prepared-jobs' / new; out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(destination / 'job.xml', out / 'job.xml')
        print('PREPARED_FRESH_JOB', new)


if __name__ == '__main__': run()
