#!/usr/bin/env python3
"""Isolated checkout -> real webhook -> download, frozen P1 buyer files only.

Writes only a newly created scratch tree. Never reads production config/orders.
The prior edition is a marked synthetic fixture, not a historical buyer archive.
"""
import argparse
import hashlib
import io
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree as ET

RUNTIME = ['payment.php', 'products-config.php', 'webhook.php', 'download.php']
EXCLUDE = {'.htaccess', '00-PISMO-POSLE-POKUPKI.txt', 'MANIFEST.md'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_map(path):
    result = {}
    for file in sorted(path.rglob('*')):
        if file.is_symlink():
            raise AssertionError('no symlink sources permitted')
        if file.is_file() and file.name not in EXCLUDE:
            result[file.relative_to(path).as_posix()] = sha(file.read_bytes())
    return result


def zip_map(data):
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        names = [n for n in package.namelist() if not n.endswith('/')]
        assert len(names) == len(set(names)), 'duplicate ZIP entries'
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
        return {n: sha(package.read(n)) for n in sorted(names)}


def request(port, path, body=None):
    url = 'http://127.0.0.1:' + str(port) + path
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as response:
        return response.code, response.read()


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', required=True, type=Path)
    parser.add_argument('--head', required=True)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--buyer-dir', required=True, type=Path)
    parser.add_argument('--receipt-root', required=True, type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    expected = json.loads(args.manifest.read_text())
    assert expected['site_content_head'] == args.head
    assert len(args.head) == 40 and all(c in '0123456789abcdef' for c in args.head)
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.head, 'HEAD'], cwd=site, check=True)
    runtime_bytes = {name: (site / name).read_bytes() for name in RUNTIME}
    for name, data in runtime_bytes.items():
        frozen = subprocess.check_output(['git', 'show', args.head + ':' + name], cwd=site)
        assert data == frozen, 'runtime changed after content freeze: ' + name
    original = source_map(args.buyer_dir)
    expected_files = {f['file']: f['raw_hash'].removeprefix('sha256:') for f in expected['files']}
    assert len(original) == 19 and original == expected_files, 'frozen 19-source manifest mismatch'
    frozen_zip = Path(expected['zip_path']).read_bytes()
    assert sha(frozen_zip) == expected['edition']['sha256']
    assert zip_map(frozen_zip) == original, 'frozen ZIP differs from actual 19 sources'
    assert args.receipt_root.resolve() != site and site not in args.receipt_root.resolve().parents
    args.receipt_root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='p1-actual-integration-', dir=args.receipt_root))
    web, orders, masters = scratch / 'web', scratch / 'orders', scratch / 'masters'
    for directory in [web, orders / 'delivery', masters / '01-zakrytie-rabot']:
        directory.mkdir(parents=True)
    source = masters / '01-zakrytie-rabot'
    for name in original:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((args.buyer_dir / name).read_bytes())
    for name, data in runtime_bytes.items():
        (web / name).write_bytes(data)
    # The OLD fixture has the same 19 names and one explicitly synthetic DOCX mark.
    mark_file = source / '01-ks-2.docx'
    current_docx = mark_file.read_bytes()
    with zipfile.ZipFile(io.BytesIO(current_docx)) as inp, zipfile.ZipFile(mark_file, 'w') as out:
        doc = ET.fromstring(inp.read('word/document.xml'))
        slot = next(t for t in doc.iter() if t.tag.endswith('}t') and t.text)
        slot.text += ' [СИНТЕТИЧЕСКИЙ ТЕСТ ПРЕЖНЕГО ИЗДАНИЯ]'
        for item in inp.infolist():
            out.writestr(item, ET.tostring(doc, encoding='utf-8', xml_declaration=True)
                         if item.filename == 'word/document.xml' else inp.read(item))
    prior_map = source_map(source)
    assert set(prior_map) == set(original) and sum(prior_map[n] != original[n] for n in original) == 1
    state, api_audits = {}, []

    class MockApi(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def reply(self, value):
            data = json.dumps(value).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            assert self.path == '/payments'
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            order_id = payload['metadata']['order_id']
            order = json.loads((orders / (order_id + '.json')).read_text())
            edition = order['items'][0]['edition']
            pinned = orders / 'delivery' / edition['zip']
            ok = (order['status'] == 'pending' and len(order['items']) == 1
                  and order['items'][0]['sku'] == 'p1' and order['total'] == 249000
                  and order['items'][0]['price'] == 249000
                  and payload['amount'] == {'value': '2490.00', 'currency': 'RUB'}
                  and edition['zip'] == 'p1-' + edition['sha256'] + '.zip'
                  and pinned.is_file() and sha(pinned.read_bytes()) == edition['sha256'])
            assert ok, 'pending pin/price absent before API request'
            api_audits.append({'pin_present_before_api': ok, 'sku': 'p1', 'price_kopeks': 249000})
            payment_id = 'mock_' + order_id
            state[payment_id] = {'id': payment_id, 'status': 'succeeded',
                                 'metadata': {'order_id': order_id}}
            self.reply({'id': payment_id, 'status': 'pending', 'confirmation': {
                'confirmation_url': 'https://example.invalid/synthetic-no-checkout'}})

        def do_GET(self):
            assert self.path.startswith('/payments/')
            self.reply(state[self.path.removeprefix('/payments/')])

    mock = ThreadingHTTPServer(('127.0.0.1', 0), MockApi)
    thread = threading.Thread(target=mock.serve_forever, daemon=True)
    thread.start()
    site_port = port()
    config = {'ORDERS_DIR': str(orders), 'PRODUCTS_DIR': str(masters),
              'SITE_URL': 'http://127.0.0.1:' + str(site_port), 'ADMIN_EMAIL': 'nobody@example.invalid',
              'YOOKASSA_SHOP_ID': 'synthetic', 'YOOKASSA_SECRET_KEY': 'synthetic',
              'YOOKASSA_MODE': 'test', 'YOOKASSA_API_URL': 'http://127.0.0.1:' + str(mock.server_port)}
    (web / 'config.php').write_text('<?php\n' + '\n'.join(
        'define(' + json.dumps(k) + ',' + json.dumps(v) + ');' for k, v in config.items()))
    logfile = (scratch / 'php-server.log').open('wb')
    proc = subprocess.Popen(['php', '-d', 'sendmail_path=/bin/false', '-S',
                             '127.0.0.1:' + str(site_port), '-t', str(web)], stdout=logfile, stderr=logfile)
    receipt = {'status': 'RUNNING', 'scope': 'isolated actual frozen 19 P1 files only',
               'content_head': args.head, 'scratch': str(scratch),
               'head_observed_start': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=site).decode().strip(),
               'runtime_sha256': {n: sha(b) for n, b in runtime_bytes.items()},
               'frozen_edition': expected['edition'], 'new_source_sha256': original,
               'synthetic_prior_source_sha256': prior_map, 'checks': [],
               'production_inventory': 'BLOCKED: production access/path/orders inventory and authoritative historical ZIP remain unverified; synthetic OLD is not a historical archive',
               'network': 'loopback mock API/HTTP only; example.invalid confirmation URL not visited',
               'mail': 'PHP sendmail_path=/bin/false; buyer email empty; no email sent'}

    def check(name, condition):
        assert condition, name
        receipt['checks'].append({'name': name, 'pass': True})

    def checkout():
        code, body = request(site_port, '/payment.php', {'items': [{'sku': 'p1', 'price': 1,
            'edition': {'zip': 'forged.zip', 'sha256': '0' * 64}}], 'phone': 'synthetic test only'})
        assert code == 200, (code, body[:300])
        data = json.loads(body)
        assert data['ok']
        return json.loads((orders / (data['order_id'] + '.json')).read_text())

    def reload(order):
        return json.loads((orders / (order['id'] + '.json')).read_text())

    def callback(order):
        code, body = request(site_port, '/webhook.php', {'event': 'payment.succeeded', 'object': {
            'id': order['payment_id'], 'status': 'canceled', 'metadata': {'order_id': 'forged'},
            'edition': {'zip': 'forged.zip', 'sha256': '0' * 64}}})
        assert code == 200 and json.loads(body)['ok'], (code, body[:300])
        paid = reload(order)
        assert paid['status'] == 'paid' and list(paid['delivery']['items']) == ['p1']
        return paid

    def download(order):
        return request(site_port, '/download.php?o=' + order['id'] + '&t=' + order['delivery']['token'] + '&f=p1')

    try:
        for _ in range(40):
            try:
                with socket.create_connection(('127.0.0.1', site_port), timeout=.1):
                    break
            except OSError:
                time.sleep(.05)
        old = checkout()
        check('synthetic prior checkout pins actual 19-file content before payment API; forged edition/price ignored',
              zip_map((orders / 'delivery' / old['items'][0]['edition']['zip']).read_bytes()) == prior_map)
        # Publish only inside this scratch fixture; actual source files stay read-only.
        mark_file.write_bytes(current_docx)
        new = checkout()
        check('new checkout pins frozen release ZIP exactly at P1 249000 kopeks',
              new['items'][0]['edition'] == expected['edition'] and len(api_audits) == 2)
        old, new = callback(old), callback(new)
        check('real webhook uses authoritative local API and keeps prior/new pins after source change',
              old['delivery']['editions']['p1'] == old['items'][0]['edition']
              and new['delivery']['editions']['p1'] == expected['edition']
              and old['delivery']['items']['p1'] != new['delivery']['items']['p1'])
        for label, order, file_map in [('old', old, prior_map), ('new', new, original)]:
            code, data = download(order)
            check(label + ' actual HTTP ZIP has exactly its 19 source SHA256 entries',
                  code == 200 and sha(data) == order['items'][0]['edition']['sha256'] and zip_map(data) == file_map)
            (scratch / (label + '-download.zip')).write_bytes(data)
            if label == 'new':
                check('new HTTP response bytes equal frozen root runtime ZIP', data == frozen_zip)
        before = reload(old)['delivery']
        replay = callback(old)['delivery']
        check('callback replay preserves issued token/edition/expiry/download count',
              all(replay.get(k) == before.get(k) for k in ['token', 'items', 'editions', 'created_at', 'expires_at', 'downloads']))
        prior_path = orders / 'delivery' / old['items'][0]['edition']['zip']
        preserved = prior_path.read_bytes()
        prior_path.unlink()
        code, _ = download(old)
        check('missing pinned edition denies without rebuilding from new sources or consuming download',
              code == 500 and not prior_path.exists() and reload(old)['delivery']['downloads'] == before['downloads'])
        prior_path.write_bytes(b'SYNTHETIC CORRUPT PINNED SNAPSHOT')
        code, _ = download(old)
        check('corrupt pinned edition denies without consuming download',
              code == 500 and reload(old)['delivery']['downloads'] == before['downloads'])
        prior_path.write_bytes(preserved)
        check('all original 19 sources and runtime files remained unchanged',
              source_map(args.buyer_dir) == original and all((site / n).read_bytes() == b for n, b in runtime_bytes.items()))
        receipt.update(status='PASS', api_audits=api_audits,
                       synthetic_prior_edition=old['items'][0]['edition'],
                       actual_new_edition=new['items'][0]['edition'],
                       head_observed_end=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=site).decode().strip())
    except BaseException as error:
        receipt.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        proc.terminate()
        proc.wait(timeout=3)
        logfile.close()
        mock.shutdown()
        mock.server_close()
        data = json.dumps(receipt, ensure_ascii=False, indent=2).encode()
        (scratch / 'receipt.json').write_bytes(data)
        print(json.dumps({'status': receipt['status'], 'checks': len(receipt['checks']),
                          'receipt': str(scratch / 'receipt.json'), 'receipt_sha256': sha(data)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
