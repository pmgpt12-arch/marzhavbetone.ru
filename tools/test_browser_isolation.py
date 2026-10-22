import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from tools.browser_isolation import handle_external


class BrowserIsolationTests(unittest.TestCase):
    def test_local_assets_are_not_stubbed(self):
        route, observed = Mock(), []
        self.assertFalse(handle_external(route, SimpleNamespace(url='http://127.0.0.1:8100/app-script.php', method='GET'), 'http://127.0.0.1:8100', observed))
        route.fulfill.assert_not_called()
        route.abort.assert_not_called()
        self.assertEqual(observed, [])

    def test_telemetry_never_reaches_provider(self):
        route, observed = Mock(), []
        self.assertTrue(handle_external(route, SimpleNamespace(url='https://mc.yandex.ru/metrika/tag.js', method='GET'), 'http://127.0.0.1:8100', observed))
        route.fulfill.assert_called_once_with(status=204, body='')
        route.continue_.assert_not_called()
        self.assertEqual(observed[0]['disposition'], 'inert_external_telemetry')

    def test_unknown_external_asset_or_other_port_is_rejected(self):
        for url in ['https://external.invalid/a.css', 'http://127.0.0.1:8200/a.js', 'https://mc.yandex.ru.invalid/tag.js']:
            route, observed = Mock(), []
            self.assertTrue(handle_external(route, SimpleNamespace(url=url, method='GET'), 'http://127.0.0.1:8100', observed))
            route.abort.assert_called_once_with('blockedbyclient')
            route.fulfill.assert_not_called()
            self.assertEqual(observed[0]['disposition'], 'rejected_external_resource')


if __name__ == '__main__':
    unittest.main()
