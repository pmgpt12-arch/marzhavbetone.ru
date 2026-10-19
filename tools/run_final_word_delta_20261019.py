#!/usr/bin/env python3
"""Review changed Word SHAs; retain existing proof and hold an unexplained prior FAIL."""
from pathlib import Path
from hashlib import sha256
import json, shutil, time, xml.etree.ElementTree as E
from submit_office_review_job import submit

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
WORK = BASE / 'checkpoint-working'
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = BASE / 'evidence/native-final-20261019/word-delta'
HELD_SHA = '2cc358fcf801e98ca37aa649f6d12ad1cb884de12bbf4e7dabccec5b897c077b'


def run():
    verified = set()
    for index in (BASE / 'evidence').glob('word-native*/summary.json'):
        for row in json.loads(index.read_text()):
            if row['status'] == 'PASS':
                verified.update((f['name'], f['sha256']) for f in row['source_files'])
    # Availability job has an exact manifest and a native PDF for the final act SHA.
    ident = 'office-word-p1-act-availability-20261019-0705'
    job = E.parse(ROOT / 'word' / ident / 'job.xml').getroot()
    report = E.parse(ROOT / 'results/word' / ident / 'report.xml').getroot()
    assert report.get('job') == ident and report.get('status') == 'PASS'
    for file in job.findall('file'):
        receipt = report.find("file[@tag='" + file.get('tag') + "']")
        pdf = ROOT / 'results/word' / ident / (file.get('tag') + '.pdf')
        assert receipt is not None and receipt.get('status') == 'PASS'
        assert sha256(pdf.read_bytes()).hexdigest() == receipt.get('pdf_sha256')
        verified.add((file.get('name'), file.get('sha256')))
    OUT.mkdir(parents=True, exist_ok=True)
    pending = []
    for source in sorted(WORK.rglob('*.docx')):
        if source.parent.name == 'P3':
            continue
        digest = sha256(source.read_bytes()).hexdigest()
        if (source.name, digest) not in verified and digest != HELD_SHA:
            pending.append(source)
    assert len(pending) == 10, len(pending)
    records = []
    deadline = time.monotonic() + 1200
    # Separate SKUs avoid identical instruction filenames within one manifest.
    for sku in sorted({p.parent.name for p in pending}):
        files = [p for p in pending if p.parent.name == sku]
        for offset in range(0, len(files), 3):
            group = files[offset:offset + 3]
            ident = 'r3g-word-' + sku.lower() + '-' + str(offset // 3 + 1) + '-20261019'
            jobdir = ROOT / 'word' / ident
            job = E.Element('job', id=ident, qa_only='true')
            for i, source in enumerate(group):
                E.SubElement(job, 'file', name=source.name, tag=sku.lower() + '-' + str(i),
                             sha256=sha256(source.read_bytes()).hexdigest())
            receipt = ROOT / 'results/word' / ident / 'report.xml'
            if (jobdir / 'job.xml').exists():
                assert E.tostring(E.parse(jobdir / 'job.xml').getroot()) == E.tostring(job)
            else:
                jobdir.mkdir()
                for source in group:
                    shutil.copyfile(source, jobdir / source.name)
                E.ElementTree(job).write(jobdir / 'job.xml', encoding='utf-8', xml_declaration=True)
            if not receipt.exists():
                submit(ROOT, 'word', jobdir)
                print('SUBMITTED', ident, flush=True)
                stop = min(deadline, time.monotonic() + 300)
                while not receipt.exists() and time.monotonic() < stop:
                    time.sleep(3)
            if not receipt.exists():
                raise SystemExit('RECEIPT_TIMEOUT: keep current manifest; inspect worker ' + ident)
            result = E.parse(receipt).getroot()
            assert result.get('job') == ident
            target = OUT / ident
            target.mkdir(exist_ok=True)
            shutil.copyfile(jobdir / 'job.xml', target / 'job.xml')
            shutil.copyfile(receipt, target / 'report.xml')
            for f in job.findall('file'):
                child = result.find("file[@tag='" + f.get('tag') + "']")
                pdf = receipt.parent / (f.get('tag') + '.pdf')
                row = dict(f.attrib, sku=sku, job=ident, status=child.get('status') if child is not None else 'NOT_EXECUTED')
                if row['status'] == 'PASS':
                    assert pdf.read_bytes().startswith(b'%PDF-')
                    row['pdf_sha256'] = sha256(pdf.read_bytes()).hexdigest()
                    assert row['pdf_sha256'] == child.get('pdf_sha256')
                    shutil.copyfile(pdf, target / pdf.name)
                records.append(row)
            (OUT / 'summary.json').write_text(json.dumps({
                'scope': 'Final changed DOCX normal native opening/export; exact unchanged SHAs reused separately.',
                'held_prior_failure_sha256': HELD_SHA,
                'held_reason': 'Read previous child result before any retry.', 'records': records}, ensure_ascii=False, indent=2) + '\n')
            print('RECEIPT', ident, result.get('status'), flush=True)
            if result.get('status') != 'PASS':
                raise SystemExit('STOP: inspect new Word failure; no automatic retry')
    print('WORD_DELTA_PASS', len(records), 'HELD_PRIOR_FAIL', HELD_SHA, flush=True)


if __name__ == '__main__':
    run()
