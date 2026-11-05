#!/usr/bin/env python3
"""One bounded authorized owner Gmail canary through the existing hosting SSH route."""
import json
import os
import pathlib
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
EVIDENCE = pathlib.Path('/tmp/nsp-final-evidence')
PAYLOAD = (ROOT / 'tools/nsp-final/mail-from-20261105/canary.php').read_bytes()
HOST = os.environ['HOST']
USER = os.environ['SSH_USER']
PORT = os.environ['PORT']
assert PORT.isdigit() and HOST and USER and PAYLOAD.startswith(b'<?php'), 'PREFLIGHT_ARGS'

# This reads ONLY the two vhost PHP environment variables from the existing
# REG.RU wrapper. It does not execute that file, print its contents or read keys.
REMOTE = r'''
import os
import pathlib
import subprocess
import sys
base = pathlib.Path.home()
wrapper = base / 'php-bin-regru-php83/nastoronepodryadchika.ru/php'
lines = wrapper.read_text().splitlines()
settings = {}
for line in lines:
    for key in ('PHPRC', 'PHP_INI_SCAN_DIR'):
        if line.startswith(key + '='):
            value = line.split('=', 1)[1].strip()
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            settings[key] = value
assert set(settings) == set(('PHPRC', 'PHP_INI_SCAN_DIR')), 'VHOST_ENV_MISSING'
env = os.environ.copy()
env.update(settings)
data = sys.stdin.buffer.read()
assert data.startswith(b'<?php') and len(data) < 9000, 'PHP_PAYLOAD_SCOPE'
cmd = [
    '/opt/php/8.3/bin/php', '/dev/stdin',
    str(base / 'www/nastoronepodryadchika.ru'),
    str(base / 'nsp-migration-private'),
]
p = subprocess.run(cmd, input=data, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE, timeout=32, env=env)
sys.stdout.buffer.write(p.stdout)
sys.stderr.buffer.write(p.stderr[:1024])
sys.exit(p.returncode)
'''
ssh = [
    'ssh', '-p', PORT, '-i', str(pathlib.Path.home() / '.ssh/nsp_final_key'),
    '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
    '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=12',
    USER + '@' + HOST, 'python3 -c ' + shlex.quote(REMOTE),
]
try:
    result = subprocess.run(ssh, input=PAYLOAD, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=65)
    if result.returncode != 0:
        sys.stderr.write('NSP_CANARY_EXECUTION_BLOCKED=' +
                         result.stderr.decode(errors='replace')[-500:] + '\n')
        raise SystemExit(1)
    report = json.loads(result.stdout)
    if not (report.get('status') == 'ACCEPTED_BY_LOCAL_MAIL_TRANSPORT'
            and report.get('mail_attempts') == 1
            and report.get('production_php_files_modified') == 0
            and report.get('orders_created') == 0
            and report.get('payment_requests') == 0):
        raise RuntimeError('CANARY_RECEIPT_NOT_ACCEPTED')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / 'mail-canary.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print('NSP_MAIL_CANARY_ACCEPTED_BY_LOCAL_TRANSPORT_ONLY')
    print('INBOX_AND_AUTHENTICATION_PENDING_INDEPENDENT_GMAIL_CHECK')
except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
    sys.stderr.write('NSP_MAIL_CANARY_BLOCKED=' + type(e).__name__ + '\n')
    raise SystemExit(1)
