"""Exact-plan legacy contact cleanup. No raw-contact backup or export is made."""
import collections
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

START = time.monotonic()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def budget():
    need(time.monotonic() - START < 150, 'CLEANUP_TIME_BUDGET')

def financial(record):
    allowed = ('id', 'created_at', 'paid_at', 'status', 'payment_id', 'total', 'currency')
    result = {key: record[key] for key in allowed if key in record}
    result['items'] = [{key: item[key] for key in ('sku', 'name', 'price') if key in item}
                       for item in record.get('items', []) if isinstance(item, dict)]
    return (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()

def archive_members(path):
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    with tarfile.open(path) as archive:
        return [m.name for m in archive]

def rewrite_archive(path, remove):
    """Verify every retained member, then atomically replace; do not keep the PI original."""
    fd, name = tempfile.mkstemp(prefix='.privacy-cleanup-', dir=str(path.parent))
    os.close(fd)
    tmp = Path(name)
    try:
        before = []
        if path.suffix == '.zip':
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(tmp, 'w') as dest:
                dest.comment = source.comment
                for item in source.infolist():
                    budget()
                    if item.filename in remove:
                        continue
                    data = source.read(item)
                    before.append((item.filename, sha(data)))
                    dest.writestr(item, data)
            with zipfile.ZipFile(tmp) as verify:
                after = [(item.filename, sha(verify.read(item))) for item in verify.infolist()]
        else:
            mode = 'w:gz' if path.name.endswith(('.tgz', '.tar.gz')) else 'w'
            with tarfile.open(path) as source, tarfile.open(tmp, mode) as dest:
                for item in source:
                    budget()
                    if item.name in remove:
                        continue
                    data = source.extractfile(item).read() if item.isfile() else None
                    before.append((item.name, sha(data) if data is not None else None))
                    dest.addfile(item, io.BytesIO(data) if data is not None else None)
            with tarfile.open(tmp) as verify:
                after = [(item.name, sha(verify.extractfile(item).read()) if item.isfile() else None) for item in verify]
        need(before == after, 'ARCHIVE_RETAINED_MEMBER_MISMATCH')
        os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
        need(not set(archive_members(path)) & set(remove), 'ARCHIVE_REMOVAL_VERIFY')
    finally:
        if tmp.exists():
            tmp.unlink()

def main(home, mode, expected=None, fixture=False):
    home = Path(home).resolve()
    old = home / 'www/marzhavbetone.ru/orders'
    current = home / 'nsp-production-private/orders'
    need(old.is_dir() and not old.is_symlink(), 'OLD_ORDERS_NOT_REGULAR_DIRECTORY')
    need(current.is_dir() and current.resolve() != old.resolve(), 'CURRENT_STORE_ISOLATION')
    sources = []
    for path in sorted(old.glob('order_*.json')):
        need(path.is_file() and not path.is_symlink(), 'ORDER_SYMLINK')
        raw = path.read_bytes()
        record = json.loads(raw)
        need(isinstance(record, dict) and str(record.get('id', path.stem)) == path.stem, 'ORDER_ID_MISMATCH')
        paid = record.get('status') in ('paid', 'succeeded') or bool(record.get('paid_at'))
        if paid:
            need(record.get('total') == 100, 'NON_TEST_PAYMENT_REQUIRES_RETENTION_REVIEW')
        else:
            need(record.get('status') in ('pending', 'canceled', 'cancelled', 'failed') and
                 str(record.get('created_at', ''))[:10] < '2026-10-29', 'ACTIVE_OR_UNKNOWN_ORDER')
        sources.append((path, sha(raw), record, paid))
    need(len(sources) == 18 if not fixture else bool(sources), 'LEGACY_RECORD_COUNT_CHANGED')
    need(sum(row[3] for row in sources) == 8 if not fixture else True, 'LEGACY_PAYMENT_COUNT_CHANGED')
    names = {row[0].name for row in sources}
    backups = []
    loose = []
    coverage = []
    unknown_loose_order_copies = 0
    unknown_archived_order_copies = 0
    empty_synthetic_probe_records = 0
    for name in ('nsp-migration-private', 'nsp-migration-backups', 'p3-release-backups', 'p11-release-backups',
                 'p5-release-backups', 't2-release-backups', 't3-release-backups', 'remaining-release-backups'):
        root = home / name
        if not root.is_dir() or root.is_symlink():
            continue
        files = 0
        for folder, dirs, items in os.walk(root, followlinks=False):
            dirs[:] = [n for n in dirs if not (Path(folder) / n).is_symlink()]
            for item in items:
                budget()
                files += 1
                need(files < 20000, 'BACKUP_FILE_COUNT_LIMIT')
                path = Path(folder) / item
                if path.is_symlink() or not path.is_file():
                    continue
                if path.name in names:
                    loose.append((path, sha(path.read_bytes())))
                elif path.name.startswith('order_') and path.suffix == '.json':
                    probe = json.loads(path.read_bytes())
                    if probe.get('migration_probe') and probe.get('provider_payment_performed') is False and not probe.get('email') and not probe.get('phone'):
                        empty_synthetic_probe_records += 1
                    else:
                        unknown_loose_order_copies += 1
                elif path.name.endswith(('.zip', '.tar', '.tgz', '.tar.gz')):
                    need(path.stat().st_size < 150000000, 'ARCHIVE_SIZE_LIMIT')
                    members = archive_members(path)
                    remove = [n for n in members if Path(n).name in names]
                    unknown_archived_order_copies += sum(Path(n).name.startswith('order_') and n.endswith('.json') and Path(n).name not in names for n in members)
                    if remove:
                        backups.append((path, sha(path.read_bytes()), remove))
        coverage.append({'area': name, 'files_inspected': files})
    # Hosting-owned logs and the external Yandex inbox are explicitly not represented as erased.
    log_hints = []
    log_targets = []
    logs = home / 'logs'
    if logs.is_dir():
        for path in logs.rglob('*'):
            budget()
            if re.fullmatch(r'marzhavbetone\.ru\.(?:access|error)\.log(?:\.\d+\.gz)?',path.name) and path.is_file():
                need(not path.is_symlink(), 'LOG_SYMLINK')
                stat = path.stat()
                writable = os.access(str(path), os.W_OK)
                rotated = path.name.endswith('.gz')
                log_hints.append({'kind': 'legacy_domain_log', 'bytes': stat.st_size, 'writable': writable, 'rotated': rotated})
                if writable:
                    # Active append-only log contents may grow; exact inode/permissions still bind the scope.
                    log_targets.append((path, sha(path.read_bytes()) if rotated else None, stat.st_ino, stat.st_mode, stat.st_uid))
    raw_plan = [(str(p.relative_to(home)), digest) for p, digest, _, _ in sources]
    raw_plan += [(str(p.relative_to(home)), digest, remove) for p, digest, remove in backups]
    raw_plan += [(str(p.relative_to(home)), digest) for p, digest in loose]
    raw_plan += [(str(p.relative_to(home)), digest, inode, mode, uid) for p,digest,inode,mode,uid in log_targets]
    digest = sha(json.dumps(raw_plan, sort_keys=True).encode())
    report = {'status': 'PLAN', 'mode': mode, 'plan_digest': digest,
              'legacy_records': len(sources), 'unpaid_to_delete': sum(not r[3] for r in sources),
              'paid_minimum_records_to_retain_privately': sum(r[3] for r in sources),
              'backup_archives_to_scrub': len(backups), 'archive_record_copies_to_delete': sum(len(r[2]) for r in backups),
              'loose_backup_record_copies_to_delete': len(loose), 'backup_coverage': coverage,
              'unknown_loose_order_copies_preserved': unknown_loose_order_copies,
              'unknown_archived_order_copies_preserved': unknown_archived_order_copies,
              'verified_empty_synthetic_probe_records_preserved': empty_synthetic_probe_records,
              'legacy_rotated_logs_to_delete': sum(d is not None for _,d,_,_,_ in log_targets),
              'legacy_active_logs_to_truncate': sum(d is None for _,d,_,_,_ in log_targets),
              'legacy_log_hints': log_hints, 'raw_user_data_exported': False,
              'limits': ['Yandex inbox not accessed', 'New legacy redirect requests may create fresh security-log entries after cleanup', 'Provider snapshots require separate confirmation',
                         'Shared telemetry without contacts not removed by this order-contact cleanup']}
    if mode == 'plan':
        return report
    need(mode == 'apply' and expected == digest, 'EXACT_PLAN_REQUIRED')
    new_before = {p.name: sha(p.read_bytes()) for p in current.glob('*.json') if p.is_file()}
    php_before = {str(p.relative_to(home)): sha(p.read_bytes()) for domain in ('marzhavbetone.ru', 'nastoronepodryadchika.ru')
                  for p in (home/'www'/domain).glob('*.php') if p.is_file()}
    vault = home / 'nsp-legacy-financial-records'
    need(not vault.exists(), 'FINANCIAL_VAULT_ALREADY_EXISTS')
    vault.mkdir(mode=0o700)
    for path, before, record, paid in sources:
        need(sha(path.read_bytes()) == before, 'ORDER_CHANGED_BEFORE_RETENTION')
        if paid:
            target = vault / path.name
            payload = financial(record)
            with target.open('xb') as stream:
                stream.write(payload)
            os.chmod(target, 0o600)
            need(target.read_bytes() == payload, 'FINANCIAL_MINIMUM_VERIFY')
    for path, before, remove in backups:
        need(sha(path.read_bytes()) == before, 'BACKUP_ARCHIVE_CHANGED')
        rewrite_archive(path, remove)
    for path, before in loose:
        need(sha(path.read_bytes()) == before, 'LOOSE_BACKUP_CHANGED')
        path.unlink()
    for path, before, _, _ in sources:
        need(sha(path.read_bytes()) == before, 'ORDER_CHANGED_BEFORE_DELETE')
        path.unlink()
        lock = path.with_name(path.name + '.lock')
        if lock.is_file() and not lock.is_symlink():
            lock.unlink()
    for path, before, inode, mode_bits, owner in log_targets:
        stat = path.stat()
        need(not path.is_symlink() and (stat.st_ino,stat.st_mode,stat.st_uid)==(inode,mode_bits,owner),'LOG_IDENTITY_CHANGED')
        if before is not None:
            need(sha(path.read_bytes())==before,'ROTATED_LOG_CHANGED')
            path.unlink()
        else:
            with path.open('r+b') as stream:
                need(os.fstat(stream.fileno()).st_ino==inode,'ACTIVE_LOG_REPLACED')
                stream.truncate(0)
                stream.flush()
                os.fsync(stream.fileno())
    need(not list(old.glob('order_*.json')), 'LEGACY_JSON_REMAINS')
    need(all((current / name).is_file() and sha((current/name).read_bytes()) == value for name,value in new_before.items()), 'CURRENT_ORDER_CHANGED')
    need(all(sha((home / p).read_bytes()) == value for p,value in php_before.items()), 'PHP_CHANGED')
    for path, _, remove in backups:
        need(not set(archive_members(path)) & set(remove), 'BACKUP_RESCAN_FAILED')
    need(all(not p.exists() for p,_ in loose), 'LOOSE_BACKUP_REMAINS')
    report.update(status='PASS_SCOPED_LEGACY_CONTACT_CLEANUP', deleted_legacy_records=len(sources),
                  legacy_contact_record_files_remaining=0, financial_minimum_records=len(list(vault.glob('*.json'))),
                  financial_minimum_has_contact_fields=any(any(k in json.loads(p.read_bytes()) for k in ('email','phone','attribution','delivery')) for p in vault.glob('*.json')),
                  current_order_records_preserved=len(new_before), runtime_php='UNCHANGED', no_raw_contact_backup_created=True)
    return report

if __name__ == '__main__':
    try:
        print(json.dumps(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None), ensure_ascii=False, indent=2))
    except Exception as error:
        print(json.dumps({'status':'STOPPED','reason':str(error),'no_automatic_retry':True}), file=sys.stderr)
        raise SystemExit(1)
