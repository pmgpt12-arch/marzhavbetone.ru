#!/usr/bin/env python3
"""Wait for an observed worker update, then submit two prepared bounded jobs."""
from pathlib import Path
from hashlib import sha256
import argparse, json, shutil, time, xml.etree.ElementTree as E
from submit_office_review_job import submit

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = REPO / 'tools/candidates/remaining-batch-r3-20261018/evidence/native-final-20261019/source-print'


def ready():
    receipt = ROOT / 'results/native/r3f-worker-diagnostics-20261019/report.xml'
    if not receipt.exists(): return False
    report = E.parse(receipt).getroot()
    if report.get('scope') != 'WORKER_DIAGNOSTICS_ONLY': return False
    stamp = receipt.stat().st_mtime
    for channel in ['native', 'word']:
        path = ROOT / 'results' / (channel + '-laptop-status.json')
        if not path.exists(): return False
        status = json.loads(path.read_text())
        if status.get('state') != 'ONLINE' or status.get('time', 0) < stamp: return False
    return True


def run(wait_seconds):
    stop = time.monotonic() + wait_seconds
    while not ready() and time.monotonic() < stop: time.sleep(3)
    if not ready(): raise SystemExit('WORKER_UPDATE_NOT_OBSERVED; no job submitted; Office connectivity is not the blocker')
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'results/native/r3f-worker-diagnostics-20261019/report.xml', OUT / 'worker-update-diagnostics.xml')
    for ident in ['r3n-source-print-preflight-20261020', 'r3n-original-xls-source-print-20261020']:
        jobdir = ROOT / 'native' / ident
        job = E.parse(jobdir / 'job.xml').getroot()
        for file in job.findall('file'):
            assert file.get('export_source_first') == 'true' and file.get('print_preflight') == 'true'
            assert sha256((jobdir / file.get('name')).read_bytes()).hexdigest() == file.get('sha256')
        receipt = ROOT / 'results/native' / ident / 'report.xml'
        if not receipt.exists():
            submit(ROOT, 'native', jobdir); print('SUBMITTED', ident, flush=True)
            deadline = time.monotonic() + 240
            while not receipt.exists() and time.monotonic() < deadline: time.sleep(3)
        if not receipt.exists(): raise SystemExit('RECEIPT_TIMEOUT; preserve current manifest: ' + ident)
        report = E.parse(receipt).getroot(); assert report.get('job') == ident
        target = OUT / ident; target.mkdir(exist_ok=True)
        shutil.copyfile(jobdir / 'job.xml', target / 'job.xml')
        for path in receipt.parent.iterdir():
            if path.is_file(): shutil.copyfile(path, target / path.name)
        print('RECEIPT', ident, report.get('status'), flush=True)
        if report.get('status') != 'PASS':
            print(receipt.read_text(), flush=True); raise SystemExit('STOP_INSPECT_SOURCE_PRINT_FAILURE')
        for file in job.findall('file'):
            tag = file.get('tag')
            for suffix in ['input_sha', 'export_source_first', 'pdf_export', 'source_unchanged']:
                check = report.find("check[@name='" + tag + ':' + suffix + "']")
                assert check is not None and check.get('pass', '').lower() == 'true', (tag, suffix, 'HARNESS_CAPABILITY_NOT_QUALIFIED')
            states = report.findall("print_preflight[@tag='" + tag + "']")
            assert {state.get('stage') for state in states} == {'opened', 'exported_saved'}, (tag, 'HARNESS_PRINT_PREFLIGHT_MISSING')
            for state in states: print('PRINT_PREFLIGHT', E.tostring(state, encoding='unicode'), flush=True)
    print('PREPARED_SOURCE_EXPORT_JOBS_COMPLETE; visual/reference qualification remains required', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--wait-seconds', type=int, default=0)
    args = parser.parse_args(); assert 0 <= args.wait_seconds <= 240
    run(args.wait_seconds)
