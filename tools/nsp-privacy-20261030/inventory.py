"""Read-only project data inventory. Never emit contact values, order IDs or secrets."""
import collections
import hashlib
import json
import os
import re
import sys
import tarfile
import time
import zipfile
from pathlib import Path

START = time.monotonic()
HOME = Path(sys.argv[1]).resolve()
DOMAINS = ('marzhavbetone.ru', 'nastoronepodryadchika.ru')
LIMIT = 12000
visited = 0

def budget():
    global visited
    visited += 1
    if visited > LIMIT or time.monotonic() - START > 65:
        raise RuntimeError('INVENTORY_BUDGET')

def relative(p):
    try:
        return '[HOME]/' + str(Path(p).relative_to(HOME))
    except ValueError:
        return '[OUTSIDE_HOME]'

def configured_path(source, key, root):
    match = re.search(r"define\s*\(\s*['\"]" + key + r"['\"]\s*,\s*(.*?)\);", source, re.S)
    if not match:
        return None
    expr = match[1].strip()
    match = re.fullmatch(r"(['\"])([^'\"]+)\1", expr)
    if match:
        p = Path(match[2])
        return p if p.is_absolute() else None
    match = re.fullmatch(r"(__DIR__|dirname\(__DIR__\))\s*\.\s*(['\"])([^'\"]+)\2", expr)
    if match:
        return Path(str(root if match[1] == '__DIR__' else root.parent) + match[3])
    return None

def walk(root, depth=0):
    if not root.is_dir() or root.is_symlink():
        return
    for p in sorted(root.iterdir()):
        budget()
        if p.is_symlink():
            continue
        if p.is_dir():
            if depth < 4:
                yield from walk(p, depth + 1)
        elif p.is_file():
            yield p

def order_inventory(root):
    result = {'path': relative(root), 'exists': root.is_dir(), 'symlink': root.is_symlink(), 'files': 0,
              'json_records': 0, 'invalid_json': 0, 'with_email': 0, 'with_phone': 0,
              'statuses': {}, 'paid_records': 0, 'paid_100_kopeck': 0, 'recorded_downloads': 0,
              'download_records': 0, 'old_origin': 0, 'new_origin': 0, 'unattributed_origin': 0,
              'expired_unpaid_records': 0, 'other_file_types': {}}
    fingerprints = set()
    statuses = collections.Counter()
    types = collections.Counter()
    dates = []
    for p in walk(root):
        result['files'] += 1
        types[p.suffix.lower() or '[none]'] += 1
        if p.suffix != '.json' or p.stat().st_size > 2000000:
            continue
        raw = p.read_bytes()
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError):
            result['invalid_json'] += 1
            continue
        if not isinstance(record, dict) or not any(k in record for k in ('email', 'phone', 'payment_id', 'status')):
            continue
        fingerprints.add(hashlib.sha256(raw).digest())
        result['json_records'] += 1
        result['with_email'] += bool(record.get('email'))
        result['with_phone'] += bool(record.get('phone'))
        status = str(record.get('status', '[missing]'))
        statuses[status if status in ('paid', 'pending', 'canceled', 'cancelled', 'failed', 'succeeded', 'test') else '[other]'] += 1
        paid = status in ('paid', 'succeeded') or bool(record.get('paid_at'))
        result['paid_records'] += paid
        result['paid_100_kopeck'] += paid and record.get('total') == 100
        delivery = record.get('delivery') if isinstance(record.get('delivery'), dict) else {}
        downloads = int(delivery.get('downloads') or 0)
        result['recorded_downloads'] += downloads
        result['download_records'] += downloads > 0
        touches = json.dumps(record.get('attribution') or {}, ensure_ascii=False)
        if 'nastoronepodryadchika.ru' in touches:
            result['new_origin'] += 1
        elif 'marzhavbetone.ru' in touches:
            result['old_origin'] += 1
        else:
            result['unattributed_origin'] += 1
        created = str(record.get('created_at', ''))
        if re.match(r'^20\d\d-\d\d-\d\d', created):
            dates.append(created[:10])
            result['expired_unpaid_records'] += not paid and created[:10] < '2026-10-29'
    result['statuses'] = dict(statuses)
    result['other_file_types'] = dict(types)
    result['created_date_range'] = [min(dates), max(dates)] if dates else []
    return result, fingerprints

