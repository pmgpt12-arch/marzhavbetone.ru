#!/usr/bin/env python3
"""Bind all 66 current DOCX SHAs to native Word receipts, without re-running unchanged files."""
from pathlib import Path
from hashlib import sha256
import json, tarfile, xml.etree.ElementTree as E

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = BASE / 'evidence/native-final-20261019'


def run():
    current = {sha256(p.read_bytes()).hexdigest(): p for p in (BASE / 'checkpoint-working').rglob('*.docx') if p.parent.name != 'P3'}
    assert len(current) == 66
    candidates = []
    for summary in (BASE / 'evidence').glob('word-native*/summary.json'):
        for row in json.loads(summary.read_text()):
            if row['status'] == 'PASS': candidates.append((row['job'], summary.parent / row['job'], False))
    availability = 'office-word-p1-act-availability-20261019-0705'
    jobs = [availability] + sorted(p.name for p in (ROOT / 'word').glob('r3g-word-*-20261019') if p.is_dir())
    candidates.extend((ident, ROOT / 'results/word' / ident, True) for ident in jobs)
    verified = {}; archive_members = {}
    for ident, directory, fresh in candidates:
        job_path = ROOT / 'word' / ident / 'job.xml' if fresh else directory / 'job.xml'
        report_path = directory / 'report.xml'
        if not report_path.exists(): continue
        job = E.parse(job_path).getroot(); report = E.parse(report_path).getroot()
        assert job.get('id') == ident and report.get('job') == ident
        for file in job.findall('file'):
            digest = file.get('sha256'); tag = file.get('tag')
            if digest not in current: continue
            child = report.find("file[@tag='" + tag + "']")
            if child is None or child.get('status') != 'PASS': continue
            pdf = directory / (tag + '.pdf')
            assert pdf.read_bytes().startswith(b'%PDF-')
            assert sha256(pdf.read_bytes()).hexdigest() == child.get('pdf_sha256')
            source = current[digest]
            verified[digest] = {'sku': source.parent.name, 'file': source.name, 'sha256': digest,
                               'job': ident, 'tag': tag, 'status': 'PASS', 'fresh': fresh,
                               'pdf_sha256': child.get('pdf_sha256'),
                               'proof': ('word-current-proofs.tar.xz:' + ident) if fresh else str(directory.relative_to(BASE / 'evidence')),
                               'visual_review': 'PENDING' if fresh and ident != availability else 'REUSED_PREVIOUS_REVIEW'}
            if fresh:
                archive_members[ident + '/job.xml'] = job_path
                archive_members[ident + '/report.xml'] = report_path
                archive_members[ident + '/' + pdf.name] = pdf
    assert set(verified) == set(current), sorted(str(current[k]) for k in current.keys() - verified.keys())
    archive = OUT / 'word-current-proofs.tar.xz'
    with tarfile.open(archive, 'w:xz') as target:
        for name, path in sorted(archive_members.items()): target.add(path, arcname=name, recursive=False)
    index = {'status': 'WORD_OPENING_AND_EXPORT_PASS_ONLY', 'documents': 66,
             'fresh_proofs': sum(v['fresh'] for v in verified.values()),
             'reused_proofs': sum(not v['fresh'] for v in verified.values()),
             'previous_algorithm_fail': 'Same SHA passed a bounded isolated run after observed agent restart. Prior cause remains unproven; no claim of a permanent runtime repair.',
             'scope': 'Exact input SHA checked before/after read-only Word opening and PDF export by the installed worker; every PDF checksum matched to its receipt.',
             'new_native_pdf_visual_review': 'PENDING', 'owner_acceptance': 'NOT_READY', 'publication': 'NOT_PERFORMED',
             'archive': {'file': archive.name, 'sha256': sha256(archive.read_bytes()).hexdigest(), 'bytes': archive.stat().st_size},
             'files': sorted(verified.values(), key=lambda v: (v['sku'], v['file']))}
    (OUT / 'word-current-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: index[k] for k in ['status', 'documents', 'fresh_proofs', 'reused_proofs', 'archive']}), flush=True)


if __name__ == '__main__':
    run()
