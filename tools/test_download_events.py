#!/usr/bin/env python3
"""Real isolated PHP GETs, synthetic orders/ZIPs; no payment or mail endpoints."""
import concurrent.futures
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PHP = os.environ.get('ROUTE_PHP') or shutil.which('php')
TOKEN = 'synthetic-private-download-token-DO-NOT-LOG'
PII = ['buyer-private@example.invalid', '+79991234567', 'Synthetic Private Buyer']
ARCHIVE_CONTENT = b'SYNTHETIC PRIVATE ARCHIVE CONTENT - DO NOT LOG'


class DownloadEvents(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PHP, 'PHP is required, never silently skip acceptance')
        self.temp = tempfile.TemporaryDirectory(prefix='nsp-download-observation-')
        self.base = Path(self.temp.name)
        self.web, self.orders, self.outbox = [self.base / x for x in ('web', 'orders', 'outbox')]
        self.delivery = self.orders / 'delivery'
        for p in (self.web, self.delivery, self.outbox):
            p.mkdir(parents=True)
        for name in ('download.php', 'products-config.php', 'mvb_funnel.php'):
            shutil.copy2(ROOT / name, self.web / name)
        self.archive = self.delivery / 'synthetic.zip'
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('synthetic.txt', ARCHIVE_CONTENT)
        self.zip_bytes = self.archive.read_bytes()
        self.order_id = 'order_20261023_070000_synthetic'
        self.order_file = self.orders / (self.order_id + '.json')
        self.order = {'id': self.order_id, 'status': 'paid', 'email': PII[0],
                      'phone': PII[1], 'name': PII[2], 'items': [{'sku': 'p3'}],
                      'delivery': {'token': TOKEN, 'expires_at': (dt.datetime.now(dt.timezone.utc)
                                   + dt.timedelta(hours=1)).isoformat(),
                                   'downloads': 0, 'items': {'p3': 'synthetic.zip'}}}
        self.save_order()
        self.process = None

    def tearDown(self):
        if self.process is not None:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=5)
            self.log.close()
        self.temp.cleanup()

    def save_order(self):
        self.order_file.write_text(json.dumps(self.order))

    def start(self, fault_read=False, library=True):
        if not library:
            (self.web / 'mvb_funnel.php').unlink()
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        config = {'ORDERS_DIR': str(self.orders), 'PRODUCTS_DIR': str(self.base / 'empty-masters'),
                  'ADMIN_EMAIL': 'admin@example.invalid', 'SITE_URL': 'http://127.0.0.1:%d' % self.port}
        # A stream that passes stat() but fails the REAL builtin readfile().
        # This is only in the isolated config, never a runtime fault hook.
        extra = '''class ReadFault { public function url_stat($p,$f) { return ['mode'=>0100644,'size'=>8]; }
          public function stream_open($p,$m,$o,&$opened) { return false; } }
          stream_wrapper_register('readfault','ReadFault');
          define('DELIVERY_DIR','readfault://delivery');''' if fault_read else ''
        (self.web / 'config.php').write_text('<?php\n' + '\n'.join(
            'define(%s,%s);' % (json.dumps(k), json.dumps(v)) for k, v in config.items()) + '\n' + extra)
        env = dict(os.environ, MVB_FUNNEL_OUTBOX=str(self.outbox), PHP_CLI_SERVER_WORKERS='4')
        self.log = (self.base / 'php.log').open('wb')
        self.process = subprocess.Popen([PHP, '-d', 'sendmail_path=/bin/false', '-d', 'display_errors=0',
                                         '-S', '127.0.0.1:%d' % self.port, '-t', str(self.web)],
                                        env=env, stdout=self.log, stderr=self.log, start_new_session=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.assertIsNone(self.process.poll(), 'isolated PHP server exited')
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=.1):
                    return
            except OSError:
                time.sleep(.025)
        self.fail('isolated PHP start exceeded 5 seconds')

    def get(self, token=TOKEN, sku='p3', method='GET'):
        url = 'http://127.0.0.1:%d/download.php?o=%s&t=%s&f=%s' % (self.port, self.order_id, token, sku)
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                try:
                    return response.status, response.read(), False
                except http.client.IncompleteRead as exc:
                    return response.status, exc.partial, True
        except urllib.error.HTTPError as response:
            return response.code, response.read(), False

    def observations(self, expected=2):
        # The observer runs AFTER the response. Wait for its actual durable
        # receipt, not merely for an HTTP command's exit code.
        deadline = time.monotonic() + 3
        values = []
        while time.monotonic() < deadline:
            values = []
            for p in (self.outbox / 'download-receipts').glob('*.json'):
                events = json.loads(p.read_text()).get('events', {})
                if isinstance(events, dict):
                    values.extend(events.values())
                else:
                    self.assertEqual(events, [], 'malformed receipt event map')
            if len(values) >= expected:
                break
            time.sleep(.01)
        return values

    def test_initial_receipt_is_not_a_completed_observation(self):
        p = self.outbox / 'download-receipts' / 'initial.json'
        p.parent.mkdir()
        for initial in ({}, []):
            p.write_text(json.dumps({'events': initial}))
            self.assertEqual(self.observations(expected=0), [])

    def queue(self):
        return [json.loads(line) for p in self.outbox.glob('*.pending.jsonl') if p.is_file()
                for line in p.read_text().splitlines() if line]

    def assert_private(self, observations):
        serialized = json.dumps(observations + self.queue())
        for value in [TOKEN, self.order_id, *PII, ARCHIVE_CONTENT.decode()]:
            self.assertNotIn(value, serialized)
        for event in observations:
            self.assertEqual(set(event) - {'queued'}, {'event_type', 'event_uuid', 'occurred_at', 'sku', 'status', 'reason'})
            self.assertIn(event['sku'], ('p3', None))

    def assert_failed(self, status, reason):
        self.assertEqual(self.get()[0], status)
        self.assertEqual(self.get()[0], status)
        observed = self.observations()
        self.assertEqual(len(observed), 2)
        self.assertEqual({e['event_type'] for e in observed}, {'download.link_opened', 'download.failed'})
        error = next(e for e in observed if e['event_type'] == 'download.failed')
        self.assertEqual((error['status'], error['reason']), (status, reason))
        self.assertEqual(self.queue(), [])
        self.assert_private(observed)

    def test_valid_and_repeat_preserve_bytes_and_count_once(self):
        self.start()
        for _ in range(3):
            self.assertEqual(self.get(), (200, self.zip_bytes, False))
        observed = self.observations()
        self.assertEqual(len(observed), 2)
        self.assertEqual({e['event_type'] for e in observed}, {'download.link_opened', 'download.file_served'})
        self.assertEqual(len(self.queue()), 1)
        self.assertEqual(self.queue()[0]['event_type'], 'funnel.product_delivered')
        self.assertEqual(json.loads(self.order_file.read_text())['delivery']['downloads'], 3)
        self.assertEqual(self.archive.read_bytes(), self.zip_bytes)
        self.assert_private(observed)

    def test_expired_link(self):
        self.order['delivery']['expires_at'] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat()
        self.save_order()
        self.start()
        self.assert_failed(410, 'expired')
        self.assertEqual(json.loads(self.order_file.read_text())['delivery']['downloads'], 0)

    def test_wrong_token_then_legal_retry(self):
        self.start()
        for _ in range(2):
            self.assertEqual(self.get(token='invalid-token')[0], 403)
        observed = self.observations()
        self.assertEqual(len(observed), 2)
        self.assertEqual(self.queue(), [])
        self.assertEqual(self.get(), (200, self.zip_bytes, False))
        observed = self.observations(3)
        self.assertEqual(len(observed), 3)
        self.assertEqual(len(self.queue()), 1)
        self.assertEqual(sum(e['event_type'] == 'download.link_opened' for e in observed), 1)
        self.assert_private(observed)

    def test_missing_file_rolls_back_reservation(self):
        self.archive.unlink()
        self.start()
        self.assert_failed(500, 'file_unavailable')
        self.assertEqual(json.loads(self.order_file.read_text())['delivery']['downloads'], 0)

    def test_server_error_does_not_rewrite_unreadable_order(self):
        self.order_file.write_text('{')
        self.start()
        self.assert_failed(503, 'server_error')
        self.assertEqual(self.order_file.read_text(), '{')

    def test_head_is_not_a_delivery_event(self):
        self.start()
        self.assertEqual(self.get(method='HEAD'), (200, b'', False))
        # A second request to the single endpoint synchronises finished
        # shutdown callbacks without introducing another runtime endpoint.
        self.assertEqual(self.get(method='HEAD')[0], 200)
        self.assertEqual(self.observations(expected=0), [])
        self.assertEqual(self.queue(), [])

    def test_parallel_downloads_count_once_and_keep_limit_counter(self):
        self.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.get(), range(12)))
        self.assertTrue(all(r == (200, self.zip_bytes, False) for r in results))
        self.assertEqual(len(self.observations()), 2)
        self.assertEqual(len(self.queue()), 1)
        self.assertEqual(json.loads(self.order_file.read_text())['delivery']['downloads'], 12)

    def test_queue_failure_never_breaks_download_and_retry_recovers(self):
        blocked = self.outbox / (dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d') + '.pending.jsonl')
        blocked.mkdir()
        self.start()
        self.assertEqual(self.get(), (200, self.zip_bytes, False))
        observed = self.observations()
        served = next(e for e in observed if e['event_type'] == 'download.file_served')
        self.assertFalse(served['queued'])
        self.assertEqual(self.queue(), [])
        blocked.rmdir()
        self.assertEqual(self.get(), (200, self.zip_bytes, False))
        deadline = time.monotonic() + 3
        while not self.queue() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(len(self.queue()), 1)
        self.assertEqual(self.queue()[0]['event_uuid'], served['event_uuid'])
        self.assertEqual(self.get(), (200, self.zip_bytes, False))
        self.assertEqual(len(self.observations()), 2)
        self.assertEqual(len(self.queue()), 1)

    def test_missing_analytics_library_keeps_download_available(self):
        self.start(library=False)
        self.assertEqual(self.get(), (200, self.zip_bytes, False))
        self.assertEqual(self.get(), (200, self.zip_bytes, False))
        self.assertEqual(self.queue(), [])

    def test_actual_readfile_failure_never_claims_delivery(self):
        self.start(fault_read=True)
        status, data, incomplete = self.get()
        self.assertEqual(status, 200)  # Original headers precede readfile().
        self.assertNotEqual(data, self.zip_bytes)
        observed = self.observations()
        self.assertEqual({e['event_type'] for e in observed}, {'download.link_opened', 'download.failed'})
        self.assertEqual(next(e['reason'] for e in observed if e['event_type'] == 'download.failed'), 'read_failed')
        self.assertEqual(self.queue(), [])

    def test_untrusted_sku_cannot_enter_analytics(self):
        self.start()
        self.assertEqual(self.get(sku='private-buyer@example.invalid')[0], 404)
        observed = self.observations()
        self.assertTrue(all(e['sku'] is None for e in observed))
        self.assertNotIn('private-buyer', json.dumps(observed))
        self.assertEqual(self.queue(), [])

    def test_receipt_write_failure_replays_same_identity_not_a_new_event(self):
        # Fault only the isolated receipt writer after append. The commercial
        # order writer and the checked-out endpoint remain unchanged.
        p = self.web / 'products-config.php'
        text = p.read_text()
        signature = 'function mvb_write_order(string $orderFile, array $order, bool $резерв = true): bool\n{'
        self.assertEqual(text.count(signature), 1)
        text = text.replace(signature, signature + '\n    if (strpos($orderFile, "download-receipts") !== false && is_file($orderFile)) return false;', 1)
        p.write_text(text)
        self.start()
        for _ in range(2):
            self.assertEqual(self.get(), (200, self.zip_bytes, False))
        deadline = time.monotonic() + 3
        while len(self.queue()) < 2 and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(len(self.queue()), 2)
        self.assertEqual(len({e['event_uuid'] for e in self.queue()}), 1)
        self.assert_private([])


if __name__ == '__main__':
    unittest.main(verbosity=2)
