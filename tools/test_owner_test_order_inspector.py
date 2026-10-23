"""Privacy, correlation, and zero-write contract on an isolated hosting fixture."""
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from tools.inspect_owner_test_order import inspect, orders_path


class OwnerOrderInspector(unittest.TestCase):
    def test_manual_dispatch_uses_existing_entrypoint_and_keeps_other_jobs_off(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / '.github/workflows/deploy.yml').read_text()
        self.assertFalse((root / '.github/workflows/nsp-hosting-readonly.yml').exists(),
                         'new workflow paths may be unregistered; use the existing entrypoint')
        self.assertRegex(workflow, r'inspect_owner_test_order:\n\s+description:.*\n\s+type: boolean\n\s+default: false')
        jobs = re.findall(r'^  ([\w-]+):\n    if: (.+)', workflow, re.M)
        self.assertTrue(jobs)
        for name, condition in jobs:
            if name == 'inspect-owner-test-order':
                self.assertIn("github.ref_name == 'fix/nsp-customer-route-20261022' && inputs.inspect_owner_test_order == true", condition)
                self.assertNotIn('||', condition)
            elif name == 'deploy':
                self.assertIn("github.ref_name == 'main' &&", condition)
            elif name == 'deploy-remaining-only':
                self.assertIn('inputs.remaining_only == true', condition)
                self.assertIn("github.event_name == 'push'", condition)
            else:
                self.assertRegex(condition, r'inputs\.(?!inspect_owner_test_order)\w+ == true')
                self.assertNotIn('||', condition)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.site = self.home / 'www/nastoronepodryadchika.ru'
        self.orders = self.site / 'orders'
        self.orders.mkdir(parents=True)
        (self.orders / 'delivery').mkdir()
        (self.site / 'config.php').write_text("<?php\ndefine('ORDERS_DIR', __DIR__ . '/orders');\ndefine('KEY','PRIVATE_LIVE_SECRET');")
        for name in ['index.html', 'app.js', 'lead.php', 'payment.php', 'webhook.php', 'products-config.php', 'download.php']:
            (self.site / name).write_text('synthetic source')
        self.oid = 'order_20261023_010000_private'
        self.order = {'id': self.oid, 'created_at': '2026-10-23T01:00:00+00:00',
            'status': 'paid', 'total': 100, 'payment_id': 'PRIVATE_PAYMENT_ID',
            'paid_at': '2026-10-23T01:01:00+00:00', 'email': 'private-buyer@example.invalid',
            'phone': '+79991234567', 'items': [{'sku': 'test1'}],
            'delivery': {'token': 'PRIVATE_DOWNLOAD_TOKEN', 'email_sent_at': '2026-10-23T01:01:01+00:00',
                'downloads': 2, 'last_download_at': '2026-10-23T01:02:01+00:00', 'items': {'test1': 'service.zip'}}}
        (self.orders / (self.oid + '.json')).write_text(json.dumps(self.order))
        self.archive = self.orders / 'delivery/service.zip'
        self.archive.write_bytes(b'PRIVATE_ARCHIVE_CONTENT')
        logs = self.home / 'logs'
        logs.mkdir()
        rows = []
        for method, code, size in [('GET', 200, self.archive.stat().st_size), ('GET', 200, self.archive.stat().st_size), ('HEAD', 200, 0), ('GET', 403, 12)]:
            rows.append('PRIVATE_IP - - [23/Oct/2026:01:02:00 +0000] "%s /download.php?o=%s&t=PRIVATE_DOWNLOAD_TOKEN&f=test1 HTTP/1.1" %s %s' % (method, self.oid, code, size))
        rows.append('PRIVATE_IP - - [23/Oct/2026:01:02:00 +0000] "GET /download.php?o=OTHER_ORDER&t=OTHER_TOKEN HTTP/1.1" 200 99')
        (logs / 'nastoronepodryadchika.ru.access.log').write_text('\n'.join(rows))
        (self.home / 'mail.log').write_text('[23-Oct-2026 01:01:01 UTC] mail() on [/private/products-config.php:884]: To: private-buyer@example.invalid, -- Headers: PRIVATE_HEADER')

    def snapshot(self):
        return {str(p.relative_to(self.home)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.home.rglob('*') if p.is_file()}

    def test_correlates_same_order_without_pii_or_hosting_writes(self):
        before = self.snapshot()
        original = io.open
        def readonly(file, mode='r', *args, **kwargs):
            self.assertFalse(any(c in mode for c in 'wax+'), 'hosting write attempted')
            self.assertNotEqual(Path(file), self.archive, 'archive contents must not be read')
            return original(file, mode, *args, **kwargs)
        with patch('io.open', readonly):
            report = inspect(self.site, self.home)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(report['order']['download_reservations'], 2)
        self.assertEqual(len(report['matching_access_records']), 4)
        self.assertEqual(sum(r['full_archive_bytes'] for r in report['matching_access_records']), 2)
        self.assertEqual(report['nearby_buyer_mail_transport_records'], 1)
        self.assertFalse(report['new_download_observer_present'])
        text = json.dumps(report)
        for secret in [self.oid, 'PRIVATE_', 'OTHER_TOKEN', 'private-buyer', '+79991234567', str(self.home)]:
            self.assertNotIn(secret, text)

    def test_multiple_orders_are_visible_as_ambiguity_not_owner_identity(self):
        other = {**self.order, 'id': 'order_older', 'created_at': '2026-10-22T01:00:00+00:00'}
        (self.orders / 'order_older.json').write_text(json.dumps(other))
        report = inspect(self.site, self.home)
        self.assertEqual(report['matching_service_orders'], 2)
        self.assertIn('owner identity not inferred', report['selection'])

    def test_unsupported_config_fails_without_execution(self):
        (self.site / 'config.php').write_text("<?php\ndefine('ORDERS_DIR', getenv('SECRET')); file_put_contents('BAD','BAD');")
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_ORDERS_PATH'):
            orders_path(self.site)
        self.assertFalse((self.site / 'BAD').exists())

    def test_receipt_output_uses_only_known_event_types_and_reasons(self):
        receipt = self.site.parent / 'mvb-private/funnel-outbox/download-receipts' / (hashlib.sha256(self.oid.encode()).hexdigest() + '.json')
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({'events': {'a': {'event_type': 'download.failed',
            'reason': 'PRIVATE_ERROR_MESSAGE', 'occurred_at': 'PRIVATE_TIMESTAMP', 'token': 'PRIVATE_TOKEN'},
            'b': {'event_type': 'PRIVATE_EVENT_TYPE'}}}))
        report = inspect(self.site, self.home)
        self.assertEqual(report['default_outbox_observations'], [{'type': 'download.failed', 'reason': None, 'at': None}])
        self.assertNotIn('PRIVATE_', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
