#!/usr/bin/env python3
"""Bind successful input-only scenario receipts to current buyer source SHAs."""
from pathlib import Path
from hashlib import sha256
import json, xml.etree.ElementTree as E

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
OUT = BASE / 'evidence/native-final-20261019'


def collect():
    qualified = []; superseded = []
    for folder, prefix in [('calculation-fixtures', 'r3h-calc-fixtures'),
                           ('p8-warning-layout', 'r3l-p8-warning-layout')]:
        directory = OUT / folder
        archive = OUT / ('calculation-current-proofs.tar.xz' if folder == 'calculation-fixtures' else 'p8-warning-layout-proofs.tar.xz')
        archive_sha = sha256(archive.read_bytes()).hexdigest()
        manifest = json.loads((directory / 'fixture-manifest.json').read_text())
        summary = json.loads((directory / 'summary.json').read_text())
        assert summary['status'] == 'PASS'
        jobs = []
        for entry in summary['groups']:
            assert entry['status'] == 'PASS' and not entry['failed_checks'] and entry['job'].startswith(prefix)
            path = directory / entry['job']
            job = E.parse(path / 'job.xml').getroot(); report = E.parse(path / 'report.xml').getroot()
            assert report.get('status') == 'PASS' and job.get('id') == report.get('job') == entry['job']
            jobs.append((path, job, report))
        for row in manifest['records']:
            source = BASE / 'checkpoint-working' / row['sku'] / row['file']
            current = sha256(source.read_bytes()).hexdigest()
            if current != row['source_sha256']:
                superseded.append({'name': row['name'], 'old_source_sha256': row['source_sha256'], 'current_source_sha256': current})
                continue
            if not row['inputs']: continue  # Exact source copy is an opening proof, not a scenario.
            probes = []
            for sheet, expected in row['probes'].items():
                found = []
                for path, job, report in jobs:
                    for file in job.findall('file'):
                        if file.get('name') != row['name'] + '.xlsx' or file.get('sheet') != sheet: continue
                        assert file.get('sha256') == row['fixture_sha256']
                        tag = file.get('tag'); case = file.find('case')
                        assert case.get('name') == row['name']
                        wanted = {address: ('text' if isinstance(value, str) else 'number', str(value)) for address, value in expected.items()}
                        actual = {e.get('cell'): (e.get('kind'), e.get('value')) for e in case.findall('expect')}
                        assert wanted == actual and len(actual) == len(case.findall('expect'))
                        checks = [c for c in report.findall('check') if c.get('name', '').startswith(tag + ':')]
                        assert len(checks) == len(expected) + 3 and all(c.get('pass', '').lower() == 'true' for c in checks)
                        for suffix in ['input_sha', 'source_unchanged']:
                            check = report.find("check[@name='" + tag + ':' + suffix + "']")
                            assert check.get('actual') == row['fixture_sha256']
                        pdf = path / (tag + '-filled.pdf'); assert pdf.read_bytes().startswith(b'%PDF-')
                        found.append({'sheet': sheet, 'job': job.get('id'), 'tag': tag,
                                      'expected_values': len(expected), 'checks': len(checks),
                                      'pdf_sha256': sha256(pdf.read_bytes()).hexdigest(),
                                      'archive': archive.name, 'archive_sha256': archive_sha,
                                      'report_member': str((path / 'report.xml').relative_to(directory)),
                                      'report_sha256': sha256((path / 'report.xml').read_bytes()).hexdigest(),
                                      'job_sha256': sha256((path / 'job.xml').read_bytes()).hexdigest()})
                assert len(found) == 1, (row['name'], sheet, len(found))
                probes.extend(found)
            qualified.append({'name': row['name'], 'sku': row['sku'], 'file': row['file'],
                              'source_sha256': current, 'fixture_sha256': row['fixture_sha256'],
                              'input_preservation': row['preservation'], 'probes': probes})
    result = {'status': 'PASS_CURRENT_SOURCE_SCENARIOS_ONLY', 'scenarios': len(qualified),
              'sheet_probes': sum(len(r['probes']) for r in qualified),
              'expected_values': sum(p['expected_values'] for r in qualified for p in r['probes']),
              'native_checks': sum(p['checks'] for r in qualified for p in r['probes']),
              'scope': 'Independent input-only fixtures preserving the qualified source formulas and features. Native Excel expected-value checks; UI typing/paste and general print acceptance are separate.',
              'native_source_print': 'PENDING_WORKER_UPDATE', 'superseded_scenarios': superseded, 'records': qualified}
    assert (result['scenarios'], result['sheet_probes'], result['expected_values']) == (14, 22, 60), result
    (OUT / 'calculation-current-source-index.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('CURRENT_CALCULATIONS_PASS', result['scenarios'], result['sheet_probes'], result['expected_values'], result['native_checks'])


if __name__ == '__main__': collect()
