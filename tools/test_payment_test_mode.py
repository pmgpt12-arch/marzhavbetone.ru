import json
import unittest
from tools.check_payment_test_mode import inspect_config


class PaymentModeTests(unittest.TestCase):
    def test_live_key_cannot_select_test_path(self):
        report = inspect_config('live_' + 'synthetic' * 5, 'synthetic-shop')
        self.assertFalse(report['test_configuration_present'])
        self.assertEqual(report['status'], 'LIVE_KEY_NOT_ALLOWED_FOR_NO_CHARGE_TEST')

    def test_complete_test_config_is_not_provider_acceptance(self):
        report = inspect_config('test_' + 'synthetic' * 5, 'synthetic-shop')
        self.assertTrue(report['test_configuration_present'])
        self.assertFalse(report['provider_verified'])
        self.assertEqual(report['provider_requests'], 0)

    def test_missing_shop_is_incomplete(self):
        self.assertFalse(inspect_config('test_' + 'synthetic' * 5, '')['test_configuration_present'])

    def test_empty_unknown_and_short_keys_are_not_ready(self):
        for key in ['', 'synthetic', 'test_']:
            self.assertFalse(inspect_config(key, 'synthetic-shop')['test_configuration_present'])

    def test_report_contains_no_key_or_shop_value(self):
        key, shop = 'test_' + 'synthetic' * 5, 'private-synthetic-shop'
        text = json.dumps(inspect_config(key, shop))
        self.assertNotIn(key, text)
        self.assertNotIn(shop, text)


if __name__ == '__main__':
    unittest.main()
