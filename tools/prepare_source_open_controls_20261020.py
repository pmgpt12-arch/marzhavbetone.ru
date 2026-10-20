#!/usr/bin/env python3
"""Prepare immutable Local-mode controls and original-XLS read-only qualification."""
from pathlib import Path
from hashlib import sha256
import json, shutil, tarfile, xml.etree.ElementTree as E

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
ROOT = Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
OUT = BASE / 'evidence/native-final-20261019'


def prepare():
    native = ROOT / 'results/native/r3n-original-xls-source-print-20261020/ks2-filled.xlsx'
    p1 = BASE / 'checkpoint-working/P1/06A-rabochiy-reestr-obemov.xlsx'
    groups = [('r3r-xlsx-local-mode-control-20261020', [
        (native, 'control-ks2-false.xlsx', 'ctrlfalse', 'стр1', False),
        (native, 'control-ks2-true.xlsx', 'ctrltrue', 'стр1', True),
        (p1, 'control-p1-false.xlsx', 'p1false', 'Реестр', False),
        (p1, 'control-p1-true.xlsx', 'p1true', 'Реестр', True)]),
        ('r3r-original-xls-readonly-20261020', [
        (BASE / 'checkpoint-working/P1/01-ks-2.xls', 'ks2-original.xls', 'ks2', 'стр1', False),
        (BASE / 'checkpoint-working/P1/02-ks-3.xls', 'ks3-original.xls', 'ks3', 'стр1', False),
        (BASE / 'checkpoint-working/P1/06-zhurnal-ucheta-rabot-ks-6a.xls', 'ks6a-original.xls', 'ks6a', 'стр1', False)])]
    for ident, files in groups:
        directory = ROOT / 'native' / ident
        job = E.Element('job', id=ident, qa_only='true', scope='NORMAL_READ_ONLY_OPENING_LOCAL_MODE_CONTROL_NO_BUYER_EDITS')
        for source, name, tag, sheet, local in files:
            E.SubElement(job, 'file', name=name, tag=tag, sheet=sheet,
                sha256=sha256(source.read_bytes()).hexdigest(), open_local=str(local).lower(),
                export_source_first='true', print_preflight='true')
        if directory.exists():
            assert E.tostring(E.parse(directory / 'job.xml').getroot()) == E.tostring(job)
        else:
            directory.mkdir()
            for source, name, *_ in files: shutil.copyfile(source, directory / name)
            E.ElementTree(job).write(directory / 'job.xml', encoding='utf-8', xml_declaration=True)
        target = OUT / 'prepared-jobs' / ident; target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(directory / 'job.xml', target / 'job.xml')
        print('PREPARED', ident, len(files))


def collect():
    ids = ['r3n-source-print-preflight-20261020', 'r3n-original-xls-source-print-20261020',
           'r3p-excel-produced-print-control-20261020', 'r3r-xlsx-local-mode-control-20261020',
           'r3r-original-xls-readonly-20261020']
    target = OUT / 'source-print-diagnostics-20261020'; target.mkdir(exist_ok=True)
    summary = []
    for ident in ids:
        result = ROOT / 'results/native' / ident / 'report.xml'
        if not result.exists(): continue
        destination = target / ident; destination.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / 'native' / ident / 'job.xml', destination / 'job.xml')
        for path in result.parent.iterdir():
            if path.is_file(): shutil.copyfile(path, destination / path.name)
        report = E.parse(result).getroot()
        summary.append({'job': ident, 'status': report.get('status'),
                        'report_sha256': sha256(result.read_bytes()).hexdigest(),
                        'failed_checks': [dict(c.attrib) for c in report.findall('check') if c.get('pass', '').lower() != 'true'],
                        'print_states': [dict(s.attrib, sheets=[dict(v.attrib) for v in s.findall('sheet')]) for s in report.findall('print_preflight')]})
    data = {'scope': 'Source-opening/printing diagnostics only. No general product PASS or buyer nomination.', 'jobs': summary}
    (target / 'summary.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    archive = OUT / 'source-print-native-proofs-20261020.tar.xz'
    with tarfile.open(archive, 'w:xz') as output:
        for path in sorted(target.rglob('*')):
            if path.is_file(): output.add(path, arcname=str(path.relative_to(target)), recursive=False)
    index = dict(scope=data['scope'], file=archive.name, sha256=sha256(archive.read_bytes()).hexdigest(), bytes=archive.stat().st_size, jobs=len(summary))
    (OUT / 'source-print-native-proofs-20261020.json').write_text(json.dumps(index, indent=2) + '\n')
    print('PROOF_ARCHIVE', json.dumps(index))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--collect-only', action='store_true'); args = parser.parse_args()
    if not args.collect_only: prepare()
    collect()
