#!/usr/bin/env python3
"""Run bounded native expectations on independently authored input-only fixtures."""
from pathlib import Path
from hashlib import sha256
import json, shutil, time, xml.etree.ElementTree as E
from submit_office_review_job import submit

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
FIXTURES = Path('/tmp/mb-r3/calculation-fixtures-20261019')
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = BASE / 'evidence/native-final-20261019/calculation-fixtures'


def run():
    manifest = json.loads((FIXTURES / 'fixture-manifest.json').read_text())
    assert len(manifest['records']) == 13
    probes = []
    for row in manifest['records']:
        source = BASE / 'checkpoint-working' / row['sku'] / row['file']
        fixture = FIXTURES / (row['name'] + '.xlsx')
        assert sha256(source.read_bytes()).hexdigest() == row['source_sha256']
        assert sha256(fixture.read_bytes()).hexdigest() == row['fixture_sha256']
        for sheet, expected in row['probes'].items():
            probes.append((row, sheet, expected))
    assert len(probes) == 20
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / 'fixture-manifest.json', OUT / 'fixture-manifest.json')
    summary = []
    deadline = time.monotonic() + 1000
    for start in range(0, len(probes), 4):
        ident = 'r3h-calc-fixtures-g' + str(start // 4 + 1).zfill(2) + '-20261019'
        job = E.Element('job', id=ident, qa_only='true', scope='INPUT_ONLY_DISPOSABLE_FIXTURES_NOT_BUYER_SHAS')
        group = probes[start:start + 4]
        for i, (row, sheet, expected) in enumerate(group, start):
            file = E.SubElement(job, 'file', name=row['name'] + '.xlsx', tag='c' + str(i).zfill(2),
                                sheet=sheet, sha256=row['fixture_sha256'])
            case = E.SubElement(file, 'case', name=row['name'])
            for address, value in expected.items():
                E.SubElement(case, 'expect', cell=address, kind='text' if isinstance(value, str) else 'number', value=str(value))
        directory = ROOT / 'native' / ident
        if (directory / 'job.xml').exists():
            assert E.tostring(E.parse(directory / 'job.xml').getroot()) == E.tostring(job)
        else:
            directory.mkdir()
            for row, sheet, expected in group:
                name = row['name'] + '.xlsx'
                shutil.copyfile(FIXTURES / name, directory / name)
            E.ElementTree(job).write(directory / 'job.xml', encoding='utf-8', xml_declaration=True)
        receipt = ROOT / 'results/native' / ident / 'report.xml'
        if not receipt.exists():
            submit(ROOT, 'native', directory)
            print('SUBMITTED', ident, flush=True)
            stop = min(deadline, time.monotonic() + 240)
            while not receipt.exists() and time.monotonic() < stop:
                time.sleep(3)
        if not receipt.exists():
            raise SystemExit('RECEIPT_TIMEOUT; do not replace current.xml: ' + ident)
        report = E.parse(receipt).getroot()
        assert report.get('job') == ident
        target = OUT / ident; target.mkdir(exist_ok=True)
        shutil.copyfile(directory / 'job.xml', target / 'job.xml')
        for path in receipt.parent.iterdir():
            if path.is_file(): shutil.copyfile(path, target / path.name)
        failures = [dict(c.attrib) for c in report.findall('check') if c.get('pass', '').lower() != 'true']
        summary.append({'job': ident, 'status': report.get('status'),
                        'checks': len(report.findall('check')), 'failed_checks': failures})
        (OUT / 'summary.json').write_text(json.dumps({'status': 'RUNNING' if report.get('status') == 'PASS' else 'FAIL',
              'scope': 'Controlled input-only fixtures; exact buyer SHAs qualified separately for opening.',
              'groups': summary}, ensure_ascii=False, indent=2) + '\n')
        print('RECEIPT', ident, report.get('status'), 'CHECKS', len(report.findall('check')), flush=True)
        if report.get('status') != 'PASS':
            print(receipt.read_text(), flush=True)
            raise SystemExit('STOP_INSPECT_CALCULATION_FAILURE; no automatic retry')
    p = OUT / 'summary.json'; final = json.loads(p.read_text()); final['status'] = 'PASS'; final['fixtures'] = 13; final['sheet_probes'] = 20
    p.write_text(json.dumps(final, ensure_ascii=False, indent=2) + '\n')
    print('NATIVE_CALCULATION_FIXTURES_PASS', 13, 'SHEET_PROBES', 20, flush=True)


if __name__ == '__main__':
    run()
