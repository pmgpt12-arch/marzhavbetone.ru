#!/usr/bin/env python3
"""Disabled-by-default one batch: five known official URLs, no host files."""
import base64
import concurrent.futures
import hashlib
import json
import math
import os
import selectors
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

REQUESTS = [
    ('gk2', 'http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102039276', 8 * 1024 * 1024),
    ('nk2', 'http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102067058', 8 * 1024 * 1024),
    ('fz127', 'http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102078527', 8 * 1024 * 1024),
    ('ppvs7_registered_card', 'https://vsrf.ru/documents/own/8478/', 2 * 1024 * 1024),
    ('ppvs54_known_card', 'https://vsrf.ru/documents/all/8524/', 2 * 1024 * 1024),
]
HOSTS = {'pravo.gov.ru', 'vsrf.ru', 'www.vsrf.ru'}
HEADER_LIMIT = 256 * 1024
TRAILER = b'\n__P1_HTTP_CODE__:'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def headers_only(data):
    """Keep complete HTTP header blocks; discard CLI diagnostics."""
    result = b''
    while data.startswith(b'HTTP/'):
        separators = [(data.find(s), s) for s in (b'\r\n\r\n', b'\n\n') if data.find(s) >= 0]
        if not separators:
            break
        end, separator = min(separators, key=lambda item: item[0])
        if end < 0:
            break
        end += len(separator)
        result += data[:end]
        data = data[end:]
    return result


def one(curl, request):
    key, url, limit = request
    assert urlsplit(url).hostname in HOSTS and urlsplit(url).scheme in {'http', 'https'}
    command = [curl, '-q', '--noproxy', '*', '--proto', '=http,https', '--max-time', '12',
               '--retry', '0', '--max-redirs', '0', '--silent', '--show-error',
               '--dump-header', '/dev/stderr', '--write-out', TRAILER.decode() + '%{http_code}\n', url]
    started = time.monotonic()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={'LC_ALL': 'C'})
    buffers = {'body': bytearray(), 'headers': bytearray()}
    truncated = {'body': False, 'headers': False}
    try:
        with selectors.DefaultSelector() as selected:
            selected.register(proc.stdout, selectors.EVENT_READ, 'body')
            selected.register(proc.stderr, selectors.EVENT_READ, 'headers')
            while selected.get_map():
                if time.monotonic() - started > 14:
                    proc.kill()
                    break
                for event, _ in selected.select(.1):
                    chunk = os.read(event.fileobj.fileno(), 65536)
                    if not chunk:
                        selected.unregister(event.fileobj)
                        continue
                    label = event.data
                    maximum = limit + 128 if label == 'body' else HEADER_LIMIT
                    room = maximum - len(buffers[label])
                    buffers[label].extend(chunk[:room])
                    if len(chunk) > room:
                        truncated[label] = True
                        proc.kill()
                        break
                if any(truncated.values()):
                    break
        proc.wait(timeout=2)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)
        proc.stdout.close()
        proc.stderr.close()
    output = bytes(buffers['body'])
    code, body = 0, output[:limit]
    if TRAILER in output:
        candidate_body, metadata = output.rsplit(TRAILER, 1)
        if metadata.strip().isdigit() and len(metadata.strip()) == 3:
            code, body = int(metadata.strip()), candidate_body[:limit]
            truncated['body'] |= len(candidate_body) > limit
    headers = headers_only(bytes(buffers['headers']))
    return {'key': key, 'url': url, 'http_status': code, 'curl_exit_code': proc.returncode,
            'seconds': round(time.monotonic() - started, 3), 'redirects_followed': 0,
            'body_truncated': truncated['body'], 'headers_truncated': truncated['headers'],
            'body_sha256': digest(body), 'headers_sha256': digest(headers),
            'body_base64': base64.b64encode(body).decode(), 'headers_base64': base64.b64encode(headers).decode(),
            'verification_status': 'NOT_VERIFIED'}


