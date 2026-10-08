#!/usr/bin/env python3
"""Read only the established SITE_PATH/orders scope; emit no IDs or PII.

Executed over SSH stdin. Does not import production code/config, resolve other
directories, create locks, build archives, send mail or write host files.
"""
import collections
import contextlib
import hashlib
import json
import os
import re
import stat
import sys
import time
import zipfile
from pathlib import Path

SCHEMA_VERSION = 1
MAX_ORDERS = 1000
MAX_ORDER_BYTES = 2 * 1024 * 1024
MAX_CONFIG_BYTES = 512 * 1024
MAX_ARCHIVES = 100
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_ZIP_MEMBERS = 500
MAX_UNCOMPRESSED = 128 * 1024 * 1024
MAX_SECONDS = 180
STATUSES = {'pending', 'paid', 'canceled', 'waiting_for_capture'}
SKUS = {'p' + str(i) for i in range(1, 14)} | {'t1', 'test1', 's1'}
KNOWN_LEGACY = '01-ks-podpisany-deneg-net.zip'
KNOWN_MEMBERS = {
    '00-INSTRUKCIYA.docx', '00-INSTRUKCIYA.pdf', '00-START-HERE.txt',
    '01-ks-2.docx', '02-ks-3.docx', '03-akt-vypolnennyh-rabot.docx',
    '04-akt-priemki.docx', '05-peredatochnyy-akt.docx',
    '06-zhurnal-obemov.xlsx', '07-reestr-zamechaniy.xlsx',
    '08-reestr-peredachi.xlsx', '09-checklist-peredachi.pdf',
    '10-sroki-hraneniya.pdf', '11-slovar-poley.docx',
    '12-pretenziya-na-neoplatu-po-ks-2.docx',
    '13-uvedomlenie-o-prosrochke-oplaty.docx',
    '14-raschet-procentov-395-gk.xlsx', '15-algoritm-pri-zaderzhke-oplaty.docx',
    '16-iskovoe-zayavlenie-o-vzyskanii.docx',
}
BASE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,179}\.zip\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def safe_basename(value):
    return isinstance(value, str) and bool(BASE.fullmatch(value)) and '..' not in value


def pin(value):
    if not isinstance(value, dict):
        return None
    name, sha = value.get('zip'), value.get('sha256')
    if isinstance(sha, str) and HEX.fullmatch(sha) and name == 'p1-' + sha + '.zip':
        return {'zip': name, 'sha256': sha}
    return None


def static_orders_match(text, known_absolute_orders):
    """Only literal ORDERS_DIR declaration; no PHP execution or other values out."""
    if not text.lstrip().startswith('<?php') or '<<<' in text or '`' in text:
        return None
    lexical = re.compile(r'/\*[\s\S]*?\*/|//[^\r\n]*|\#[^\r\n]*|\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z0-9_]*|[^\s]')
    matches = [m for m in lexical.finditer(text) if not m.group().startswith(('/*', '//', '#'))]
    tokens = [m.group() for m in matches]
    for i in range(len(tokens) - 1):
        if tokens[i:i + 2] == ['?', '>']:
            if text[matches[i + 1].end():].strip():
                return None
            tokens = tokens[:i]
            break
    if any(t.lower() in {'eval', 'include', 'include_once', 'require', 'require_once'} for t in tokens):
        return None
    def literal(token):
        if len(token) < 2 or token[0] not in "'\"" or token[-1] != token[0]:
            return None
        value = token[1:-1]
        if '\\' in value or any(c in value for c in '\r\n\x00') or (token[0] == '"' and '$' in value):
            return None
        return value
    declarations = []
    for i, token in enumerate(tokens):
        expression = None
        if token.lower() == 'define' and tokens[i + 1:i + 2] == ['(']:
            if i + 3 >= len(tokens) or literal(tokens[i + 2]) is None:
                return None
            if literal(tokens[i + 2]) != 'ORDERS_DIR':
                continue
            if tokens[i + 3] != ',':
                return None
            end = next((j for j in range(i + 4, len(tokens)) if tokens[j] == ')'), None)
            expression = tokens[i + 4:end] if end is not None else []
        elif token.lower() == 'const' and tokens[i + 1:i + 3] == ['ORDERS_DIR', '=']:
            end = next((j for j in range(i + 3, len(tokens)) if tokens[j] == ';'), None)
            expression = tokens[i + 3:end] if end is not None else []
        if expression is None:
            continue
        if len(expression) == 3 and expression[:2] == ['__DIR__', '.'] and literal(expression[2]) == '/orders':
            declarations.append(True)
        elif len(expression) == 1 and literal(expression[0]) is not None and literal(expression[0]).startswith('/'):
            declarations.append(os.path.normpath(literal(expression[0])) == known_absolute_orders)
        else:
            return None
    return declarations[0] if len(declarations) == 1 else None


