#!/usr/bin/env python3
"""Package only the 22 current Excel files for the owner's manual review."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import argparse, json, shutil, subprocess

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
NAME = 'NSP_Excel_22_manual_review_2026-10-20.zip'


def package(commit, output):
    checkpoint = subprocess.check_output(['git', 'show', commit + ':tools/candidates/remaining-batch-r3-20261018/evidence/working-checkpoint.json'], cwd=REPO)
    rows = [row for row in json.loads(checkpoint)['inventory']
            if row['sku'] != 'P3' and Path(row['file']).suffix.lower() in {'.xls', '.xlsx'}]
    assert len(rows) == 22
    assert sum(row['file'].endswith('.xlsx') for row in rows) == 19
    assert sum(row['file'].endswith('.xls') for row in rows) == 3
    output.mkdir(parents=True, exist_ok=True); archive = output / NAME
    members = {}
    for row in rows:
        key = row['sku'] + '/' + row['file']; source = BASE / 'checkpoint-working' / key
        data = source.read_bytes()
        assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256'], key
        assert key not in members and not key.startswith('/') and '..' not in Path(key).parts
        members[key] = data
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=9) as target:
        for name, data in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 10, 20, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            target.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(archive) as target:
        assert target.testzip() is None and len(target.namelist()) == 22
        assert sorted(target.namelist()) == sorted(members)
        for name, data in members.items(): assert target.read(name) == data, name
    evidence = {
        'status': 'OWNER_MANUAL_OPEN_AND_PRINT_REVIEW_PENDING',
        'source_commit': commit, 'archive': NAME, 'sha256': sha256(archive.read_bytes()).hexdigest(),
        'bytes': archive.stat().st_size, 'file_count': 22, 'xlsx': 19, 'xls': 3,
        'CRC': 'PASS', 'all_member_SHA_match_current_checkpoint': '22/22',
        'scope': 'Only current Excel review files. Accepted unchanged P3 workbooks excluded. No workbook content changes; no service files in the ZIP.',
        'manual_review': ['Open without an error or recovery prompt.',
                          'Inspect print preview of every worksheet: columns, text, repeating headings, totals and signatures.',
                          'Close without saving changes. Report product folder, filename, sheet/page and any defect.'],
        'native_source_print': 'INCOMPLETE; substituted by pending owner manual review, not silently marked PASS',
        'buyer_product_release': 'NOT_PERFORMED', 'inventory': sorted(rows, key=lambda x: (x['sku'], x['file']))}
    durable = BASE / 'owner-manual-excel-20261020'; durable.mkdir(exist_ok=True)
    shutil.copyfile(archive, durable / NAME)
    (durable / 'manifest.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: evidence[k] for k in ['archive', 'sha256', 'bytes', 'file_count', 'CRC']}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--source-commit', required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); package(a.source_commit, a.output)
