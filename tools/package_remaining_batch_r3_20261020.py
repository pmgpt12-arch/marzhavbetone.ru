#!/usr/bin/env python3
"""Record the exact 22-file manual acceptance and package the final R3 review batch."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from io import BytesIO
from urllib.parse import unquote, urlparse
import argparse, json, re, subprocess, tempfile, xml.etree.ElementTree as E
from editorial_business_style_gate import check as editorial_check, extract
from standard_form_original_gate import check_member

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / 'tools/candidates/remaining-batch-r3-20261018'
WORK = BASE / 'checkpoint-working'
EVIDENCE = BASE / 'evidence/native-final-20261019'
OUT = BASE / 'final-buyer-review-20261020'
COUNTS = {'P1': 20, 'P2': 15, 'P3': 11, 'P4': 25, 'P7': 13, 'P8': 11, 'P9': 10, 'P10': 8, 'P13': 10}
MANUAL_SHA = '7b9dd906a4b8e11db49fb8a0e89252ac3bfa6e762e497e6d6c7913d3e8da6ca5'
OUTER_NAME = 'NSP_remaining_products_R3_owner_review_2026-10-20.zip'
FILE_REF = re.compile(r'(?<![A-Za-z0-9_-])([0-9]{2}[A-Z]?[-_][A-Za-z0-9_.-]+\.(?:docx|xlsx|xls|pdf|txt))\b')


def digest(data): return sha256(data).hexdigest()
def read_json(path): return json.loads(path.read_text())
def write_json(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def record_manual_acceptance():
    folder = BASE / 'owner-manual-excel-20261020'
    manifest = read_json(folder / 'manifest.json')
    assert manifest['sha256'] == MANUAL_SHA and manifest['file_count'] == 22
    archive = folder / manifest['archive']; assert digest(archive.read_bytes()) == MANUAL_SHA
    current = {(p.parent.name, p.name): digest(p.read_bytes()) for p in WORK.rglob('*') if p.is_file()}
    with ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist()) == 22
        for row in manifest['inventory']:
            key = row['sku'] + '/' + row['file']
            assert digest(z.read(key)) == row['sha256'] == current[row['sku'], row['file']]
    acceptance = {
        'status': 'PASS_OWNER_MANUAL_OPEN_AND_PRINT', 'archive': manifest['archive'],
        'sha256': MANUAL_SHA, 'files': 22, 'xlsx': 19, 'xls': 3,
        'owner_message': 'Все готово - ок', 'reported_at': '2026-10-20T12:52:49+07:00',
        'scope': 'Owner confirmation following the supplied 22-file opening and all-sheet print-preview checklist.',
        'automatic_harness_status': 'Historical native print/source-integrity failures retained; not relabelled PASS.',
        'numerical_scenarios': 'Previously qualified independently; not attributed to this manual check.',
        'whole_product_batch_acceptance': 'PENDING', 'publication': 'NOT_PERFORMED',
        'inventory': manifest['inventory']}
    write_json(folder / 'acceptance.json', acceptance)
    manifest.update(status=acceptance['status'], owner_acceptance='acceptance.json',
                    native_source_print='Owner manual opening/print PASS for these exact 22 SHAs; automatic harness remains diagnostic only.')
    write_json(folder / 'manifest.json', manifest)
    qualifications_path = BASE / 'form-originals-audit/qualified-buyer-originals.json'
    qualifications = read_json(qualifications_path)
    visual = read_json(EVIDENCE / 'original-xls-native-visual-review-20261020.json')
    assert visual['visual_pages'] == 6
    for row in visual['files']:
        source = WORK / 'P1' / row['file']; assert digest(source.read_bytes()) == row['source_sha256']
        assert any(v['sku'] == 'P1' and v['file'] == row['file'] and v['sha256'] == row['source_sha256'] for v in acceptance['inventory'])
        qualifications = [v for v in qualifications if not (v['sku'] == 'P1' and v['file'] == row['file'])]
        qualifications.append({'sku': 'P1', 'file': row['file'], 'sha256': row['source_sha256'],
            'visual_status': 'PASS', 'reference_url': 'https://www.consultant.ru/document/cons_doc_LAW_26303/',
            'evidence': '../evidence/native-final-20261019/original-xls-native-visual-review-20261020.json and ../owner-manual-excel-20261020/acceptance.json',
            'pages': row['pages'], 'qualification_method': 'Original source bytes, six-page native visual comparison, exact-SHA owner manual opening/print acceptance'})
    assert len(qualifications) == 8
    write_json(qualifications_path, qualifications)
    return acceptance


def verify_evidence(expected):
    words = read_json(EVIDENCE / 'word-current-index.json')
    assert words['documents'] == 66 and words['new_native_pdf_visual_review'] == 'PASS'
    current_words = {(p.parent.name, p.name): digest(p.read_bytes()) for p in WORK.rglob('*.docx') if p.parent.name != 'P3'}
    assert len(current_words) == 66
    assert {(v['sku'], v['file']): v['sha256'] for v in words['files']} == current_words
    assert all(v['status'] == 'PASS' and v['visual_review'] in {'PASS', 'REUSED_PREVIOUS_REVIEW'} for v in words['files'])
    excel = read_json(EVIDENCE / 'xlsx-opening-index.json')
    current_excel = {(p.parent.name, p.name): digest(p.read_bytes()) for p in WORK.rglob('*.xlsx') if p.parent.name != 'P3'}
    assert len(current_excel) == 19 and excel['workbooks'] == 19
    assert {(v['sku'], v['file']): v['sha256'] for v in excel['files']} == current_excel
    math = read_json(EVIDENCE / 'calculation-current-source-index.json')
    assert (math['scenarios'], math['expected_values'], math['native_checks']) == (14, 60, 126)
    for row in math['records']: assert expected[row['sku'], row['file']]['sha256'] == row['source_sha256']
    preservation = read_json(BASE / 'evidence/workbook-preservation.json')
    assert preservation['status'] == 'PASS' and preservation['formula_count'] == 2470
    for row in preservation['workbooks']:
        assert expected[row['sku'], row['file']]['sha256'] == row['sha256'] and row['status'] == 'PASS'
    metadata = read_json(BASE / 'evidence/working-checkpoint.json')['office_core_metadata_gate']
    assert metadata['status'] == 'PASS' and metadata['files'] == 93
    for lock in read_json(BASE / 'original-form-lock.json'):
        assert expected[lock['sku'], lock['member']]['sha256'] == lock['sha256']
    return {'word_native_current_SHA': 'PASS_66', 'word_visual': 'PASS_REUSED_UNCHANGED_VIEWS',
        'xlsx_native_opening_current_SHA': 'PASS_19', 'excel_owner_manual_open_and_print': 'PASS_22',
        'numerical_scenarios': 'PASS_14_SCENARIOS_60_EXPECTED_VALUES',
        'workbook_preservation': 'PASS_2470_FORMULAS_AND_FUNCTIONAL_FEATURES',
        'office_metadata': 'REUSED_PASS_93_IDENTICAL_CHECKPOINT_FILES',
        'original_forms': 'PASS_8_EXACT_BUYER_SHAS',
        'accepted_P3_unrelated_members': 'UNCHANGED_FROM_VERIFIED_CHECKPOINT'}


def write_zip(path, files):
    with ZipFile(path, 'w', ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, (2026, 10, 20, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(path) as z:
        assert z.testzip() is None and len(z.namelist()) == len(files)
        assert sorted(z.namelist()) == sorted(files)
        for name, data in files.items(): assert z.read(name) == data


def references(sku, name, data, names):
    text = extract(name, data)
    observed = set(FILE_REF.findall(text))
    if name.endswith('.pdf'):
        # pdftotext removes end-of-line discretionary hyphens in wrapped filenames.
        # Resolve only unique hyphen-equivalent visible labels; URI targets stay exact.
        for label in list(observed - names):
            matches = [n for n in names if n.replace('-', '') == label.replace('-', '')]
            if len(matches) == 1:
                observed.remove(label); observed.add(matches[0])
        # Also inspect real PDF URI annotations; visible labels alone do not cover them.
        with tempfile.NamedTemporaryFile(suffix='.pdf') as source:
            source.write(data); source.flush()
            document = json.loads(subprocess.check_output(['qpdf', '--json', source.name]))
        def visit(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {'/URI', '/F', '/UF'} and isinstance(value, str):
                        target = value[2:] if value.startswith('u:') else value
                        if urlparse(target).scheme not in {'http', 'https', 'mailto'}:
                            observed.update(FILE_REF.findall(unquote(target)))
                    visit(value)
            elif isinstance(node, list):
                for value in node: visit(value)
        visit(document)
    assert observed <= names, (sku, name, 'unknown buyer filename references', sorted(observed - names))
    return sorted(observed)


def run():
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    checkpoint = read_json(BASE / 'evidence/working-checkpoint.json')
    expected = {(v['sku'], v['file']): v for v in checkpoint['inventory']}
    assert len(expected) == 123
    paths = [p for p in WORK.rglob('*') if p.is_file()]
    assert {(p.parent.name, p.name) for p in paths} == set(expected)
    for p in paths:
        row = expected[p.parent.name, p.name]
        assert p.stat().st_size == row['bytes'] and digest(p.read_bytes()) == row['sha256'], p
    acceptance = record_manual_acceptance()
    checks = verify_evidence(expected)
    OUT.mkdir(parents=True, exist_ok=True)
    all_archives = {}; packages = []
    for sku, count in COUNTS.items():
        files = sorted((WORK / sku).iterdir()); assert len(files) == count and all(p.is_file() for p in files)
        names = {p.name for p in files}; contents = {}; members = []; links = []
        for p in files:
            data = p.read_bytes(); assert p.suffix in {'.txt', '.pdf', '.docx', '.xlsx', '.xls'}
            assert not editorial_check(p.name, data), (sku, p.name, 'editorial gate')
            check_member(sku, p.name, data)
            seen = references(sku, p.name, data, names)
            if seen: links.append({'file': p.name, 'references': seen})
            contents[p.name] = data
            members.append({'file': p.name, 'bytes': len(data), 'sha256': digest(data)})
        name = sku + '-buyer-review-R3-20261020.zip'; archive = OUT / name
        write_zip(archive, contents)
        manifest = {'sku': sku, 'status': 'READY_FOR_OWNER_PRODUCT_ACCEPTANCE', 'archive': name,
            'sha256': digest(archive.read_bytes()), 'bytes': archive.stat().st_size, 'file_count': count,
            'CRC': 'PASS', 'source_SHA_match': 'PASS', 'editorial': 'PASS',
            'original_form_gate': 'PASS', 'buyer_filename_references': 'PASS',
            'source_commit': source_commit, 'members': members, 'reference_details': links,
            'publication': 'NOT_PERFORMED'}
        write_json(OUT / (sku + '-manifest-R3.json'), manifest)
        all_archives[name] = archive.read_bytes(); packages.append(manifest)
        print('PACKAGE_PASS', sku, count, manifest['sha256'], flush=True)
    guide = '''КОМПЛЕКТЫ ДЛЯ ОБЩЕЙ ПОКУПАТЕЛЬСКОЙ ПРИЁМКИ — 20.10.2026

Восемь комплектов: P1, P2, P4, P7, P8, P9, P10, P13.
Отдельно — адресная редакция P3 с исходной формой АОСР и пояснениями к её применению.
В каждом ZIP находятся только файлы соответствующего продукта.

Проверка 22 Excel-файлов принята по вашему сообщению «Все готово - ок»; повторять её не требуется.
Для общей приёмки распакуйте нужный ZIP, ознакомьтесь с инструкцией и проверьте состав, содержание писем, актов и порядок применения документов.
Для P3 проверьте замену АОСР и соответствующие пояснения; остальные ранее принятые файлы сохранены.
Замечания сообщайте по формату: пакет / файл / страница или пункт / необходимое исправление.

Статус: комплекты переданы на общую приёмку. Публикация этой редакции на сайте не выполнялась.
'''
    all_archives['00-PORYADOK-PRIEMKI.txt'] = guide.encode('utf-8-sig')
    outer = OUT / OUTER_NAME; write_zip(outer, all_archives)
    batch = {'status': 'READY_FOR_OWNER_PRODUCT_ACCEPTANCE', 'source_commit': source_commit,
        'archive': outer.name, 'sha256': digest(outer.read_bytes()), 'bytes': outer.stat().st_size,
        'new_product_packages': 8, 'isolated_P3_revision': 1, 'product_files': 123,
        'outer_members': 10, 'outer_CRC': 'PASS', 'all_inner_CRC': 'PASS',
        'manual_excel_archive_sha256': acceptance['sha256'], 'checks': checks,
        'checks_requiring_manual_substitution': 'Opening/print confirmed by owner on exact 22-file ZIP; failed automatic harness receipts retained.',
        'whole_product_batch_owner_acceptance': 'PENDING', 'publication': 'NOT_PERFORMED',
        'accepted_main_product_counter': 'UNCHANGED', 'packages': packages}
    write_json(OUT / 'BATCH-MANIFEST-R3.json', batch)
    checkpoint.update(status='READY_FOR_OWNER_PRODUCT_ACCEPTANCE',
        native_office_final='66 DOCX current-SHA native/visual PASS; 19 XLSX opening PASS; exact 22 Excel files owner manual opening/print PASS. Historical harness failures retained separately.')
    write_json(BASE / 'evidence/working-checkpoint.json', checkpoint)
    report = BASE / 'REVIEW-STATUS.md'
    text = report.read_text(); text = text.replace('# R3: доработка, не покупательская приёмка', '# R3: готово к общей покупательской приёмке')
    text += '\n## Ручная проверка Excel принята и комплекты собраны — 20 октября\n\nВладелец подтвердил «Все готово - ок» для точного 22-файлового архива SHA ' + MANUAL_SHA + '. Приёмка открытия и печати зафиксирована в owner-manual-excel-20261020/acceptance.json. Диагностика языкового режима больше не блокирует передачу на общую приёмку; исторические автоматические FAIL не переименованы в PASS.\n\nСобраны восемь новых комплектов и адресная редакция P3, всего 123 неизменённых продуктовых файла. Архивы, SHA и результаты проверок находятся в final-buyer-review-20261020/BATCH-MANIFEST-R3.json. Все внутренние составы, CRC, ссылки на имена файлов, редакционный контроль и точные исходные SHA проверены. Общая покупательская приёмка пакетов ожидается. Публикация, VERIFIED DONE и изменение счётчика принятых основных продуктов не выполнялись.\n'
    report.write_text(text)
    print('FINAL_REVIEW_BUNDLE', json.dumps({k: batch[k] for k in ['archive', 'sha256', 'bytes', 'product_files', 'outer_members']}), flush=True)


if __name__ == '__main__': run()
