#!/usr/bin/env python3
"""Run bounded native expectations on independently authored input-only fixtures."""
from pathlib import Path
from hashlib import sha256
import json, re, shutil, subprocess, tarfile, time, xml.etree.ElementTree as E
from submit_office_review_job import submit

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
FIXTURES = Path('/tmp/mb-r3/calculation-fixtures-20261019')
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = BASE / 'evidence/native-final-20261019/calculation-fixtures'
SOURCE_ROOT = BASE / 'checkpoint-working'
EXPECTED_FIXTURES = 13
EXPECTED_PROBES = 20
PREFIX = 'r3h-calc-fixtures'
ARCHIVE_STEM = 'calculation-current'


def run():
    manifest = json.loads((FIXTURES / 'fixture-manifest.json').read_text())
    assert len(manifest['records']) == EXPECTED_FIXTURES
    if 'complete' in manifest:
        assert manifest['complete'] and manifest['expected_count'] == EXPECTED_FIXTURES
    probes = []
    for row in manifest['records']:
        source = SOURCE_ROOT / row['sku'] / row['file']
        fixture = FIXTURES / (row['name'] + '.xlsx')
        assert sha256(source.read_bytes()).hexdigest() == row['source_sha256']
        assert sha256(fixture.read_bytes()).hexdigest() == row['fixture_sha256']
        for sheet, expected in row['probes'].items():
            probes.append((row, sheet, expected))
    assert len(probes) == EXPECTED_PROBES
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / 'fixture-manifest.json', OUT / 'fixture-manifest.json')
    summary = []
    deadline = time.monotonic() + 1000
    for start in range(0, len(probes), 4):
        ident = PREFIX + '-g' + str(start // 4 + 1).zfill(2) + '-20261019'
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
    p = OUT / 'summary.json'; final = json.loads(p.read_text()); final['status'] = 'PASS'; final['fixtures'] = EXPECTED_FIXTURES; final['sheet_probes'] = EXPECTED_PROBES
    p.write_text(json.dumps(final, ensure_ascii=False, indent=2) + '\n')
    print('NATIVE_CALCULATION_FIXTURES_PASS', EXPECTED_FIXTURES, 'SHEET_PROBES', EXPECTED_PROBES, flush=True)


def collect_print_evidence():
    """A calculation PASS is separate from display and source-print qualification."""
    summary = json.loads((OUT / 'summary.json').read_text())
    assert summary['status'] == 'PASS' and summary['fixtures'] == EXPECTED_FIXTURES
    normalize = lambda value: re.sub(r'\s+', ' ', value).strip()
    scans = []
    checks = 0
    expected_values = 0
    for directory in sorted(OUT.glob(PREFIX + '-g*')):
        job = E.parse(directory / 'job.xml').getroot()
        report = E.parse(directory / 'report.xml').getroot()
        assert report.get('status') == 'PASS' and report.get('job') == job.get('id')
        checks += len(report.findall('check'))
        for file in job.findall('file'):
            pdf = directory / (file.get('tag') + '-filled.pdf')
            result = subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, text=True, timeout=20, check=True)
            text = normalize(result.stdout)
            expected = file.findall('case/expect')
            expected_values += len(expected)
            messages = [{'text': e.get('value'), 'present_in_pdf_text': normalize(e.get('value')) in text}
                        for e in expected if e.get('kind') == 'text']
            scans.append({'job': job.get('id'), 'tag': file.get('tag'), 'fixture': file.get('name'),
                          'sheet_probe': file.get('sheet'), 'pdf_sha256': sha256(pdf.read_bytes()).hexdigest(),
                          'hash_marks': bool(re.search(r'#{3,}', text)),
                          'formula_errors': sorted(set(re.findall(r'#(?:REF!|DIV/0!|VALUE!|NAME\?|NUM!|N/A|NULL!)', text))),
                          'expected_messages': messages})
    missing = [dict(job=row['job'], tag=row['tag'], text=m['text']) for row in scans
               for m in row['expected_messages'] if not m['present_in_pdf_text']]
    display = {'scope': 'Native PDF text screening for expected messages, hash marks and unexpected formula errors. '
                        'Text presence alone is not visual qualification. Exports use the current SaveAs-first harness.',
               'calculation_status': 'PASS', 'native_checks': checks, 'expected_values': expected_values,
               'missing_message_candidates': missing, 'pdfs': scans, 'native_print_visual': 'PENDING'}
    (OUT / 'display-text-screen.json').write_text(json.dumps(display, ensure_ascii=False, indent=2) + '\n')
    archive = OUT.parent / (ARCHIVE_STEM + '-proofs.tar.xz')
    with tarfile.open(archive, 'w:xz') as target:
        for path in sorted(OUT.rglob('*')):
            if path.is_file(): target.add(path, arcname=str(path.relative_to(OUT)), recursive=False)
    archive_index = OUT.parent / ('calculation-proof-archive.json' if ARCHIVE_STEM == 'calculation-current' else ARCHIVE_STEM + '-archive.json')
    archive_index.write_text(json.dumps({
        'status': 'CALCULATION_PASS_ONLY', 'file': archive.name, 'sha256': sha256(archive.read_bytes()).hexdigest(),
        'bytes': archive.stat().st_size, 'fixtures': EXPECTED_FIXTURES, 'sheet_probes': EXPECTED_PROBES,
        'native_checks': checks, 'expected_values': expected_values,
        'source_print': 'UNQUALIFIED: existing native print issue remains open'}, ensure_ascii=False, indent=2) + '\n')
    print('DISPLAY_TEXT_SCREEN', json.dumps({'missing_messages': missing,
          'pdfs_with_hash_marks_or_formula_errors': [r['tag'] for r in scans if r['hash_marks'] or r['formula_errors']]}), flush=True)
    print('CALCULATION_PROOF_ARCHIVE', archive.stat().st_size, sha256(archive.read_bytes()).hexdigest(), flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--fixtures-dir', type=Path); parser.add_argument('--source-root', type=Path)
    parser.add_argument('--profile', choices=['original', 'p8-layout'], default='original')
    parser.add_argument('--job-prefix')
    args = parser.parse_args()
    if args.fixtures_dir: FIXTURES = args.fixtures_dir
    if args.source_root: SOURCE_ROOT = args.source_root
    if args.profile == 'p8-layout':
        EXPECTED_FIXTURES = 4; EXPECTED_PROBES = 8; PREFIX = 'r3j-p8-warning-layout'
        ARCHIVE_STEM = 'p8-warning-layout'; OUT = BASE / 'evidence/native-final-20261019/p8-warning-layout'
    if args.job_prefix:
        assert re.fullmatch(r'[a-z0-9-]{1,40}', args.job_prefix)
        PREFIX = args.job_prefix
    if not args.collect_only: run()
    collect_print_evidence()
