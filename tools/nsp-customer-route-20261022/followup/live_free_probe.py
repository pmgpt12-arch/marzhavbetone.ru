#!/usr/bin/env python3
"""Explicit live acceptance probe; two synthetic submissions, no paid orders."""
import argparse
import hashlib
import io
import json
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'observed_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'published site; two explicitly requested synthetic free-material submissions',
              'paid_orders': 0, 'rows': []}
    origin = 'https://nastoronepodryadchika.ru'
    for material, expected in [('checklist', '/downloads/checklist-zakrytiya-rabot.pdf'),
                               ('dengi', '/downloads/dengi.zip')]:
        row = {'material': material, 'expected_path': expected}
        report['rows'].append(row)
        try:
            body = urllib.parse.urlencode({'name': 'Проверка staging-маршрута НСП',
                'contact': 'route-qa@example.invalid', 'consent': 'yes',
                'material': material, 'source': 'staging_acceptance_20261023'}).encode()
            request = urllib.request.Request(origin + '/lead.php', data=body,
                headers={'Accept': 'application/json', 'User-Agent': 'NSP-authorized-acceptance/1.0'})
            with urllib.request.urlopen(request, timeout=12) as response:
                row['form_http'] = response.status
                result = json.load(response)
            assert result.get('ok') is True
            assert result.get('download') == expected, 'unexpected download route'
            request = urllib.request.Request(origin + expected,
                headers={'User-Agent': 'NSP-authorized-acceptance/1.0'})
            with urllib.request.urlopen(request, timeout=15) as response:
                assert urllib.parse.urlsplit(response.url).netloc == 'nastoronepodryadchika.ru'
                data = response.read(30 * 1024 * 1024 + 1)
                assert len(data) <= 30 * 1024 * 1024
                row.update(download_http=response.status, bytes=len(data),
                           mime=response.headers.get_content_type(),
                           sha256=hashlib.sha256(data).hexdigest())
                length = response.headers.get('Content-Length')
                if length is not None:
                    assert len(data) == int(length), 'incomplete HTTP body'
            if material == 'checklist':
                assert data.startswith(b'%PDF-')
            else:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    assert archive.testzip() is None
                    row['archive_entries'] = sum(not n.endswith('/') for n in archive.namelist())
                    assert row['archive_entries'] > 0
            row['status'] = 'PASS_REAL_BYTES'
        except Exception as error:
            row.update(status='FAIL', error=type(error).__name__ + ': ' + str(error)[:250])
    report['limits'] = ['admin notification delivery is not checked',
                        'not an acceptance of the unpublished candidate form',
                        'HTTP receipt does not prove an analytics download_served event',
                        'no paid-provider or buyer-email acceptance']
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(any(row['status'] != 'PASS_REAL_BYTES' for row in report['rows']))


if __name__ == '__main__':
    raise SystemExit(main())
