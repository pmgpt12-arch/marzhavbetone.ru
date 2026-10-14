#!/usr/bin/env python3
"""Bounded loopback HTTP test of the already accepted P11 delivery overlay.

No production code is changed. No payment provider, SMTP, real customer data,
Office or model is used. The accepted 65-case CLI suite is a dependency, not
re-executed here. read(commit, path) supplies immutable reviewed Git bytes.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
from typing import Callable
from urllib.parse import urlencode, urlsplit
import zipfile

BASE = '8311bb2dc7b497415952d03630e4a477f8bf9d7c'
HEAD = 'e6cf48c0478c359353d469dd27fd65a110f2c8ca'
MERGE = '91767b143ebf4eb35eea79dbda4a7784700b9d56'
CAND = 'tools/candidates/p11-isolated-delivery-binding-20261014/'
PREFIX = 'tools/candidates/portfolio-owner-pdf-20261013/'
ZIP_PATH = PREFIX + 'p11-t6-consolidated-gold-20261014/p11-t6-eight-files-gold-candidate.zip'
TXT_PATH = PREFIX + '19-kvartiry-vmesto-deneg/00-PISMO-POSLE-POKUPKI.txt'
ZIP_SHA = 'f365039ef568dbbe9c661a6e1f553d21ddd0b086c9172f1e5a4340fb7dfe7f70'
TXT_SHA = 'c8f9d78cf2335f2acf52ab8d12258e4e3e799c9c87e3447edcc17c7f0f507ea5'
EDITION = {'kind': 'p11-t6-gold-20261014', 'zip': 'p11-' + ZIP_SHA + '.zip',
           'sha256': ZIP_SHA, 'letter': 'p11-letter-' + TXT_SHA + '.txt',
           'letter_sha256': TXT_SHA}
INPUTS = {
    'products-config.php': (BASE, 'products-config.php', '6874b4bfea06351fecdb4405bb0c9c8a07333e142d69697ab87de1af5bd16b91'),
    'download.php': (BASE, 'download.php', 'bd6380b155ac95ed8e73c7fb2a587a3903e0d85658ce4de3154b74306d7a78f8'),
    'builder': (HEAD, CAND + 'build_candidate.py', 'e71b35efc4c296f1c90c91f41bf5320cc6cf6606f8503dc39b0bdfc9a4a7b800'),
    'helper': (HEAD, CAND + 'binding_helpers.php.txt', 'ec04c9e5d608afab08b8a417f35fec2721a4a7dcba2da8d062f7ec470c71e8a5'),
    'patch': (HEAD, CAND + 'isolated-binding.patch', '8d9ae2c857d3e4de399a2c9f79110fa734f291e58a4321eb54673ee8a1368eb5'),
    'archive': (HEAD, ZIP_PATH, ZIP_SHA),
    'letter': (HEAD, TXT_PATH, TXT_SHA),
}
OUTPUTS = {'products-config.php': 'a6427bddba614efd8adbc5579acd838aaaaffd190bd2b4ba0e4a324d33a447dd',
           'download.php': '2ccd9b2507cfc7e64eeada608825f507b4c780cd898c4cdc799cdce67691c92d'}

CONFIG = """<?php
declare(strict_types=1);
define('ORDERS_DIR', dirname(__DIR__).'/orders');
define('DELIVERY_DIR', ORDERS_DIR.'/delivery');
define('PRODUCTS_DIR', dirname(__DIR__).'/masters');
define('MVB_P11_CANDIDATE_SOURCE_DIR', dirname(__DIR__).'/accepted');
define('MVB_P11_CANDIDATE_BINDING', true);
define('ADMIN_EMAIL', 'support@fixture.invalid');
define('SITE_URL', 'ORIGIN_PLACEHOLDER');
"""
BRIDGE = """<?php
// CLI fixture only; this file is outside the HTTP document root.
require __DIR__.'/web/config.php';
if (function_exists('mail')) throw new RuntimeException('Native mail must be disabled');
if (!function_exists('mail')) {
    function mail($to, $subject, $body, $headers) {
        if (!str_ends_with((string)$to, '@fixture.invalid')) throw new RuntimeException('Non-fixture recipient');
        file_put_contents(__DIR__.'/captured-mail.jsonl', json_encode(['to'=>$to,'subject'=>$subject,'body'=>$body], JSON_UNESCAPED_UNICODE)."\\n", FILE_APPEND);
        return true;
    }
}
require __DIR__.'/web/products-config.php';
$r = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
if (!preg_match('/^order_[0-9_]+_[a-z0-9]+$/i', $r['id'])) throw new RuntimeException('Bad fixture ID');
if (!in_array($r['op'], ['prepare','notify'], true)) throw new RuntimeException('Unknown fixture op');
$file = ORDERS_DIR.'/'.$r['id'].'.json';
$result = mvb_with_order_lock($file, function(array &$o) use ($r) {
    return $r['op'] === 'notify' ? mvb_deliver_and_notify($o) : mvb_prepare_delivery($o);
});
echo json_encode(['result'=>$result, 'order'=>json_decode(file_get_contents($file), true)], JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_http(read: Callable[[str, str], bytes]) -> dict:
    started = time.monotonic()
    result = {'schema_version': 1, 'id': 'P11-ISOLATED-HTTP-TRANSPORT-20261014',
              'status': 'RUNNING', 'scope': 'HTTP_SANDBOX_TRANSPORT_ONLY',
              'accepted_head': HEAD, 'accepted_merge': MERGE,
              'independent_dependency_receipt_sha256': '179ba94660d8c9abf19985b8ca1527545e4f8d53bab4737ebcbc13dab20aaa30',
              'checks': {}, 'http_observations': [], 'inputs': {},
              'limits': {'overall_budget_seconds': 60, 'http_timeout_seconds': 3,
                         'php_cli_timeout_seconds': 5, 'startup_budget_seconds': 3},
              'release': 'HOLD', 'G1_G8_accepted_products': 0,
              'independent_acceptance_of_this_new_test': 'PENDING',
              'real_payments': 0, 'real_mail_sent': 0, 'live_orders_touched': 0,
              'accepted_65_case_suite_repeated': False, 'product_bytes_changed': 0,
              'production_source_nominated': False, 'checkout_marker_assignment_tested': False,
              'real_checkout_or_smtp_tested': False, 'server_process_stopped': False,
              'temporary_directory_removed': False}
    checks = result['checks']
    def check(name: str, condition: bool) -> None:
        checks[name] = 'PASS' if condition else 'FAIL'
        require(condition, name)
    temp = None
    server = None
    log_handle = None
    old_alarm = None
    port = None
    def on_timeout(signum, frame):
        raise TimeoutError('HTTP sandbox budget exceeded')
    try:
        old_alarm = signal.signal(signal.SIGALRM, on_timeout)
        signal.alarm(60)
        data = {}
        for key, (commit, path, expected) in INPUTS.items():
            raw = read(commit, path)
            check('immutable_input_' + key, sha(raw) == expected)
            data[key] = raw
            result['inputs'][key] = {'commit': commit, 'path': path, 'sha256': sha(raw),
                                    'git_blob': git_blob(raw), 'bytes': len(raw)}
        namespace = {'__name__': 'accepted_builder'}
        exec(compile(data['builder'], 'accepted_build_candidate.py', 'exec'), namespace)
        outputs, patch = namespace['build']({k: data[k] for k in OUTPUTS}, data['helper'].decode('utf-8'))
        check('accepted_runtime_output_hashes', {k: sha(v) for k, v in outputs.items()} == OUTPUTS)
        check('accepted_patch_identity', patch.encode() == data['patch'])
        result['runtime_copy_sha256'] = OUTPUTS
        php_meta = subprocess.run(['php', '-r', 'echo json_encode(["version"=>PHP_VERSION,"zip"=>extension_loaded("zip")]);'], capture_output=True, timeout=5, check=True)
        metadata = json.loads(php_meta.stdout)
        result['php'] = metadata
        check('php_zip_preflight', metadata['zip'] is True)
        temp = tempfile.TemporaryDirectory(prefix='p11-http-transport-')
        root = Path(temp.name)
        os.chmod(root, 0o700)
        web = root / 'web'
        orders = root / 'orders'
        delivery = orders / 'delivery'
        accepted = root / 'accepted'
        masters = root / 'masters'
        for directory in (web, delivery, accepted, masters):
            directory.mkdir(parents=True, exist_ok=True)
        for name, content in outputs.items():
            (web / name).write_bytes(content)
        (accepted / 'accepted.zip').write_bytes(data['archive'])
        (accepted / 'accepted-letter.txt').write_bytes(data['letter'])
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        origin = 'http://127.0.0.1:' + str(port)
        (web / 'config.php').write_text(CONFIG.replace('ORIGIN_PLACEHOLDER', origin))
        (root / 'bridge.php').write_text(BRIDGE)
        php = ['php', '-d', 'disable_functions=mail,exec,shell_exec,system,passthru,popen,proc_open,curl_exec',
               '-d', 'allow_url_fopen=0', '-d', 'display_errors=stderr',
               '-d', 'open_basedir=' + str(root), '-d', 'sys_temp_dir=' + str(root)]
        env = {k: v for k, v in os.environ.items() if k not in ('PHPRC', 'PHP_INI_SCAN_DIR', 'PHP_CLI_SERVER_WORKERS')}
        log_handle = (root / 'http-server.log').open('w+b')
        server = subprocess.Popen(php + ['-S', '127.0.0.1:' + str(port), '-t', str(web)],
                                  cwd=root, env=env, stdout=log_handle, stderr=log_handle)
        deadline = time.monotonic() + 3
        ready = False
        # Readiness polling of one existing child; no process restart or task retry.
        while time.monotonic() < deadline:
            require(server.poll() is None, 'HTTP server exited at startup')
            with socket.socket() as probe:
                probe.settimeout(0.15)
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    ready = True
                    break
            time.sleep(0.05)
        check('loopback_listener_ready', ready)
        result['listener'] = {'host': '127.0.0.1', 'port': port, 'pid': server.pid,
                              'document_root_contains_only_runtime_copies': True,
                              'order_and_archive_directories_outside_webroot': True}
        def store(order):
            (orders / (order['id'] + '.json')).write_text(json.dumps(order, ensure_ascii=False))
        def saved(order):
            return json.loads((orders / (order['id'] + '.json')).read_text())
        def make_order(number, sku='p11', marked=False):
            position = {'sku': sku}
            if marked:
                position['edition'] = copy.deepcopy(EDITION)
            return {'id': f'order_20261014_{number}_{sku}', 'status': 'paid',
                    'email': 'buyer@fixture.invalid', 'items': [position]}
        def call(order, op='prepare'):
            response = subprocess.run(php + [str(root / 'bridge.php')],
                                      input=json.dumps({'id': order['id'], 'op': op}).encode(),
                                      capture_output=True, timeout=5, env=env, cwd=root)
            require(response.returncode == 0 and not response.stderr,
                    'CLI preparation failed: ' + response.stderr.decode(errors='replace'))
            return json.loads(response.stdout)
        def request(label, order=None, sku='p11', override=None, path=None):
            before = saved(order)['delivery']['downloads'] if order else None
            if path is None:
                query = {'o': order['id'], 't': order['delivery']['token'], 'f': sku}
                query.update(override or {})
                path = '/download.php?' + urlencode(query)
            require(path.startswith('/') and not path.startswith('//'), 'HTTP target must be local path')
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                connection.request('GET', path)
                response = connection.getresponse()
                body = response.read(2 * 1024 * 1024)
                status = response.status
                headers = {k.lower(): v for k, v in response.getheaders()}
            finally:
                connection.close()
            after = saved(order)['delivery']['downloads'] if order else None
            result['http_observations'].append({'case': label, 'method': 'GET',
                'request_path_without_query': path.split('?')[0], 'query_sha256': sha(path.encode()),
                'fixture_order_id': order['id'] if order else None,
                'status': status, 'headers': headers, 'body_bytes': len(body), 'body_sha256': sha(body),
                'downloads_before': before, 'downloads_after': after})
            return status, headers, body, before, after

        current = make_order(100, marked=True)
        store(current)
        prepared = call(current, 'notify')
        current = prepared['order']
        check('paid_fixture_persisted_with_edition', current['delivery']['editions']['p11'] == EDITION)
        mails = [json.loads(line) for line in (root / 'captured-mail.jsonl').read_text().splitlines()]
        body = mails[0]['body']
        link = prepared['result'][0]['url']
        parsed = urlsplit(link)
        check('issued_link_targets_actual_loopback_handler', parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and parsed.port == port and parsed.path == '/download.php')
        check('single_captured_email_contains_accepted_txt', len(mails) == 1 and data['letter'].decode() in body)
        result['captured_mail'] = {'count': len(mails), 'body_sha256': sha(body.encode()),
                                   'accepted_letter_sha256': TXT_SHA, 'external_send': False}
        s, h, b, before, after = request('new_p11_download_from_issued_link', current,
                                      path=parsed.path + '?' + parsed.query)
        check('http_new_p11_200_exact_accepted_zip', s == 200 and b == data['archive'])
        check('http_zip_headers', h.get('content-type') == 'application/zip' and
              h.get('content-length') == str(len(data['archive'])) and
              h.get('content-disposition') == 'attachment; filename="13-raschet-metrami.zip"' and
              h.get('x-content-type-options') == 'nosniff')
        check('http_download_persisted_counter_once', before == 0 and after == 1)
        post_get = saved(current)
        notified = call(post_get, 'notify')
        check('callback_after_http_preserves_saved_order_and_mail_count', notified['order'] == post_get and len((root / 'captured-mail.jsonl').read_text().splitlines()) == 1)
        s, h, b, before, after = request('second_valid_download', post_get)
        check('second_http_download_exact_bytes_and_counter', s == 200 and b == data['archive'] and before == 1 and after == 2)
        for label, override, expected in [('wrong_token', {'t': 'badtoken'}, 403), ('unowned_sku', {'f': 't6'}, 404)]:
            s, h, b, before, after = request(label, current, override=override)
            check('http_' + label + '_no_counter_charge', s == expected and after == before and b != data['archive'])
        for number, label, edit, expected in [
            (101, 'unpaid', lambda o: o.update(status='pending'), 403),
            (102, 'expired', lambda o: o['delivery'].update(expires_at='2000-01-01T00:00:00Z'), 410),
            (103, 'quota', lambda o: o['delivery'].update(downloads=30), 429),
            (104, 'missing_edition_metadata', lambda o: o['delivery'].update(editions={}), 500),
        ]:
            clone = copy.deepcopy(current)
            clone['id'] = f'order_20261014_{number}_p11'
            edit(clone)
            store(clone)
            s, h, b, before, after = request(label, clone)
            check('http_' + label + '_no_counter_charge', s == expected and before == after and b != data['archive'])
        snapshot = delivery / EDITION['zip']
        for label in ('corrupt_snapshot', 'missing_snapshot'):
            if label == 'corrupt_snapshot':
                snapshot.write_bytes(data['archive'] + b'!')
            else:
                snapshot.unlink()
            s, h, b, before, after = request(label, current)
            check('http_' + label + '_no_rebuild_or_charge', s == 500 and before == after and
                  (snapshot.read_bytes() == data['archive'] + b'!' if snapshot.exists() else label == 'missing_snapshot'))
            snapshot.write_bytes(data['archive'])
        for idx, sku, directory, zipname in [(200, 'p11', '13-raschet-metrami', '13-raschet-metrami.zip'),
                                           (300, 't6', '19-kvartiry-vmesto-deneg', '19-kvartiry-vmesto-deneg.zip')]:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                info = zipfile.ZipInfo('legacy-' + sku + '.txt', (2026, 1, 1, 0, 0, 0))
                archive.writestr(info, ('Original fixture ' + sku).encode())
            old_bytes = buffer.getvalue()
            cache = delivery / zipname
            cache.write_bytes(old_bytes)
            master = masters / directory
            master.mkdir()
            (master / 'new.txt').write_text('Must never replace prior purchase')
            os.utime(master / 'new.txt', (2100000000, 2100000000))
            old = make_order(idx, sku)
            old['delivery'] = {'token': 'legacytoken' + sku, 'created_at': '2026-01-01T00:00:00Z',
                               'expires_at': '2099-01-01T00:00:00Z', 'downloads': 2,
                               'items': {sku: zipname}, 'editions': [], 'email_sent_at': '2026-01-01T00:00:00Z'}
            store(old)
            s, h, b, before, after = request('legacy_' + sku + '_before_new_order', old, sku)
            check('http_legacy_' + sku + '_original_before', s == 200 and b == old_bytes and before == 2 and after == 3)
            old_state = saved(old)
            unmarked = make_order(idx + 1, sku)
            store(unmarked)
            new_result = call(unmarked)
            check('unmarked_' + sku + '_preserves_legacy_file_and_order',
                  not new_result['result']['missing'] and cache.read_bytes() == old_bytes and saved(old) == old_state)
            s, h, b, before, after = request('legacy_' + sku + '_after_new_order', old, sku)
            check('http_legacy_' + sku + '_original_after', s == 200 and b == old_bytes and before == 3 and after == 4 and saved(old)['delivery']['token'] == old['delivery']['token'])
            cache.unlink()
            s, h, b, before, after = request('legacy_' + sku + '_missing', old, sku)
            check('http_legacy_' + sku + '_missing_not_rebuilt', s == 500 and before == after and not cache.exists())
            cache.write_bytes(old_bytes)
        s, h, b, _, _ = request('fixture_orders_not_in_document_root', path='/orders/' + current['id'] + '.json')
        check('fixture_private_order_not_http_exposed', s == 404 and current['delivery']['token'].encode() not in b)
        check('accepted_inputs_remain_unchanged', all(sha(data[key]) == entry[2] for key, entry in INPUTS.items()) and
              (accepted / 'accepted.zip').read_bytes() == data['archive'] and
              (accepted / 'accepted-letter.txt').read_bytes() == data['letter'])
        check('runtime_copies_not_changed_by_http_test', {name: sha((web / name).read_bytes()) for name in OUTPUTS} == OUTPUTS)
        check('no_additional_mail', len((root / 'captured-mail.jsonl').read_text().splitlines()) == 1)
        log_handle.flush()
        log_handle.seek(0)
        log = log_handle.read().decode(errors='replace')
        result['http_server_log_sha256'] = sha(log.encode())
        result['http_server_log'] = log.replace(str(root), '<sandbox>')
        check('no_php_fatal_warning_or_notice', not any(token in log for token in ('PHP Fatal', 'PHP Warning', 'PHP Notice', 'Parse error')))
        result['status'] = 'PASS_AUTHOR_HTTP_SANDBOX_TRANSPORT_ONLY'
    except Exception as error:
        result['status'] = 'FAIL_HTTP_SANDBOX_TRANSPORT'
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
        if log_handle:
            log_handle.flush()
            log_handle.seek(0)
            result['http_server_log'] = log_handle.read().decode(errors='replace')
    finally:
        signal.alarm(0)
        if old_alarm is not None:
            signal.signal(signal.SIGALRM, old_alarm)
        if server:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=2)
            result['server_process_stopped'] = server.poll() is not None
        if log_handle:
            log_handle.close()
        if temp:
            temp_name = temp.name
            temp.cleanup()
            result['temporary_directory_removed'] = not Path(temp_name).exists()
        if server:
            checks['cleanup_server_stopped'] = 'PASS' if result['server_process_stopped'] else 'FAIL'
        if temp:
            checks['cleanup_directory_removed'] = 'PASS' if result['temporary_directory_removed'] else 'FAIL'
        if any(value != 'PASS' for value in checks.values()):
            result['status'] = 'FAIL_HTTP_SANDBOX_TRANSPORT'
        result['checks_passed'] = sum(value == 'PASS' for value in checks.values())
        result['checks_total'] = len(checks)
        result['http_requests'] = len(result['http_observations'])
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    def read(commit: str, path: str) -> bytes:
        return subprocess.check_output(['git', '-C', str(args.repo), 'show', commit + ':' + path], timeout=8)
    result = verify_http(read)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: result.get(key) for key in ('status', 'checks_passed', 'checks_total', 'http_requests', 'error', 'server_process_stopped', 'temporary_directory_removed')}, ensure_ascii=False))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
