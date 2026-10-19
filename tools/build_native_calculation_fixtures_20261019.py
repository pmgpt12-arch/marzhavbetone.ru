#!/usr/bin/env python3
"""Author disposable input fixtures; preserve every source formula and feature."""
from pathlib import Path
from datetime import date
from zipfile import ZipFile
from hashlib import sha256
from copy import deepcopy
from lxml import etree as E
import argparse, json, os, re, subprocess
from normalize_xlsx_element_order import normalize_parts, column_number

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / 'tools/candidates/remaining-batch-r3-20261018/checkpoint-working'
OUT = Path('/tmp/mb-r3/calculation-fixtures-20261019')
RUNTIME = Path('/tmp/mb-r3/runtime')
NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
Q = '{' + NS['x'] + '}'


def day(month, value):
    return (date(2026, month, value) - date(1899, 12, 30)).days


def specs():
    result = []
    def add(name, sku, filename, inputs, probes):
        result.append(dict(name=name, sku=sku, file=filename, inputs=inputs, probes=probes))
    initial = {'Входные данные': {'B4': 1000000, 'B5': day(1, 1), 'B6': day(1, 10),
                                 'A12': day(1, 1), 'B12': 18},
               'Расчёт': {'A4': day(1, 1), 'B4': day(1, 10)}}
    add('p1-interest-base', 'P1', '14-raschet-procentov-395-gk.xlsx', initial,
        {'Расчёт': {'C4': 10, 'D4': 1000000, 'E4': 18, 'F4': 365, 'G4': 4931.51},
         'Итог для документа': {'B6': 1000000, 'B10': 4931.51, 'B11': 1004931.51}})
    partial = deepcopy(initial)
    partial['Входные данные'].update(A35=day(1, 5), B35=200000)
    partial['Расчёт'].update(B4=day(1, 5), A5=day(1, 6), B5=day(1, 10))
    add('p1-interest-partial', 'P1', '14-raschet-procentov-395-gk.xlsx', partial,
        {'Расчёт': {'D5': 800000, 'G4': 2465.75, 'G5': 1972.60, 'G45': 4438.35},
         'Итог для документа': {'B6': 800000, 'B10': 4438.35, 'B11': 804438.35}})
    gap = deepcopy(partial); gap['Расчёт']['A5'] = day(1, 7)
    add('p1-interest-gap', 'P1', '14-raschet-procentov-395-gk.xlsx', gap,
        {'Расчёт': {'H5': 'Период пропущен или перекрыт — исправьте даты'}})
    cost = {'Реестр': {'D4': 10, 'E4': 500, 'H4': 1.2}}
    add('p2-cost-coefficient', 'P2', '07-raschet-stoimosti.xlsx', cost,
        {'Реестр': {'F4': 5000, 'I4': 6000}})
    cost = deepcopy(cost); cost['Реестр']['H4'] = None
    add('p2-cost-empty-coefficient', 'P2', '07-raschet-stoimosti.xlsx', cost,
        {'Реестр': {'F4': 5000, 'I4': 5000}})
    terms = {5: 1000000, 7: 1, 8: 'пропорционально из каждой КС', 9: 0, 10: 0,
             11: 0, 12: 1, 13: 0, 14: 0, 15: 100, 16: 2, 17: 0, 18: 70, 19: 0, 20: 0}
    inputs = {'Условия': {column + str(row): value for column in ['B', 'C'] for row, value in terms.items()},
              'График КС': {'B5': 50, 'C5': 50, 'B6': 50, 'C6': 50}}
    inputs['Условия'].update(B6=20, C6=0)
    add('p8-advance-compare', 'P8', '02-kalkulyator-usloviy-avansa.xlsx', inputs,
        {'Условия': {'B23': 200000, 'C23': 0, 'B24': 0, 'C24': 0},
         'Сравнение': {'B5': 200000, 'C5': 0, 'B11': 200000, 'C11': 0,
                       'B14': 700000, 'C14': 700000, 'B15': 300000, 'C15': 300000}})
    missing = deepcopy(inputs); missing['Условия']['B5'] = None
    add('p8-advance-missing-price', 'P8', '02-kalkulyator-usloviy-avansa.xlsx', missing,
        {'Условия': {'B26': 'Не заполнена сумма договора'}})
    advance = {'Договор и аванс': {'B5': 1000000, 'B6': 300000,
                                  'B8': 'генподрядчик отказался от исполнения, о наших нарушениях не заявлено', 'B11': 100000},
               'Выполнено': {'C6': 'КС-2 № ТЕСТ-1', 'E6': 400000,
                            'F6': 'подписан обеими сторонами', 'I6': 200000, 'J6': 100000}}
    add('p8-advance-bilateral', 'P8', '09-raschet-otrabotannoy-chasti-avansa.xlsx', advance,
        {'Договор и аванс': {'B16': 200000, 'B17': 100000},
         'Выполнено': {'K6': 100000},
         'Сальдо': {'B11': 400000, 'B12': 200000, 'B13': 100000, 'B14': 100000}})
    unilateral = deepcopy(advance); unilateral['Выполнено']['F6'] = 'подписан односторонне'
    add('p8-advance-unilateral', 'P8', '09-raschet-otrabotannoy-chasti-avansa.xlsx', unilateral,
        {'Договор и аванс': {'B16': 0, 'B17': 300000},
         'Выполнено': {'L6': 'ОШИБКА: погашение аванса отнесено к акту, не подписанному обеими сторонами.'}})
    dates = {'Объект и должник': {'B14': day(1, 10)}, 'Реестр документов': {}}
    for row, amount, date_value in [(4, 100000, day(1, 9)), (5, 50000, day(1, 11))]:
        dates['Реестр документов'].update({f'B{row}': 'Акт', f'C{row}': 'ТЕСТ-' + str(row),
                                         f'D{row}': date_value, f'E{row}': amount, f'F{row}': 'да', f'K{row}': 'да'})
    add('p9-bankruptcy-cutoff', 'P9', '04-reestr-dokumentov-i-dat-po-obektu.xlsx', dates,
        {'Реестр документов': {'L4': 'до принятия заявления', 'L5': 'после принятия заявления'},
         'Итоги': {'B6': 100000, 'B7': 50000, 'B8': 150000}})
    rows = {column + str(row): 'не применяется' for row in range(2, 53) for column in ['D', 'I']}
    rows.update(D2='нет', I2='проверить', H2=100000, H55=500000)
    add('p13-uncovered-cost', 'P13', '63-reestr-zatrat-po-obektu.xlsx', {'Реестр затрат': rows},
        {'Реестр затрат': {'H54': 100000, 'H56': 0.2, 'C53': 'Проверка заполнена; решение о цене принимает руководитель'}})
    covered = deepcopy(rows); covered.update(D2='да', I2='покрыто, проверено', G2='Смета № ТЕСТ-1, позиция 1')
    add('p13-covered-cost', 'P13', '63-reestr-zatrat-po-obektu.xlsx', {'Реестр затрат': covered},
        {'Реестр затрат': {'H54': 0, 'H56': 0, 'C53': 'Проверка заполнена; решение о цене принимает руководитель'}})
    empty = deepcopy(rows); empty['H2'] = None
    add('p13-missing-estimate', 'P13', '63-reestr-zatrat-po-obektu.xlsx', {'Реестр затрат': empty},
        {'Реестр затрат': {'C53': 'Есть непокрытые затраты без числовой оценки'}})
    assert len(result) == 13
    return result