def configured_orders_match(site_fd, known_absolute_orders):
    try:
        handle, opened = open_readonly('config.php', site_fd)
        with handle:
            if opened.st_size > MAX_CONFIG_BYTES:
                return None
            data = handle.read(MAX_CONFIG_BYTES + 1)
            if len(data) > MAX_CONFIG_BYTES or signature(opened) != signature(os.fstat(handle.fileno())) or signature(opened) != signature(os.stat('config.php', dir_fd=site_fd, follow_symlinks=False)):
                return None
        return static_orders_match(data.decode('utf-8'), known_absolute_orders)
    except (OSError, ValueError, UnicodeError):
        return None


def directory_allowed(path):
    """Reject symlinked known subdirectories; do not follow alternative paths."""
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def open_readonly(path, parent_fd):
    if not hasattr(os, 'O_NOFOLLOW'):
        raise OSError('no nofollow support')
    before = os.stat(path, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise OSError('not regular')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0), dir_fd=parent_fd)
    opened = os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode) or signature(before) != signature(opened):
        os.close(fd)
        raise OSError('changed before open')
    return os.fdopen(fd, 'rb'), opened


def order_snapshot(orders_fd):
    snapshot = {}
    for name in os.listdir(orders_fd):
        if not (name.startswith('order_') and name.endswith('.json')):
            continue
        try:
            snapshot[name] = signature(os.stat(name, dir_fd=orders_fd, follow_symlinks=False))
        except OSError:
            snapshot[name] = None
    return snapshot


