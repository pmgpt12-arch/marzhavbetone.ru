#!/usr/bin/env python3
"""Verify active NSP mail headers and all 11 free-material routes without sending email."""
from pathlib import Path
import email
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NEW_FROM = 'site@nastoronepodryadchika.ru'
OLD_FROM = 'site@marzhavbetone.ru'
KNOWN_FLAGS = {'--handlers-only', '--sender-candidate'}
assert set(sys.argv[1:]) <= KNOWN_FLAGS, 'Unsupported test flag'

# Contact.php now returns HTTP 410. Do not test it as an active mail handler.
retired = (ROOT / 'contact.php').read_text()
assert 'http_response_code(410)' in retired and 'mail(' not in retired
for name in ['lead.php', 'webhook.php', 'products-config.php']:
    source = (ROOT / name).read_text()
    assert source.count('From: ' + NEW_FROM) == 1, name
    assert 'From: ' + OLD_FROM not in source, name
    lint = subprocess.run(['php', '-l', str(ROOT / name)],
                          capture_output=True, text=True, timeout=8)
    assert lint.returncode == 0, (name, lint.stderr)

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    site = base / 'nastoronepodryadchika.ru'
    site.mkdir()
    shutil.copy2(ROOT / 'lead.php', site / 'lead.php')
    shutil.copy2(ROOT / 'mvb_funnel.php', site / 'mvb_funnel.php')
    shutil.copytree(ROOT / 'taxonomy', site / 'taxonomy')

    capture = base / 'mail.txt'
    fake = base / 'capture.py'
    fake.write_text(
        'import pathlib,sys\n'
        'pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())\n'
    )
    env = os.environ.copy()
    env['MVB_FUNNEL_OUTBOX'] = str(base / 'outbox')
    code = '$_SERVER["REQUEST_METHOD"]=$argv[1]; $_POST=json_decode($argv[2],true); require $argv[3];'

    def invoke(fields, method='POST'):
        capture.unlink(missing_ok=True)
        cmd = [
            'php', '-d', f'sendmail_path=python3 {fake} {capture}',
            '-r', code, method, json.dumps(fields), str(site / 'lead.php'),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=12, env=env)
        assert result.returncode == 0, result.stderr
        response = json.loads(result.stdout)
        message = email.message_from_bytes(capture.read_bytes()) if capture.exists() else None
        return response, message

    # No mail for GET or invalid POST.
    for fields, method in [({}, 'GET'), ({}, 'POST')]:
        response, message = invoke(fields, method)
        assert not response['ok'] and message is None

    free_ids = [
        'checklist', 'dengi', 'dop-raboty', 'vozvrat-ks',
        'uderzhaniya', 'dogovor', 'bankrotstvo', 'avans',
        'raschet-metrami', 'ispolnitelnaya-dokumentaciya',
        'akt-skrytyh-rabot',
    ]
    for key in free_ids:
        response, message = invoke({
            'name': 'Synthetic user',
            'contact': 'test@example.invalid',
            'consent': 'yes',
            'material': key,
        })
        expected = ('/downloads/checklist-zakrytiya-rabot.pdf'
                    if key == 'checklist' else '/downloads/' + key + '.zip')
        assert response['ok'] and response['download'] == expected, key
        assert message is not None, key
        assert message['To'] == 'nastoronepodryadchika@yandex.ru', key
        assert message['From'] == NEW_FROM, key

print(json.dumps({
    'status': 'PASS', 'active_handlers': 3,
    'retired_contact': '410', 'free_routes_verified': 11,
    'negative_cases': 2, 'real_messages_sent': 0,
    'sender': NEW_FROM,
}))
