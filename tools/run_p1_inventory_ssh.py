#!/usr/bin/env python3
"""Runner-only SSH transport: discard raw stderr, validate/redact stdout."""
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import p1_production_inventory as I

TOP = {'schema_version', 'status', 'scope', 'production_config_evaluated', 'host_writes',
       'production_config_read_for_single_static_path_field', 'configured_orders_dir_matches_known_path',
       'path_authority', 'limits', 'order_files', 'status_counts', 'item_sku_position_counts',
       'p1_order_counts', 'archives', 'remaining_blockers', 'scan_entries_stable',
       'archive_state_group_counts', 'paid_p1_archive_reference_state_counts',
       'counts_are_lower_bounds', 'archive_references_unique_seen', 'historical_inventory_complete'}
ARCHIVE = {'kind', 'reference_fingerprint_sha256', 'paid_p1_order_references', 'unpinned_references',
           'malformed_or_conflicting_pin_references', 'pin_basename_mismatch_references',
           'recorded_expected_sha256', 'known_basename', 'state', 'sha256', 'zip_integrity',
           'known_p1_members', 'unknown_member_count', 'historical_authority_verified',
           'duplicate_member_count', 'unsafe_member_count', 'recorded_pin_matches_current_bytes',
           'recorded_pin_hash_mismatch'}
STATES = {'unreadable', 'missing_in_known_delivery_scope', 'size_limit_not_inspected',
          'time_limit_not_inspected', 'zip_limit_not_inspected', 'unsafe_zip_members',
          'encrypted_zip_not_inspected', 'readable_zip', 'corrupt_or_unsupported_zip',
          'changed_during_inspection', 'unsafe_or_unreadable_reference',
          'known_delivery_directory_missing_unsafe_or_unreadable'}
BLOCKERS = {'known_orders_directory_missing_unsafe_or_unreadable', 'inventory_failed_no_zero_order_inference',
            'historical_original_archive_and_pin_creation_time_not_verified',
            'custom_order_delivery_paths_not_examined_without_explicit_authority',
            'missing_or_unknown_sku_orders_not_classified_by_product_name',
            'configured_order_path_static_match_unknown_or_false_no_zero_p1_inference',
            'paid_unissued_p1_without_pin_requires_authoritative_original_archive',
            'paid_issued_unpinned_p1_existing_zip_is_not_proof_of_historical_original',
            'one_or_more_paid_p1_archive_references_unverified'}


def counters(value, keys):
    return isinstance(value, dict) and set(value) <= keys and all(type(n) is int and 0 <= n <= 10**9 for n in value.values())


