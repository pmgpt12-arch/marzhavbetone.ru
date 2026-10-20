#!/usr/bin/env python3
"""Bind individual native Excel receipts to the current 19 workbook SHAs."""
from pathlib import Path
from hashlib import sha256
import json, tarfile, xml.etree.ElementTree as E

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
WORK = BASE / 'checkpoint-working'
OUT = BASE / 'evidence/native-final-20261019'
JOBS = ['r3f-excel-p1-open-20261019', 'r3f-excel-p2-p4-open-20261019',
        'r3f-excel-p4-registers-open-20261019', 'r3f-excel-p7-p13-open-20261019',
        'r3f-p8-p9-p13-dv-check-20261019', 'r3f-p13-row-order-20261019',
        'r3l-p8-warning-layout-g02-20261019']


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def collect():
    OUT.mkdir(parents=True, exist_ok=True)
    # The two accepted P3 workbooks are unchanged and outside the new native review.
    current = {digest(p): p for p in WORK.rglob('*.xlsx') if p.parent.name != 'P3'}
    assert len(current) == 19
    verified = {}
    archive_members = {}
    for ident in JOBS:
        job_path = ROOT / 'native' / ident / 'job.xml'
        result_path = ROOT / 'results/native' / ident / 'report.xml'
        job = E.parse(job_path).getroot()
        report = E.parse(result_path).getroot()
        assert job.get('id') == ident and report.get('job') == ident
        archive_members[ident + '/job.xml'] = job_path
        archive_members[ident + '/report.xml'] = result_path
        for file in job.findall('file'):
            source_sha = file.get('sha256')
            if source_sha not in current:
                continue  # Rejected diagnostic variants and previous P13 SHA stay unqualified.
            tag = file.get('tag')
            checks = [report.find("check[@name='" + tag + ':' + name + "']")
                      for name in ['input_sha', 'pdf_export', 'source_unchanged']]
            if not all(c is not None and c.get('pass', '').lower() == 'true' for c in checks):
                continue
            assert checks[0].get('actual') == source_sha == checks[2].get('actual')
            pdf = result_path.parent / (tag + '-filled.pdf')
            assert pdf.read_bytes().startswith(b'%PDF-')
            source = current[source_sha]
            verified[source_sha] = {
                'sku': source.parent.name, 'file': source.name, 'sha256': source_sha,
                'job': ident, 'batch_status': report.get('status'),
                'individual_input_pdf_source_checks': 'PASS',
                'excel_version': report.get('excel_version'), 'excel_build': report.get('excel_build'),
                'pdf': ident + '/' + pdf.name, 'pdf_sha256': digest(pdf), 'pdf_bytes': pdf.stat().st_size,
                'scenario_tests': 'SEE_CURRENT_SOURCE_INDEX_WHERE_APPLICABLE', 'native_print_visual_review': 'PENDING'}
            for artifact in [pdf, result_path.parent / (tag + '-filled.xlsx')]:
                if artifact.exists():
                    archive_members[ident + '/' + artifact.name] = artifact
    assert set(current) == set(verified), sorted(str(current[k]) for k in current.keys() - verified.keys())
    archive = OUT / 'xlsx-opening-proofs.tar.xz'
    with tarfile.open(archive, 'w:xz') as target:
        for name, path in sorted(archive_members.items()):
            target.add(path, arcname=name, recursive=False)
    index = {
        'status': 'XLSX_OPENING_AND_EXPORT_PASS_ONLY', 'workbooks': len(verified),
        'scope': 'Exact input SHA, normal native opening, PDF export and unchanged input SHA. '
                 'Some batch receipts are FAIL because another file failed; only complete individual checks count.',
        'scenario_tests': 'SEE calculation-current-source-index.json: separate input-only fixtures',
        'native_print_visual_review': 'PENDING',
        'final_word': 'SEE word-current-index.json: separate SHA-bound qualification',
        'original_xls': 'PENDING', 'owner_acceptance': 'NOT_REQUESTED',
        'publication': 'NOT_PERFORMED',
        'archive': {'file': archive.name, 'sha256': digest(archive), 'bytes': archive.stat().st_size},
        'files': sorted(verified.values(), key=lambda row: (row['sku'], row['file']))}
    (OUT / 'xlsx-opening-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: index[k] for k in ['status', 'workbooks', 'archive']}))


if __name__ == '__main__':
    collect()