def remote():
    curl = shutil.which('curl')
    if curl is None:
        return {'status': 'CURL_CLI_UNAVAILABLE', 'logical_requests': 0, 'host_files_written': False,
                'verification_status': 'NOT_VERIFIED', 'responses': []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as workers:
        # Fixed five calls, exactly once each. No retries, redirects or fallback URLs.
        responses = list(workers.map(lambda item: one(curl, item), REQUESTS))
    return {'status': 'ONE_BATCH_FETCHED', 'logical_requests': 5, 'host_files_written': False,
            'verification_status': 'NOT_VERIFIED', 'responses': responses}


def runner():
    import run_p1_inventory_ssh as access
    out = Path('legal-source-output')
    out.mkdir(exist_ok=True)
    report = {'status': 'ONE_BATCH_TRANSPORT_FAILED_SANITIZED', 'verification_status': 'NOT_VERIFIED'}
    try:
        command = access.invocation(os.environ)
        command[-1] = 'python3 -B - --remote'
        result = subprocess.run(command, input=Path(__file__).read_bytes(), capture_output=True, timeout=60)
        if result.returncode != 0 or len(result.stdout) > 40 * 1024 * 1024:
            raise ValueError('bounded fetch unavailable')
        received = json.loads(result.stdout)
        if not isinstance(received, dict) or set(received) != {'status', 'logical_requests', 'host_files_written', 'verification_status', 'responses'}:
            raise ValueError('unexpected receipt fields')
        if received.get('host_files_written') is not False or received.get('verification_status') != 'NOT_VERIFIED':
            raise ValueError('invalid source receipt')
        if received.get('status') == 'CURL_CLI_UNAVAILABLE' and received.get('logical_requests') == 0 and received.get('responses') == []:
            report = {'status': 'CURL_CLI_UNAVAILABLE', 'logical_requests': 0, 'host_files_written': False,
                      'verification_status': 'NOT_VERIFIED'}
        else:
            responses = received.get('responses')
            if received.get('status') != 'ONE_BATCH_FETCHED' or received.get('logical_requests') != 5 or not isinstance(responses, list) or len(responses) != 5:
                raise ValueError('invalid batch count')
            validated = []
            allowed = {'key', 'url', 'http_status', 'curl_exit_code', 'seconds', 'redirects_followed',
                       'body_truncated', 'headers_truncated', 'body_sha256', 'headers_sha256',
                       'body_base64', 'headers_base64', 'verification_status'}
            for response, (key, url, limit) in zip(responses, REQUESTS):
                if not isinstance(response, dict) or set(response) != allowed or response['key'] != key or response['url'] != url:
                    raise ValueError('unexpected source')
                body = base64.b64decode(response['body_base64'], validate=True)
                headers = base64.b64decode(response['headers_base64'], validate=True)
                if len(body) > limit or len(headers) > HEADER_LIMIT or digest(body) != response['body_sha256'] or digest(headers) != response['headers_sha256']:
                    raise ValueError('invalid bounded body')
                if type(response['http_status']) is not int or not 0 <= response['http_status'] <= 599 or response['verification_status'] != 'NOT_VERIFIED' or type(response['redirects_followed']) is not int or response['redirects_followed'] != 0:
                    raise ValueError('unexpected result')
                if type(response['curl_exit_code']) is not int or not -9 <= response['curl_exit_code'] <= 255 or type(response['seconds']) not in {float, int} or not math.isfinite(response['seconds']) or not 0 <= response['seconds'] <= 20 or any(type(response[k]) is not bool for k in ['body_truncated', 'headers_truncated']):
                    raise ValueError('invalid result types')
                validated.append((key, body, headers, {k: v for k, v in response.items() if k not in {'body_base64', 'headers_base64'}}))
            # Save source bytes only after every response passed validation.
            for key, body, headers, _ in validated:
                (out / (key + '.body')).write_bytes(body)
                (out / (key + '.headers')).write_bytes(headers)
            report = {'status': 'ONE_BATCH_FETCHED', 'logical_requests': 5, 'host_files_written': False,
                      'verification_status': 'NOT_VERIFIED', 'responses': [r for _, _, _, r in validated]}
    except BaseException:
        pass
    (out / 'receipt.json').write_text(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    print('Optional official-source one batch: receipt saved; no bodies, credentials or raw remote output logged.')
    return 0 if report['status'] in {'ONE_BATCH_FETCHED', 'CURL_CLI_UNAVAILABLE'} else 2


if __name__ == '__main__':
    if sys.argv[1:] == ['--remote']:
        try:
            print(json.dumps(remote(), ensure_ascii=True))
        except BaseException:
            print(json.dumps({'status': 'REMOTE_BATCH_FAILED_SANITIZED', 'verification_status': 'NOT_VERIFIED'}))
    else:
        raise SystemExit(runner())
