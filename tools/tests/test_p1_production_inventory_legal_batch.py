import base64
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).parents[1]
sys.path.insert(0, str(TOOLS))
import p1_host_legal_batch as L
import run_p1_inventory_ssh as T
sys.path.pop(0)

SECRET = 'DO_NOT_LOG_CREDENTIALS_OR_REMOTE_STDERR'


class LegalBatchTests(unittest.TestCase):
    def receipt(self):
        responses = []
        for key, url, _ in L.REQUESTS:
            body, headers = b'official source fixture', b'HTTP/1.1 500 Error\r\n\r\n'
            responses.append(dict(key=key, url=url, http_status=500, curl_exit_code=0,
                seconds=.01, redirects_followed=0, body_truncated=False, headers_truncated=False,
                body_sha256=L.digest(body), headers_sha256=L.digest(headers),
                body_base64=base64.b64encode(body).decode(), headers_base64=base64.b64encode(headers).decode(),
                verification_status='NOT_VERIFIED'))
        return dict(status='ONE_BATCH_FETCHED', logical_requests=5, host_files_written=False,
                    verification_status='NOT_VERIFIED', responses=responses)

    def runner(self, receipt, returncode=0):
        result = mock.Mock(stdout=json.dumps(receipt).encode(), stderr=SECRET.encode(), returncode=returncode)
        env = dict(INVENTORY_HOST='host.example', INVENTORY_USER='user', SITE_PATH='www/site', SSH_PORT='22')
        stdout = io.StringIO()
        with mock.patch.dict(sys.modules, {'run_p1_inventory_ssh': T}), mock.patch.dict(os.environ, env), \
                mock.patch.object(L.subprocess, 'run', return_value=result) as call, contextlib.redirect_stdout(stdout):
            code = L.runner()
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.kwargs['timeout'], 60)
        self.assertEqual(call.call_args.args[0][-1], 'python3 -B - --remote')
        self.assertIn('BatchMode=yes', call.call_args.args[0])
        self.assertNotIn(SECRET, stdout.getvalue())
        return code, json.loads(Path('legal-source-output/receipt.json').read_text())

    def test_exact_five_known_urls_no_duplicate_pdf_or_fallback(self):
        self.assertEqual(len(L.REQUESTS), 5)
        self.assertEqual(sum(x[2] for x in L.REQUESTS), 28 * 1024 * 1024)
        self.assertEqual([x[0] for x in L.REQUESTS], ['gk2', 'nk2', 'fz127', 'ppvs7_registered_card', 'ppvs54_known_card'])
        with mock.patch.object(L.shutil, 'which', return_value='/usr/bin/curl'), \
                mock.patch.object(L, 'one', side_effect=lambda curl, entry: entry[0]) as call:
            receipt = L.remote()
        self.assertEqual(call.call_count, 5)
        self.assertEqual(receipt['responses'], [x[0] for x in L.REQUESTS])
        with mock.patch.object(L.shutil, 'which', return_value=None), mock.patch.object(L, 'one') as call:
            receipt = L.remote()
        call.assert_not_called()
        self.assertEqual(receipt['status'], 'CURL_CLI_UNAVAILABLE')

    def worker_fixture(self, body, headers, limit=1024):
        actual_popen = subprocess.Popen
        seen = []
        def isolated_process(command, **kwargs):
            seen.append((command, kwargs))
            return actual_popen([sys.executable, '-c', 'import os;os.write(1,' + repr(body) + ');os.write(2,' + repr(headers) + ')'], **kwargs)
        with mock.patch.object(L.subprocess, 'Popen', side_effect=isolated_process):
            response = L.one('/usr/bin/curl', (L.REQUESTS[0][0], L.REQUESTS[0][1], limit))
        command, kwargs = seen[0]
        self.assertEqual(command[1], '-q')
        for flag, value in [('--retry', '0'), ('--max-time', '12'), ('--max-redirs', '0'), ('--noproxy', '*')]:
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertNotIn('-L', command)
        self.assertNotIn('--location', command)
        self.assertEqual(kwargs['env'], {'LC_ALL': 'C'})
        self.assertNotIn('--output', command)
        return response

    def test_worker_redirect_is_captured_without_follow_or_error_diagnostic(self):
        response = self.worker_fixture(b'partial body' + L.TRAILER + b'302\n', b'HTTP/1.1 302 Found\r\nLocation: https://evil.invalid/\r\n\r\n' + SECRET.encode())
        self.assertEqual(response['http_status'], 302)
        self.assertEqual(response['redirects_followed'], 0)
        self.assertEqual(base64.b64decode(response['body_base64']), b'partial body')
        self.assertNotIn(SECRET.encode(), base64.b64decode(response['headers_base64']))
        self.assertEqual(response['verification_status'], 'NOT_VERIFIED')

    def test_worker_over_limit_kills_and_truncates_bounded_body(self):
        response = self.worker_fixture(b'X' * 10000, b'', limit=32)
        self.assertTrue(response['body_truncated'])
        self.assertLessEqual(len(base64.b64decode(response['body_base64'])), 32)
        self.assertEqual(response['http_status'], 0)

    def test_mixed_http_headers_end_before_cli_diagnostics(self):
        data = b'HTTP/1.1 100 Continue\n\nHTTP/2 200\r\nA: B\r\n\r\n' + SECRET.encode()
        self.assertEqual(L.headers_only(data), data[:-len(SECRET)])

    def test_validated_bytes_saved_runner_only_but_not_semantically_verified(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
            code, receipt = self.runner(self.receipt())
            self.assertEqual(code, 0)
            self.assertEqual(receipt['verification_status'], 'NOT_VERIFIED')
            self.assertEqual(len(list(Path('legal-source-output').glob('*.body'))), 5)
            self.assertNotIn('body_base64', json.dumps(receipt))
            self.assertNotIn(SECRET, json.dumps(receipt))

    def test_forged_receipts_rejected_before_any_source_body_is_saved(self):
        mutations = [lambda r: r.update(email=SECRET),
            lambda r: r['responses'][0].update(url='https://evil.invalid/'),
            lambda r: r['responses'][0].update(body_sha256='0' * 64),
            lambda r: r['responses'][0].update(seconds=float('nan')),
            lambda r: r['responses'][0].update(redirects_followed=False),
            lambda r: r['responses'][0].update(curl_exit_code=999),
            lambda r: r['responses'][0].update(email=SECRET)]
        for mutate in mutations:
            receipt = self.receipt()
            mutate(receipt)
            with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
                code, saved = self.runner(receipt)
                self.assertEqual(code, 2)
                self.assertEqual(list(Path('legal-source-output').glob('*.body')), [])
                self.assertNotIn(SECRET, json.dumps(saved))

    def test_transport_failure_and_absent_curl_are_single_attempt_without_fallback(self):
        for received, rc, expected in [({}, 255, 2),
            (dict(status='CURL_CLI_UNAVAILABLE', logical_requests=0, host_files_written=False,
                  verification_status='NOT_VERIFIED', responses=[]), 0, 0)]:
            with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
                code, _ = self.runner(received, rc)
                self.assertEqual(code, expected)
                self.assertEqual(list(Path('legal-source-output').glob('*.body')), [])


if __name__ == '__main__':
    unittest.main()