def inspect_archive(directory_fd, name, deadline):
    """Read SHA and CRC/member metadata. Never expose arbitrary member names."""
    result = {'state': 'unreadable', 'sha256': None, 'zip_integrity': 'not_checked',
              'known_p1_members': [], 'unknown_member_count': None,
              'historical_authority_verified': False}
    try:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            result['state'] = 'missing_in_known_delivery_scope'
            return result
        handle, opened = open_readonly(name, directory_fd)
        with handle:
            if opened.st_size > MAX_ZIP_BYTES:
                result['state'] = 'size_limit_not_inspected'
                return result
            hasher = hashlib.sha256()
            for chunk in iter(lambda: handle.read(65536), b''):
                if time.monotonic() > deadline:
                    result['state'] = 'time_limit_not_inspected'
                    return result
                hasher.update(chunk)
            result['sha256'] = hasher.hexdigest()
            handle.seek(0)
            try:
                with zipfile.ZipFile(handle) as archive:
                    members = archive.infolist()
                    if len(members) > MAX_ZIP_MEMBERS or sum(m.file_size for m in members) > MAX_UNCOMPRESSED:
                        result['state'] = 'zip_limit_not_inspected'
                        return result
                    filenames = [m.filename for m in members if not m.is_dir()]
                    result['known_p1_members'] = sorted(set(filenames) & KNOWN_MEMBERS)
                    result['unknown_member_count'] = sum(n not in KNOWN_MEMBERS for n in filenames)
                    result['duplicate_member_count'] = len(filenames) - len(set(filenames))
                    result['unsafe_member_count'] = sum(n.startswith(('/', '\\')) or '\\' in n
                        or '..' in Path(n).parts for n in filenames)
                    if result['duplicate_member_count'] or result['unsafe_member_count']:
                        result.update(state='unsafe_zip_members', zip_integrity='not_checked')
                        return result
                    for member in members:
                        if member.is_dir():
                            continue
                        if member.flag_bits & 1:
                            result.update(state='encrypted_zip_not_inspected', zip_integrity='not_checked')
                            return result
                        with archive.open(member) as content:
                            for _ in iter(lambda: content.read(65536), b''):
                                if time.monotonic() > deadline:
                                    result['state'] = 'time_limit_not_inspected'
                                    return result
                    result.update(state='readable_zip', zip_integrity='crc_verified')
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, ValueError):
                result.update(state='corrupt_or_unsupported_zip', zip_integrity='failed')
            if signature(opened) != signature(os.fstat(handle.fileno())) or signature(opened) != signature(os.stat(name, dir_fd=directory_fd, follow_symlinks=False)):
                result.update(state='changed_during_inspection', zip_integrity='not_authoritative')
    except OSError:
        result['state'] = 'unsafe_or_unreadable_reference'
    return result