def build(spec):
    source = WORK / spec['sku'] / spec['file']
    if not spec['inputs']:
        destination = OUT / (spec['name'] + '.xlsx'); destination.write_bytes(source.read_bytes())
        digest = sha256(source.read_bytes()).hexdigest()
        return dict(spec, source_sha256=digest, fixture_sha256=digest, bytes=destination.stat().st_size,
                    preservation='Exact source bytes copied under a QA filename; no input or workbook changes.')
    with ZipFile(source) as archive:
        infos = archive.infolist(); parts = {i.filename: archive.read(i.filename) for i in infos}
    sheets = E.fromstring(parts['xl/workbook.xml']).findall('x:sheets/x:sheet', NS)
    sheet_parts = {s.get('name'): f'xl/worksheets/sheet{i + 1}.xml' for i, s in enumerate(sheets)}
    patches = [{'sheet': sheet, 'cell': cell, 'text': value}
               for sheet, values in spec['inputs'].items() for cell, value in values.items()]
    patch = OUT / (spec['name'] + '.json'); patch.write_text(json.dumps(patches, ensure_ascii=False))
    authored = OUT / 'authored' / (spec['name'] + '.xlsx')
    process = subprocess.run([os.environ['CODEX_PRIMARY_RUNTIME_NODE'], str(RUNTIME / 'edit.mjs'),
                              str(source), str(authored), str(patch)], capture_output=True, text=True, timeout=90)
    if process.returncode:
        raise RuntimeError(spec['name'] + ': ' + process.stderr[-2000:])
    with ZipFile(authored) as archive:
        strings = E.fromstring(archive.read('xl/sharedStrings.xml')) if 'xl/sharedStrings.xml' in archive.namelist() else None
        for sheet, changes in spec['inputs'].items():
            part = sheet_parts[sheet]; original = E.fromstring(parts[part]); updated = E.fromstring(archive.read(part))
            for address, value in changes.items():
                cell = original.find('.//x:c[@r="' + address + '"]', NS)
                assert cell is not None and cell.find('x:f', NS) is None, (spec['name'], sheet, address, 'input is absent or is a formula')
                authored_cell = updated.find('.//x:c[@r="' + address + '"]', NS)
                for child in list(cell): cell.remove(child)
                cell.attrib.pop('t', None)
                if value is None: continue
                assert authored_cell is not None
                if isinstance(value, str):
                    if authored_cell.get('t') == 's':
                        actual = ''.join(strings[int(authored_cell.find('x:v', NS).text)].itertext())
                    elif authored_cell.get('t') == 'str':
                        actual = authored_cell.find('x:v', NS).text or ''
                    else: actual = ''.join(authored_cell.xpath('.//x:t/text()', namespaces=NS))
                    assert actual == value, (spec['name'], sheet, address, actual, value)
                    cell.set('t', 'inlineStr'); E.SubElement(E.SubElement(cell, Q + 'is'), Q + 't').text = actual
                else:
                    actual = authored_cell.find('x:v', NS).text
                    assert float(actual) == value, (spec['name'], sheet, address)
                    cell.set('t', 'n'); E.SubElement(cell, Q + 'v').text = actual
            parts[part] = E.tostring(original)
    assert not normalize_parts(dict(parts))
    destination = OUT / (spec['name'] + '.xlsx')
    with ZipFile(destination, 'w') as archive:
        for info in infos: archive.writestr(info, parts[info.filename])
    with ZipFile(source) as before, ZipFile(destination) as after:
        assert before.namelist() == after.namelist()
        for part in before.namelist():
            if before.read(part) == after.read(part): continue
            sheet = next((s for s, p in sheet_parts.items() if p == part), None)
            assert sheet in spec['inputs'], (spec['name'], part, 'unexpected changed part')
            a = E.fromstring(before.read(part)); b = E.fromstring(after.read(part))
            for address in spec['inputs'][sheet]:
                for root in [a, b]:
                    cell = root.find('.//x:c[@r="' + address + '"]', NS)
                    assert cell.find('x:f', NS) is None
                    cell.getparent().remove(cell)
            assert E.tostring(a, method='c14n') == E.tostring(b, method='c14n'), (spec['name'], part, 'non-input contents changed')
    return dict(spec, source_sha256=sha256(source.read_bytes()).hexdigest(),
                fixture_sha256=sha256(destination.read_bytes()).hexdigest(), bytes=destination.stat().st_size,
                preservation='Only listed non-formula input cell values changed; every other XML element and package part preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--only-source'); parser.add_argument('--source-root', type=Path)
    parser.add_argument('--out-dir', type=Path); parser.add_argument('--p8-message-boundaries', action='store_true')
    args = parser.parse_args()
    if args.source_root: WORK = args.source_root
    if args.out_dir: OUT = args.out_dir
    selected = specs()
    if args.p8_message_boundaries:
        assert args.only_source == 'P8/09-raschet-otrabotannoy-chasti-avansa.xlsx'
        unilateral = deepcopy(next(r for r in selected if r['name'] == 'p8-advance-unilateral')['inputs'])
        unilateral['Выполнено'].update(C45='КС-2 № ТЕСТ-40', E45=400000, F45='подписан односторонне', I45=100000, J45=100000)
        unilateral['Выполнено'].update(C20='КС-2 № ТЕСТ-15', E20=400000, F20='подписан обеими сторонами', I20=0, J20=0)
        import openpyxl
        source = openpyxl.load_workbook(WORK / 'P8/09-raschet-otrabotannoy-chasti-avansa.xlsx', data_only=False)
        validation = next(v for v in source['Встречное'].data_validations.dataValidation if 'B6' in v.sqref)
        assert validation.formula1.startswith('"') and validation.formula1.endswith('"')
        category = validation.formula1[1:-1].split(',')[0]
        assert source['Встречное']['G30'].data_type == 'f'
        unilateral['Встречное'] = {f'{col}{row}': value for row in [6, 30] for col, value in
                                    {'B': category, 'D': 25000, 'E': 'Документ № ТЕСТ-1', 'F': 'нет'}.items()}
        warning = 'ОШИБКА: погашение аванса отнесено к акту, не подписанному обеими сторонами.'
        payment_warning = 'По подписанному акту не отражены погашение аванса и оплата: проверьте платежи.'
        counter_warning = 'Проверьте самостоятельное основание требования и подтверждающие документы.'
        selected += [dict(name='p8-advance-message-boundaries', sku='P8', file='09-raschet-otrabotannoy-chasti-avansa.xlsx',
                          inputs=unilateral, probes={'Выполнено': {'L6': warning, 'L20': payment_warning, 'L45': warning},
                                                    'Встречное': {'G6': counter_warning, 'G30': counter_warning}}),
                     dict(name='p8-layout-source-copy', sku='P8', file='09-raschet-otrabotannoy-chasti-avansa.xlsx',
                          inputs={}, probes={'Как читать': {}})]
    if args.only_source: selected = [r for r in selected if r['sku'] + '/' + r['file'] == args.only_source]
    assert selected
    OUT.mkdir(exist_ok=True, parents=True); (OUT / 'authored').mkdir(exist_ok=True)
    manifest = OUT / 'fixture-manifest.json'
    previous = {r['name']: r for r in json.loads(manifest.read_text())['records']} if manifest.exists() else {}
    records = []
    for spec in selected:
        if spec['name'] in previous:
            old = previous[spec['name']]
            assert all(old[k] == v for k, v in spec.items())
            assert sha256((WORK / spec['sku'] / spec['file']).read_bytes()).hexdigest() == old['source_sha256']
            assert sha256((OUT / (spec['name'] + '.xlsx')).read_bytes()).hexdigest() == old['fixture_sha256']
            records.append(old)
            print('REUSED_VERIFIED_FIXTURE', spec['name'], flush=True)
            continue
        records.append(build(spec))
        (OUT / 'fixture-manifest.json').write_text(json.dumps({'status': 'DISPOSABLE_TEST_FIXTURES_NOT_BUYER_FILES',
                                                            'records': records}, ensure_ascii=False, indent=2) + '\n')
        print('FIXTURE_PRESERVATION_PASS', spec['name'], flush=True)
    assert len(records) == len(selected)
    manifest.write_text(json.dumps({'status': 'DISPOSABLE_TEST_FIXTURES_NOT_BUYER_FILES',
                                    'complete': True, 'expected_count': len(selected),
                                    'records': records}, ensure_ascii=False, indent=2) + '\n')
