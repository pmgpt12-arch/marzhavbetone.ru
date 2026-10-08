import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location('inventory', Path(__file__).parents[1] / 'p1_production_inventory.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SECRET = 'PRIVATE_PERSON_EMAIL_ORDER_ID_AND_SOURCE_CONTENT'


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name) / 'site'
        self.orders = self.site / 'orders'
        self.delivery = self.orders / 'delivery'
        self.delivery.mkdir(parents=True)
        (self.site / 'config.php').write_text("<?php\ndefine('ORDERS_DIR', __DIR__ . '/orders');\ndefine('SECRET', '" + SECRET + "');\n")

    def tearDown(self):
        self.tmp.cleanup()

    def order(self, sequence=1, **values):
        data = {'id': SECRET, 'email': SECRET, 'phone': SECRET,
                'status': 'paid', 'items': [{'sku': 'p1'}]}
        data.update(values)
        file = self.orders / ('order_' + SECRET + str(sequence) + '.json')
        file.write_text(json.dumps(data))
        return file

    def archive(self, name=M.KNOWN_LEGACY, members=None):
        path = self.delivery / name
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as package:
            for member in members or ['01-ks-2.docx', SECRET + '.txt']:
                package.writestr(member, SECRET)
        return path

    def encoded(self, report):
        value = json.dumps(report)
        self.assertNotIn(SECRET, value)
        self.assertNotIn(str(self.site), value)
        return value

    def test_paid_legacy_current_archive_is_read_but_not_historical_authority(self):
        path = self.archive()
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}, 'token': SECRET})
        report = M.scan(self.site)
        self.encoded(report)
        self.assertEqual(report['p1_order_counts']['paid__issued__no_pin'], 1)
        archive = report['archives'][0]
        self.assertEqual(archive['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(archive['zip_integrity'], 'crc_verified')
        self.assertEqual(archive['known_p1_members'], ['01-ks-2.docx'])
        self.assertEqual(archive['unknown_member_count'], 1)
        self.assertFalse(archive['historical_authority_verified'])

    def test_pending_and_paid_unissued_are_counted_without_archive_guess_or_build(self):
        self.order(status='pending')
        self.order(sequence=2)
        with mock.patch.object(M, 'inspect_archive', side_effect=AssertionError('must not inspect guessed archive')):
            report = M.scan(self.site)
        self.assertEqual(report['p1_order_counts']['pending__unissued__no_pin'], 1)
        self.assertEqual(report['p1_order_counts']['paid__unissued__no_pin'], 1)
        self.assertEqual(report['archives'], [])
        self.assertFalse((self.delivery / M.KNOWN_LEGACY).exists())

    def test_literal_sku_and_delivery_key_only_never_product_name_inference(self):
        self.order(items=[{'sku': 'test1', 'name': 'Комплект КС-2 КС-3'}])
        self.order(sequence=2, items=[{'name': SECRET}], delivery={'items': {'p1': M.KNOWN_LEGACY}})
        report = M.scan(self.site)
        self.assertEqual(report['item_sku_position_counts']['test1'], 1)
        self.assertEqual(report['p1_order_counts']['total_explicit_p1_orders'], 1)
        self.assertEqual(report['p1_order_counts']['explicit_delivery_key_only'], 1)
        self.encoded(report)

    def test_valid_recorded_pin_matches_current_bytes_without_timestamp_certification(self):
        initial = self.archive()
        sha = hashlib.sha256(initial.read_bytes()).hexdigest()
        name = 'p1-' + sha + '.zip'
        initial.rename(self.delivery / name)
        edition = {'zip': name, 'sha256': sha}
        self.order(items=[{'sku': 'p1', 'edition': edition}],
                   delivery={'items': {'p1': name}, 'editions': {'p1': edition}})
        report = M.scan(self.site)
        archive = report['archives'][0]
        self.assertTrue(archive['recorded_pin_matches_current_bytes'])
        self.assertFalse(archive['historical_authority_verified'])
        self.assertEqual(report['p1_order_counts']['paid__issued__valid_recorded_pin'], 1)

    def test_hash_mismatch_is_distinct_from_valid_zip_crc(self):
        name = 'p1-' + 'a' * 64 + '.zip'
        self.archive(name)
        self.order(items=[{'sku': 'p1', 'edition': {'zip': name, 'sha256': 'a' * 64}}],
                   delivery={'items': {'p1': name}})
        archive = M.scan(self.site)['archives'][0]
        self.assertEqual(archive['zip_integrity'], 'crc_verified')
        self.assertTrue(archive['recorded_pin_hash_mismatch'])
        self.assertFalse(archive['recorded_pin_matches_current_bytes'])

    def test_pin_conflict_and_reference_mismatch_are_not_repaired(self):
        self.archive()
        item = {'zip': 'p1-' + 'a' * 64 + '.zip', 'sha256': 'a' * 64}
        other = {'zip': 'p1-' + 'b' * 64 + '.zip', 'sha256': 'b' * 64}
        self.order(items=[{'sku': 'p1', 'edition': item}], delivery={'items': {'p1': M.KNOWN_LEGACY}, 'editions': {'p1': other}})
        self.order(sequence=2, items=[{'sku': 'p1', 'edition': item}], delivery={'items': {'p1': M.KNOWN_LEGACY}})
        report = M.scan(self.site)
        self.assertEqual(report['p1_order_counts']['conflicting_pins'], 1)
        self.assertEqual(report['archives'][0]['pin_basename_mismatch_references'], 1)
        self.assertFalse(report['archives'][0]['recorded_pin_matches_current_bytes'])

    def test_missing_archive_is_reported_only_in_known_scope(self):
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}})
        report = M.scan(self.site)
        self.assertEqual(report['archives'][0]['state'], 'missing_in_known_delivery_scope')
        self.assertEqual(report['paid_p1_archive_reference_state_counts']['missing_in_known_delivery_scope'], 1)
        self.assertEqual(list(self.delivery.iterdir()), [])

    def test_real_crc_corruption_and_plain_corruption_are_detected(self):
        path = self.archive(members=['01-ks-2.docx'])
        path.write_bytes(path.read_bytes().replace(SECRET.encode(), b'X' * len(SECRET), 1))
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}})
        self.assertEqual(M.scan(self.site)['archives'][0]['zip_integrity'], 'failed')
        path.write_bytes(b'not a zip')
        self.assertEqual(M.scan(self.site)['archives'][0]['state'], 'corrupt_or_unsupported_zip')

    def test_archive_and_order_symlinks_are_never_followed(self):
        outside = Path(self.tmp.name) / SECRET
        outside.write_text(SECRET)
        (self.orders / 'order_link.json').symlink_to(outside)
        (self.delivery / M.KNOWN_LEGACY).symlink_to(outside)
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}})
        report = M.scan(self.site)
        self.assertEqual(report['status'], 'PARTIAL')
        self.assertEqual(report['archives'][0]['state'], 'unsafe_or_unreadable_reference')
        self.encoded(report)

    def test_symlinked_orders_or_delivery_directories_are_rejected(self):
        self.delivery.rmdir()
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        self.delivery.symlink_to(outside, target_is_directory=True)
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}})
        self.assertEqual(M.scan(self.site)['archives'][0]['state'], 'known_delivery_directory_missing_unsafe_or_unreadable')
        self.delivery.unlink()
        for child in self.orders.iterdir():
            child.unlink()
        self.orders.rmdir()
        self.orders.symlink_to(outside, target_is_directory=True)
        self.assertEqual(M.scan(self.site)['status'], 'INCOMPLETE')

    def test_path_traversal_malformed_pin_status_and_unexpected_sku_are_redacted(self):
        self.order(status={'private': SECRET}, items=[{'sku': SECRET, 'edition': SECRET}, {'sku': 'p1', 'edition': SECRET}],
                   delivery={'items': {'p1': '../' + SECRET + '.zip'}})
        report = M.scan(self.site)
        self.encoded(report)
        self.assertEqual(report['p1_order_counts']['invalid_delivery_entry'], 1)
        self.assertEqual(report['p1_order_counts']['malformed_pin'], 1)
        self.assertEqual(report['archives'], [])

    def test_zip_unsafe_duplicates_and_limits_are_not_extracted(self):
        self.archive(members=['../' + SECRET])
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}})
        report = M.scan(self.site)
        self.encoded(report)
        self.assertEqual(report['archives'][0]['state'], 'unsafe_zip_members')
        self.archive(members=['01-ks-2.docx'])
        with mock.patch.object(M, 'MAX_UNCOMPRESSED', 1):
            self.assertEqual(M.scan(self.site)['archives'][0]['state'], 'zip_limit_not_inspected')

    def test_file_and_time_limits_produce_lower_bounds_not_fake_zero(self):
        self.order()
        self.order(sequence=2)
        with mock.patch.object(M, 'MAX_ORDERS', 1):
            report = M.scan(self.site)
        self.assertEqual(report['status'], 'PARTIAL')
        self.assertTrue(report['counts_are_lower_bounds'])
        self.assertEqual(report['order_files']['matching_files_seen'], 2)
        with mock.patch.object(M, 'MAX_ORDER_BYTES', 1):
            self.assertEqual(M.scan(self.site)['order_files']['oversize'], 2)
        with mock.patch.object(M, 'MAX_SECONDS', -1):
            self.assertEqual(M.scan(self.site)['status'], 'PARTIAL')

    def test_malformed_json_unknown_name_is_not_silently_zeroed(self):
        (self.orders / ('order_' + SECRET + '.json')).write_text('{broken ' + SECRET)
        report = M.scan(self.site)
        self.encoded(report)
        self.assertEqual(report['status'], 'PARTIAL')
        self.assertEqual(report['order_files']['malformed_unsafe_or_unreadable'], 1)

    def test_concurrent_order_change_invalidates_complete_count(self):
        path = self.order()
        real = M.order_snapshot
        calls = []
        def changed(fd):
            calls.append(1)
            if len(calls) == 2:
                path.write_text(json.dumps({'status': 'canceled', 'items': []}))
            return real(fd)
        with mock.patch.object(M, 'order_snapshot', side_effect=changed):
            report = M.scan(self.site)
        self.assertEqual(report['status'], 'PARTIAL')
        self.assertFalse(report['scan_entries_stable'])

    def test_scan_uses_only_read_flags_and_leaves_contents_names_mtimes_unchanged(self):
        self.archive()
        self.order(delivery={'items': {'p1': M.KNOWN_LEGACY}})
        def snapshot():
            return {str(p.relative_to(self.site)): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in self.site.rglob('*') if p.is_file()}
        before = snapshot()
        with mock.patch.object(M.os, 'open', wraps=os.open) as opening:
            M.scan(self.site)
        forbidden = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        self.assertTrue(opening.call_args_list)
        self.assertTrue(all(not (call.args[1] & forbidden) for call in opening.call_args_list))
        self.assertEqual(snapshot(), before)

    def test_failure_stdout_never_includes_exception_path_or_pii(self):
        output = io.StringIO()
        with mock.patch.object(M, 'scan', side_effect=RuntimeError(SECRET)), mock.patch.object(M.sys, 'argv', ['inventory', SECRET]), contextlib.redirect_stdout(output):
            self.assertEqual(M.main(), 2)
        self.assertNotIn(SECRET, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['status'], 'FAILED_SANITIZED')

    def test_static_orders_parser_accepts_only_exact_literal_paths(self):
        known = str(self.orders.absolute())
        self.assertTrue(M.static_orders_match("<?php define('ORDERS_DIR', __DIR__ . '/orders');", known))
        self.assertTrue(M.static_orders_match("<?php define('ORDERS_DIR', __DIR__ . '/orders'); ?>\n", known))
        self.assertTrue(M.static_orders_match("<?php const ORDERS_DIR = __DIR__ . '/orders';", known))
        self.assertTrue(M.static_orders_match("<?php define('ORDERS_DIR', '" + known + "');", known))
        self.assertFalse(M.static_orders_match("<?php define('ORDERS_DIR', '/elsewhere/orders');", known))
        for source in ["<?php define('ORDERS_DIR', getenv('PRIVATE_PATH'));",
                       "<?php define('ORDERS_DIR', __DIR__ . '/alternate');",
                       "<?php define('ORDERS_DIR', '/a'); define('ORDERS_DIR', '/b');",
                       "<?php include '" + SECRET + "'; define('ORDERS_DIR', __DIR__ . '/orders');",
                       "<?php define($variable, 'value'); define('ORDERS_DIR', __DIR__ . '/orders');",
                       "<?php $s = <<<TEXT\ndefine('ORDERS_DIR', __DIR__ . '/orders');\nTEXT;",
                       "<?php // define('ORDERS_DIR', __DIR__ . '/orders');\n"]:
            self.assertIsNone(M.static_orders_match(source, known))

    def test_parser_does_not_take_comments_or_quoted_examples_as_declarations(self):
        source = "<?php /* define('ORDERS_DIR', '/wrong'); */\n$s = \"define('ORDERS_DIR', '/wrong');\";\ndefine('ORDERS_DIR', __DIR__ . '/orders');"
        self.assertTrue(M.static_orders_match(source, str(self.orders.absolute())))

    def test_unknown_or_other_configured_directory_never_claims_zero_or_guesses(self):
        for source in ["<?php define('ORDERS_DIR', getenv('" + SECRET + "'));",
                       "<?php define('ORDERS_DIR', '/other/orders');"]:
            (self.site / 'config.php').write_text(source)
            report = M.scan(self.site)
            self.encoded(report)
            self.assertEqual(report['status'], 'PARTIAL')
            self.assertTrue(report['counts_are_lower_bounds'])
            self.assertIn('configured_order_path_static_match_unknown_or_false_no_zero_p1_inference', report['remaining_blockers'])

    def test_config_file_symlink_is_not_followed_and_no_secret_is_emitted(self):
        (self.site / 'config.php').unlink()
        outside = Path(self.tmp.name) / SECRET
        outside.write_text("<?php define('ORDERS_DIR', __DIR__ . '/orders');")
        (self.site / 'config.php').symlink_to(outside)
        report = M.scan(self.site)
        self.encoded(report)
        self.assertIsNone(report['configured_orders_dir_matches_known_path'])
        self.assertEqual(report['status'], 'PARTIAL')


if __name__ == '__main__':
    unittest.main()