def scan(site_root):
    deadline = time.monotonic() + MAX_SECONDS
    site = Path(site_root)
    orders = site / 'orders'
    report = {'schema_version': SCHEMA_VERSION, 'status': 'INCOMPLETE',
              'scope': 'established SITE_PATH/orders/order_*.json and paid explicit-P1 delivery references in orders/delivery only',
              'production_config_evaluated': False, 'host_writes': False,
              'production_config_read_for_single_static_path_field': True,
              'configured_orders_dir_matches_known_path': None,
              'path_authority': 'matches existing sales-report scope; custom ORDERS_DIR/DELIVERY_DIR outside this scope not examined',
              'limits': {'orders': MAX_ORDERS, 'order_bytes': MAX_ORDER_BYTES, 'archives': MAX_ARCHIVES,
                         'zip_bytes': MAX_ZIP_BYTES, 'members': MAX_ZIP_MEMBERS,
                         'uncompressed_bytes': MAX_UNCOMPRESSED, 'seconds': MAX_SECONDS},
              'order_files': {}, 'status_counts': {}, 'item_sku_position_counts': {},
              'p1_order_counts': {}, 'archives': [], 'remaining_blockers': []}
    if not directory_allowed(orders):
        report['remaining_blockers'] = ['known_orders_directory_missing_unsafe_or_unreadable']
        return report
    with contextlib.ExitStack() as scope:
        try:
            site_fd = os.open(site, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            scope.callback(os.close, site_fd)
            report['configured_orders_dir_matches_known_path'] = configured_orders_match(site_fd, os.path.abspath(orders))
            orders_fd = os.open('orders', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=site_fd)
        except OSError:
            report['remaining_blockers'] = ['known_orders_directory_missing_unsafe_or_unreadable']
            return report
        scope.callback(os.close, orders_fd)
        return scan_open_orders(orders_fd, deadline, report, scope)


def scan_open_orders(orders_fd, deadline, report, scope):
    before_snapshot = order_snapshot(orders_fd)
    before_names = sorted(before_snapshot)
    errors, statuses, skus, p1_counts = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    references = {}
    for name in before_names[:MAX_ORDERS]:
        if time.monotonic() > deadline:
            errors['time_limit'] += 1
            break
        try:
            handle, opened = open_readonly(name, orders_fd)
            with handle:
                if opened.st_size > MAX_ORDER_BYTES:
                    errors['oversize'] += 1
                    continue
                data = handle.read(MAX_ORDER_BYTES + 1)
                if len(data) > MAX_ORDER_BYTES:
                    errors['oversize'] += 1
                    continue
                if signature(opened) != signature(os.fstat(handle.fileno())) or signature(opened) != signature(os.stat(name, dir_fd=orders_fd, follow_symlinks=False)):
                    errors['changed_during_read'] += 1
                    continue
            order = json.loads(data)
            if not isinstance(order, dict):
                errors['not_object'] += 1
                continue
        except (OSError, ValueError, UnicodeError):
            errors['malformed_unsafe_or_unreadable'] += 1
            continue
        errors['valid_objects'] += 1
        raw_status = order.get('status')
        status = raw_status if isinstance(raw_status, str) and raw_status in STATUSES else 'other_or_missing'
        statuses[status] += 1
        positions = order.get('items') if isinstance(order.get('items'), list) else []
        for item in positions:
            sku = item.get('sku') if isinstance(item, dict) else None
            skus[sku if isinstance(sku, str) and sku in SKUS else 'other_or_missing'] += 1
        own = [p for p in positions if isinstance(p, dict) and p.get('sku') == 'p1']
        issued = order.get('delivery') if isinstance(order.get('delivery'), dict) else {}
        entries = issued.get('items') if isinstance(issued.get('items'), dict) else {}
        editions = issued.get('editions') if isinstance(issued.get('editions'), dict) else {}
        if not own and 'p1' not in entries and 'p1' not in editions:
            continue
        p1_counts['total_explicit_p1_orders'] += 1
        p1_counts['status_' + status] += 1
        p1_counts['explicit_item_sku' if own else 'explicit_delivery_key_only'] += 1
        basename = entries.get('p1')
        issued_state = 'issued' if safe_basename(basename) else ('invalid_delivery_entry' if 'p1' in entries else 'unissued')
        p1_counts[issued_state] += 1
        raw_pins = [p['edition'] for p in own if 'edition' in p]
        if 'p1' in editions:
            raw_pins.append(editions['p1'])
        valid = [pin(p) for p in raw_pins]
        if not raw_pins:
            pin_state = 'no_pin'
        elif not all(valid):
            pin_state = 'malformed_pin'
        elif len({(p['zip'], p['sha256']) for p in valid}) > 1:
            pin_state = 'conflicting_pins'
        else:
            pin_state = 'valid_recorded_pin'
        p1_counts[pin_state] += 1
        p1_counts[status + '__' + issued_state + '__' + pin_state] += 1
        if status != 'paid' or issued_state != 'issued':
            continue
        ref = references.setdefault(basename, {'count': 0, 'expected_sha256': set(), 'no_pin': 0,
                                               'invalid_or_conflicting_pin': 0, 'reference_mismatch': 0})
        ref['count'] += 1
        if pin_state == 'no_pin':
            ref['no_pin'] += 1
        elif pin_state != 'valid_recorded_pin':
            ref['invalid_or_conflicting_pin'] += 1
        else:
            ref['expected_sha256'].add(valid[0]['sha256'])
            if valid[0]['zip'] != basename:
                ref['reference_mismatch'] += 1
    try:
        delivery_fd = os.open('delivery', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=orders_fd)
        scope.callback(os.close, delivery_fd)
    except OSError:
        delivery_fd = None
    for basename, refs in sorted(references.items())[:MAX_ARCHIVES]:
        inspected = inspect_archive(delivery_fd, basename, deadline) if delivery_fd is not None else {
            'state': 'known_delivery_directory_missing_unsafe_or_unreadable', 'sha256': None,
            'zip_integrity': 'not_checked', 'historical_authority_verified': False}
        reference = {'kind': 'known_legacy_basename' if basename == KNOWN_LEGACY else 'other_basename',
                     'reference_fingerprint_sha256': digest(basename.encode()),
                     'paid_p1_order_references': refs['count'],
                     'unpinned_references': refs['no_pin'],
                     'malformed_or_conflicting_pin_references': refs['invalid_or_conflicting_pin'],
                     'pin_basename_mismatch_references': refs['reference_mismatch'],
                     'recorded_expected_sha256': sorted(refs['expected_sha256'])}
        if basename == KNOWN_LEGACY:
            reference['known_basename'] = KNOWN_LEGACY
        elif re.fullmatch(r'p1-[0-9a-f]{64}\.zip', basename):
            reference['kind'] = 'content_addressed_basename'
        reference.update(inspected)
        reference['recorded_pin_matches_current_bytes'] = inspected.get('state') == 'readable_zip' and bool(refs['expected_sha256']) and refs['expected_sha256'] == {inspected['sha256']} and not refs['reference_mismatch'] and not refs['invalid_or_conflicting_pin'] and not refs['no_pin']
        reference['recorded_pin_hash_mismatch'] = bool(refs['expected_sha256']) and inspected.get('sha256') is not None and refs['expected_sha256'] != {inspected['sha256']}
        report['archives'].append(reference)
    after_snapshot = order_snapshot(orders_fd)
    errors['matching_files_seen'] = len(before_names)
    report.update(order_files=dict(errors), status_counts=dict(statuses), item_sku_position_counts=dict(skus),
                  p1_order_counts=dict(p1_counts), scan_entries_stable=before_snapshot == after_snapshot)
    report['archive_state_group_counts'] = dict(collections.Counter(a['state'] for a in report['archives']))
    state_refs = collections.Counter()
    for archive in report['archives']:
        state_refs[archive['state']] += archive['paid_p1_order_references']
    report['paid_p1_archive_reference_state_counts'] = dict(state_refs)
    incomplete = report['configured_orders_dir_matches_known_path'] is not True or len(before_names) > MAX_ORDERS or len(references) > MAX_ARCHIVES or before_snapshot != after_snapshot or any(v for k, v in errors.items() if k not in {'matching_files_seen', 'valid_objects'})
    report['status'] = 'PARTIAL' if incomplete else 'SCANNED_KNOWN_SCOPE'
    report['counts_are_lower_bounds'] = bool(incomplete)
    report['archive_references_unique_seen'] = len(references)
    report['historical_inventory_complete'] = False
    report['remaining_blockers'] = ['historical_original_archive_and_pin_creation_time_not_verified',
        'custom_order_delivery_paths_not_examined_without_explicit_authority',
        'missing_or_unknown_sku_orders_not_classified_by_product_name']
    if report['configured_orders_dir_matches_known_path'] is not True:
        report['remaining_blockers'].append('configured_order_path_static_match_unknown_or_false_no_zero_p1_inference')
    if p1_counts.get('paid__unissued__no_pin'):
        report['remaining_blockers'].append('paid_unissued_p1_without_pin_requires_authoritative_original_archive')
    if any(a.get('unpinned_references') for a in report['archives']):
        report['remaining_blockers'].append('paid_issued_unpinned_p1_existing_zip_is_not_proof_of_historical_original')
    if any(a['state'] != 'readable_zip' for a in report['archives']):
        report['remaining_blockers'].append('one_or_more_paid_p1_archive_references_unverified')
    return report


def main():
    try:
        if len(sys.argv) != 2 or any(c in sys.argv[1] for c in '\r\n\x00'):
            raise ValueError('invalid arguments')
        report = scan(sys.argv[1])
    except BaseException:
        # Never expose exception strings, filesystem paths, order IDs or values.
        report = {'schema_version': SCHEMA_VERSION, 'status': 'FAILED_SANITIZED',
                  'host_writes': False, 'remaining_blockers': ['inventory_failed_no_zero_order_inference']}
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report['status'] in {'SCANNED_KNOWN_SCOPE', 'PARTIAL'} else 2


if __name__ == '__main__':
    sys.exit(main())
