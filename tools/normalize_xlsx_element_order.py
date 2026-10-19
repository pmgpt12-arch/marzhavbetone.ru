#!/usr/bin/env python3
"""Restore worksheet row/cell order without changing any element's contents."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import argparse, hashlib, json, re

NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def column_number(ref):
    match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', ref)
    if not match:
        raise ValueError('Invalid cell reference: ' + ref)
    value = 0
    for letter in match[1]:
        value = value * 26 + ord(letter) - 64
    return value, int(match[2])


def normalize_parts(parts):
    changes = []
    for name, data in list(parts.items()):
        if not re.fullmatch(r'xl/worksheets/sheet[0-9]+\.xml', name):
            continue
        root = E.fromstring(data)
        sheet_data = root.find('x:sheetData', NS)
        if sheet_data is None:
            continue
        rows = list(sheet_data)
        numbers = [int(row.get('r')) for row in rows]
        if len(numbers) != len(set(numbers)):
            raise ValueError('Duplicate row in ' + name)
        changed = False
        for row in rows:
            cells = list(row)
            positions = [column_number(cell.get('r')) for cell in cells]
            if len(positions) != len(set(positions)) or any(y != int(row.get('r')) for x, y in positions):
                raise ValueError('Duplicate or misplaced cell in ' + name)
            ordered = sorted(cells, key=lambda cell: column_number(cell.get('r'))[0])
            if cells != ordered:
                row[:] = ordered
                changed = True
        ordered_rows = sorted(rows, key=lambda row: int(row.get('r')))
        if rows != ordered_rows:
            sheet_data[:] = ordered_rows
            changed = True
        if changed:
            parts[name] = E.tostring(root)
            changes.append({'part': name, 'old_row_order': numbers,
                            'new_row_order': [int(row.get('r')) for row in sheet_data]})
    return changes


def repair(source, destination):
    if source.resolve() == destination.resolve():
        raise ValueError('Use a separate destination for review')
    with ZipFile(source) as original:
        infos = original.infolist()
        parts = {info.filename: original.read(info.filename) for info in infos}
    changes = normalize_parts(parts)
    with ZipFile(destination, 'w') as result:
        for info in infos:
            result.writestr(info, parts[info.filename])
    return {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'changes': changes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(repair(args.source, args.destination), ensure_ascii=False, indent=2))