def telemetry_inventory(path):
    result = {'path': relative(path), 'exists': path.is_dir(), 'files': 0, 'bytes': 0,
              'json_lines': 0, 'invalid_lines': 0, 'event_types': {}, 'contact_field_lines': 0}
    events = collections.Counter()
    for p in walk(path):
        result['files'] += 1
        result['bytes'] += p.stat().st_size
        if p.suffix not in ('.jsonl', '.log') or p.stat().st_size > 20000000:
            continue
        with p.open('r', errors='replace') as stream:
            for index,line in enumerate(stream):
                if index >= 1500:
                    result['sample_limited'] = True
                    break
                budget()
                try:
                    row = json.loads(line)
                except ValueError:
                    result['invalid_lines'] += 1
                    continue
                result['json_lines'] += 1
                event = row.get('event_type', '') if isinstance(row, dict) else ''
                events[event if re.fullmatch(r'funnel\.[a-z_]+', str(event)) else '[other]'] += 1
                result['contact_field_lines'] += bool(re.search(r'"(?:email|phone|contact|name)"\s*:', line))
    result['event_types'] = dict(events)
    return result

result = {'status': 'READ_ONLY', 'public_writes': 0, 'deleted_files': 0, 'sites': [], 'stores': [],
          'mailbox_hints': [], 'project_backups': [], 'coverage_limits': ['Yandex mailbox and hosting-provider backups require separate access; no email values exported']}
stores = {}
for domain in DOMAINS:
    root = HOME / 'www' / domain
    cfg = root / 'config.php'
    source = cfg.read_text(errors='replace') if cfg.is_file() else ''
    path = configured_path(source, 'ORDERS_DIR', root)
    orders = path or root / 'orders'
    entry = {'domain': domain, 'root_exists': root.is_dir(), 'config_sha256': hashlib.sha256(source.encode()).hexdigest(),
             'orders_path_parsed': path is not None, 'orders_path': relative(orders),
             'redirects_to_new_domain': bool(re.search(r'Redirect|RewriteRule', (root / '.htaccess').read_text(errors='replace') if (root / '.htaccess').is_file() else '')) and 'nastoronepodryadchika.ru' in ((root / '.htaccess').read_text(errors='replace') if (root / '.htaccess').is_file() else '')}
    if source:
        entry['mail_transport_mentions'] = {k: bool(re.search(k, source, re.I)) for k in ('smtp', 'yandex', 'mail\\(')}
    result['sites'].append(entry)
    key = str(orders.resolve())
    if key not in stores:
        inv, fingerprints = order_inventory(orders)
        stores[key] = (inv, fingerprints)
        result['stores'].append(inv)
    for location in ('email', 'mail'):
        mailbox = HOME / location / domain
        if mailbox.is_dir():
            count = sum(1 for _ in walk(mailbox))
            result['mailbox_hints'].append({'path': relative(mailbox), 'files': count})

store_values = list(stores.values())
result['store_count'] = len(stores)
result['duplicate_order_records_between_stores'] = len(store_values[0][1] & store_values[1][1]) if len(stores) == 2 else None
result['telemetry'] = [telemetry_inventory(p) for p in (HOME/'www/mvb-private/funnel-outbox', HOME/'mvb-private/funnel-outbox')]

for base in (HOME/'nsp-migration-private', HOME/'backups', HOME/'backup', HOME/'www/marzhavbetone.ru/backup', HOME/'www/nastoronepodryadchika.ru/backup'):
    if not base.is_dir():
        continue
    info = {'path': relative(base), 'files': 0, 'archive_count': 0, 'archives_with_order_or_contact_paths': 0,
            'loose_order_json_count': 0, 'archive_read_errors': 0, 'top_level_subdirectories': []}
    info['top_level_subdirectories'] = [p.name for p in base.iterdir() if p.is_dir() and re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',p.name)][:100]
    for p in walk(base):
        info['files'] += 1
        if p.name.startswith('order_') and p.suffix == '.json':
            info['loose_order_json_count'] += 1
        if not (p.name.endswith(('.zip', '.tar', '.tar.gz', '.tgz'))):
            continue
        info['archive_count'] += 1
        if p.stat().st_size > 150000000:
            result['coverage_limits'].append('OVERSIZE_ARCHIVE_NOT_INSPECTED')
            continue
        try:
            if p.suffix == '.zip':
                with zipfile.ZipFile(p) as archive:
                    names = archive.namelist()
            else:
                with tarfile.open(p) as archive:
                    names = [m.name for m in archive]
            info['archives_with_order_or_contact_paths'] += any(re.search(r'(?:^|/)(?:orders?|leads?|contacts?)(?:/|[._-])', n, re.I) for n in names)
        except (ValueError, OSError, zipfile.BadZipFile, tarfile.TarError):
            info['archive_read_errors'] += 1
    result['project_backups'].append(info)

result['home_directory_names'] = [p.name for p in HOME.iterdir() if p.is_dir() and not p.name.startswith('.') and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',p.name)][:100]
result['elapsed_seconds'] = round(time.monotonic() - START, 2)
print(json.dumps(result, ensure_ascii=False, indent=2))
