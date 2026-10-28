#!/usr/bin/env python3
"""Read-only, bounded, redacted corroboration of the owner's service purchase.

Never imports PHP config, calls endpoints, opens a buyer link, sends mail or writes
on the hosting server. Unsupported paths fail closed. All output is whitelisted.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback
from urllib.parse import parse_qs, urlsplit

LIMIT = 2 * 1024 * 1024
EVENTS = {'download.link_opened', 'download.file_served', 'download.failed'}
REASONS = {'invalid_link', 'access_denied', 'not_found', 'expired', 'download_limit',
           'file_unavailable', 'server_error', 'read_failed'}


def parsed_time(value):
    # Hosting may have Python 3.6: fromisoformat is not available there.
    text = str(value).replace('Z', '+0000')
    text = re.sub(r'([+-]\d{2}):(\d{2})$', r'\1\2', text)
    for shape in ['%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z',
                  '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
        try:
            return dt.datetime.strptime(text, shape)
        except ValueError:
            pass
    return None


def timestamp(value):
    parsed = parsed_time(value)
    return parsed.isoformat() if parsed else None


def tail(path):
    with path.open('rb') as stream:
        size = stream.seek(0, 2)
        stream.seek(max(0, size - LIMIT))
        data = stream.read(LIMIT)
    if size > LIMIT:
        data = data.split(b'\n', 1)[-1]
    return data.decode('utf-8', errors='replace').splitlines()


def orders_path(site):
    # Parse only the path constant. Executing config could create directories.
    text = (site / 'config.php').read_text()
    match = re.search(r"(?m)^\s*define\(\s*['\"]ORDERS_DIR['\"]\s*,\s*(.*?)\s*\);", text)
    if not match:
        raise ValueError('UNSUPPORTED_ORDERS_PATH')
    expression = match[1]
    relative = re.fullmatch(r"__DIR__\s*\.\s*(['\"])(/[^'\"]+)\1", expression)
    absolute = re.fullmatch(r"(['\"])(/[^'\"]+)\1", expression)
    if relative:
        return site / relative[2].lstrip('/')
    if absolute:
        return Path(absolute[2])
    raise ValueError('UNSUPPORTED_ORDERS_PATH')


def inspect(site, home):
    orders = orders_path(site)
    files = sorted(orders.glob('order_*.json'))
    if len(files) > 5000:
        raise ValueError('ORDER_SCAN_BUDGET_EXCEEDED')
    matches = []
    for path in files:
        if path.stat().st_size > LIMIT:
            continue
        try:
            order = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(order, dict):
            continue
        items = order.get('items', [])
        if (order.get('total') == 100 and items
                and all(isinstance(i, dict) and i.get('sku') == 'test1' for i in items)):
            matches.append(order)
    matches.sort(key=lambda o: timestamp(o.get('created_at')) or '', reverse=True)
    if not matches:
        raise ValueError('NO_ONE_RUBLE_SERVICE_ORDER')
    order = matches[0]
    oid = str(order.get('id', ''))
    if not re.fullmatch(r'order_[a-zA-Z0-9_]+', oid):
        raise ValueError('INVALID_ORDER_ID_SHAPE')
    delivery = order.get('delivery') or {}
    archive = delivery.get('items', {}).get('test1')
    archive_path = orders / 'delivery' / str(archive)
    archive_ok = (isinstance(archive, str) and Path(archive).name == archive
                  and archive_path.is_file() and not archive_path.is_symlink())
    archive_bytes = archive_path.stat().st_size if archive_ok else None
    public_files = ['index.html', 'app.js', 'lead.php', 'payment.php',
                    'webhook.php', 'products-config.php', 'download.php']
    hashes = {name: hashlib.sha256((site / name).read_bytes()).hexdigest()
              for name in public_files if (site / name).is_file()}
    download_source = (site / 'download.php').read_text()

    # Bounded tails only. No raw lines, URLs, addresses, IPs or tokens escape.
    paths = [home / 'mail.log']
    for folder in [home / 'logs', Path('/var/www/httpd-logs')]:
        if folder.is_dir():
            paths.extend(sorted(folder.glob('*nastoronepodryadchika.ru*'))[:20])
    seen, access, mail_matches, readable = set(), [], 0, 0
    email = str(order.get('email') or '')
    sent_at = timestamp(delivery.get('email_sent_at'))
    access_pattern = re.compile(r'\[([^\]]+)\]\s+"(GET|HEAD)\s+(\S+)\s+[^" ]+"\s+(\d{3})\s+(\d+|-)')
    for path in paths[:41]:
        try:
            stat = path.stat()
            inode = (stat.st_dev, stat.st_ino)
            if not path.is_file() or inode in seen:
                continue
            seen.add(inode)
            lines = tail(path)
            readable += 1
        except OSError:
            continue
        for line in lines:
            match = access_pattern.search(line)
            if match:
                try:
                    parsed = urlsplit(match[3])
                except ValueError:
                    continue
                if parsed.path != '/download.php' or parse_qs(parsed.query).get('o') != [oid]:
                    continue
                try:
                    at = dt.datetime.strptime(match[1], '%d/%b/%Y:%H:%M:%S %z').isoformat()
                except ValueError:
                    at = None
                size = int(match[5]) if match[5].isdigit() else None
                access.append({'at': at, 'method': match[2], 'http_status': int(match[4]),
                               'body_bytes': size,
                               'full_archive_bytes': match[2] == 'GET' and match[4] == '200'
                                   and archive_bytes is not None and size == archive_bytes})
            elif (path.name == 'mail.log' and email and 'products-config.php' in line
                    and re.search(r'\bTo:\s*' + re.escape(email) + r'(?=[,\s]|$)', line)):
                # A transport log match is only corroboration, never inbox proof.
                date_match = re.search(r'\[(\d{2}-[A-Za-z]{3}-\d{4} \d{2}:\d{2}:\d{2})\s+([^\]]+)\]', line)
                if date_match and sent_at:
                    try:
                        mail_time = dt.datetime.strptime(date_match[1], '%d-%b-%Y %H:%M:%S')
                        sent_time = parsed_time(sent_at)
                        # PHP's mail log may use a named timezone; require exact
                        # local wall-clock proximity rather than invent an offset.
                        if abs((mail_time - sent_time.replace(tzinfo=None)).total_seconds()) <= 10:
                            mail_matches += 1
                    except ValueError:
                        pass

    journal = site.parent / 'mvb-private/funnel-outbox/download-receipts' / (hashlib.sha256(oid.encode()).hexdigest() + '.json')
    observations = []
    try:
        if journal.stat().st_size <= LIMIT:
            data = json.loads(journal.read_text()).get('events', {})
            for event in data.values() if isinstance(data, dict) else []:
                if event.get('event_type') in EVENTS:
                    observations.append({'type': event['event_type'],
                        'reason': event.get('reason') if event.get('reason') in REASONS else None,
                        'at': timestamp(event.get('occurred_at'))})
    except (OSError, ValueError):
        pass
    return {'status': 'READ_ONLY_SERVER_CORROBORATION', 'python_version': list(sys.version_info[:3]),
        'selection': 'latest created order containing only test1 and total=100; owner identity not inferred',
        'matching_service_orders': len(matches),
        'order_ref_sha256': hashlib.sha256(('nsp-owner-e2e:' + oid).encode()).hexdigest(),
        'order': {'created_at': timestamp(order.get('created_at')),
            'status': order.get('status') if order.get('status') in {'paid', 'pending', 'canceled', 'waiting_for_capture'} else None,
            'amount_kopeks': 100, 'payment_id_present': bool(order.get('payment_id')),
            'paid_at': timestamp(order.get('paid_at')), 'email_sent_at': sent_at,
            'download_reservations': delivery.get('downloads') if isinstance(delivery.get('downloads'), int) else None,
            'last_download_at': timestamp(delivery.get('last_download_at')),
            'archive_present': bool(archive_ok), 'archive_bytes': archive_bytes},
        'source_sha256': hashes,
        'new_download_observer_present': 'function mvb_download_observe(' in download_source,
        'readable_log_files': readable, 'log_tail_bytes_per_file': LIMIT,
        'matching_access_records': access[-50:], 'access_records_truncated': len(access) > 50,
        'nearby_buyer_mail_transport_records': mail_matches,
        'default_outbox_observations': observations,
        'limits': ['No HTTP requests, mail, payment or hosting writes performed.',
            'Two matching orders are not automatically the same owner transaction.',
            'Reservation counters alone do not prove complete archive delivery.',
            'Log search is bounded; absence is not proof of no event.',
            'Mail acceptance is not inbox delivery; owner attestation remains separate.',
            'Default outbox only; a custom PHP environment outbox is not inferred.']}


if __name__ == '__main__':
    try:
        print(json.dumps(inspect(Path(sys.argv[1]), Path.home()), ensure_ascii=False, indent=2))
    except Exception as error:
        frame = traceback.extract_tb(sys.exc_info()[2])[-1]
        print(json.dumps({'status': 'INSPECTION_UNAVAILABLE', 'error_type': type(error).__name__,
            'python_version': list(sys.version_info[:3]), 'function': frame.name, 'line': frame.lineno}))
        raise SystemExit(1)