def _validate(value):
    """Reject any unsolicited field/string, even if SSH returns valid JSON."""
    if not isinstance(value, dict) or not set(value) <= TOP or value.get('schema_version') != 1:
        return False
    if value.get('status') not in {'SCANNED_KNOWN_SCOPE', 'PARTIAL', 'INCOMPLETE', 'FAILED_SANITIZED'}:
        return False
    if value.get('host_writes') is not False or value.get('production_config_evaluated', False) is not False:
        return False
    for field in {'production_config_read_for_single_static_path_field', 'scan_entries_stable', 'counts_are_lower_bounds', 'historical_inventory_complete'}:
        if field in value and type(value[field]) is not bool:
            return False
    configured = value.get('configured_orders_dir_matches_known_path')
    if configured is not None and type(configured) is not bool:
        return False
    if 'scope' in value and value['scope'] != 'established SITE_PATH/orders/order_*.json and paid explicit-P1 delivery references in orders/delivery only':
        return False
    if 'path_authority' in value and value['path_authority'] != 'matches existing sales-report scope; custom ORDERS_DIR/DELIVERY_DIR outside this scope not examined':
        return False
    if 'limits' in value and not counters(value['limits'], {'orders', 'order_bytes', 'archives', 'zip_bytes', 'members', 'uncompressed_bytes', 'seconds'}):
        return False
    types = I.STATUSES | {'other_or_missing'}
    p1keys = {'total_explicit_p1_orders', 'explicit_item_sku', 'explicit_delivery_key_only',
              'issued', 'unissued', 'invalid_delivery_entry', 'no_pin', 'malformed_pin', 'conflicting_pins', 'valid_recorded_pin'}
    p1keys |= {'status_' + s for s in types}
    p1keys |= {s + '__' + issued + '__' + pin for s in types
               for issued in {'issued', 'unissued', 'invalid_delivery_entry'}
               for pin in {'no_pin', 'malformed_pin', 'conflicting_pins', 'valid_recorded_pin'}}
    count_maps = {'order_files': {'time_limit', 'oversize', 'changed_during_read', 'not_object',
                   'malformed_unsafe_or_unreadable', 'valid_objects', 'matching_files_seen'},
                  'status_counts': types, 'item_sku_position_counts': I.SKUS | {'other_or_missing'},
                  'p1_order_counts': p1keys, 'archive_state_group_counts': STATES,
                  'paid_p1_archive_reference_state_counts': STATES}
    if any(field in value and not counters(value[field], keys) for field, keys in count_maps.items()):
        return False
    if 'archive_references_unique_seen' in value and (type(value['archive_references_unique_seen']) is not int or not 0 <= value['archive_references_unique_seen'] <= 10**9):
        return False
    if not isinstance(value.get('remaining_blockers'), list) or any(b not in BLOCKERS for b in value['remaining_blockers']):
        return False
    if not isinstance(value.get('archives', []), list):
        return False
    for archive in value.get('archives', []):
        if not isinstance(archive, dict) or not set(archive) <= ARCHIVE or archive.get('state') not in STATES:
            return False
        if archive.get('kind') not in {'known_legacy_basename', 'other_basename', 'content_addressed_basename'}:
            return False
        if archive.get('historical_authority_verified') is not False:
            return False
        if archive.get('zip_integrity') not in {'not_checked', 'crc_verified', 'failed', 'not_authoritative'}:
            return False
        for field in {'sha256', 'reference_fingerprint_sha256'}:
            if archive.get(field) is not None and not (isinstance(archive[field], str) and I.HEX.fullmatch(archive[field])):
                return False
        if not isinstance(archive.get('recorded_expected_sha256'), list) or any(not isinstance(s, str) or not I.HEX.fullmatch(s) for s in archive['recorded_expected_sha256']):
            return False
        if 'known_basename' in archive and archive['known_basename'] != I.KNOWN_LEGACY:
            return False
        if not isinstance(archive.get('known_p1_members', []), list) or any(n not in I.KNOWN_MEMBERS for n in archive.get('known_p1_members', [])):
            return False
        numeric = {'paid_p1_order_references', 'unpinned_references', 'malformed_or_conflicting_pin_references',
                   'pin_basename_mismatch_references', 'unknown_member_count', 'duplicate_member_count', 'unsafe_member_count'}
        if any(field in archive and archive[field] is not None and (type(archive[field]) is not int or not 0 <= archive[field] <= 10**9) for field in numeric):
            return False
        if any(field in archive and type(archive[field]) is not bool for field in {'recorded_pin_matches_current_bytes', 'recorded_pin_hash_mismatch'}):
            return False
    return True


def validate(value):
    try:
        return _validate(value)
    except BaseException:
        return False


def invocation(env):
    host, user, site, ssh_port = [env.get(k, '') for k in ['INVENTORY_HOST', 'INVENTORY_USER', 'SITE_PATH', 'SSH_PORT']]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]*', host) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', user):
        raise ValueError('invalid access settings')
    if not ssh_port.isdecimal() or not 1 <= int(ssh_port) <= 65535 or not site or any(c in site for c in '\r\n\x00'):
        raise ValueError('invalid established scope')
    return ['ssh', '-i', str(Path.home() / '.ssh/deploy_key'), '-p', ssh_port,
            '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=20', '-o', 'ConnectionAttempts=1',
            user + '@' + host, 'python3 -B - ' + shlex.quote(site)]


def main():
    out = Path('inventory-output')
    out.mkdir(exist_ok=True)
    failure = {'schema_version': 1, 'status': 'TRANSPORT_FAILED_SANITIZED', 'host_writes': False,
               'remaining_blockers': ['single_read_attempt_failed_no_retry_no_zero_order_inference']}
    report, code = failure, 2
    try:
        command = invocation(os.environ)
        script = Path(__file__).with_name('p1_production_inventory.py').read_bytes()
        result = subprocess.run(command, input=script, capture_output=True, timeout=215)
        if len(result.stdout) <= 1024 * 1024:
            candidate = json.loads(result.stdout)
            if validate(candidate):
                report = candidate
                code = 0 if result.returncode == 0 else 2
    except BaseException:
        pass
    # Raw stdout/stderr, exception strings, SSH destinations and settings never logged.
    (out / 'P1_inventory_report.json').write_text(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    print('P1 read-only inventory: sanitized artifact produced; no raw remote output logged.')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
