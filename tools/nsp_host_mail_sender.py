"""Change one verified hosting envelope-sender literal; never send mail."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home().resolve()
OLD = 'marzhavbetone.ru'
NEW = 'nastoronepodryadchika.ru'
BEFORE_SHA = '8cc8379ddbabec817b66b8823759c6e34ccef0c3cea30d533d523775d9fcaaa1'
BEFORE = b'nastoronepodryadchika@yandex.ru'
AFTER = b'site@nastoronepodryadchika.ru'

def need(ok, why):
    if not ok:
        raise RuntimeError(why)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def selected(domain):
    wrapper = HOME / ('php-bin-regru-php83/' + domain + '/php')
    env = os.environ.copy()
    for line in wrapper.read_text().splitlines():
        if line.startswith(('PHPRC=', 'PHP_INI_SCAN_DIR=')):
            key, value = line.split('=', 1)
            env[key] = value.strip("'\"")
    directories = [Path(p) for p in env.get('PHP_INI_SCAN_DIR', '').split(':') if p]
    need(len(directories) == 1 and directories[0].name == domain, 'WRAPPER_SELECTION')
    target = directories[0] / 'site.ini'
    code = "echo json_encode(['sendmail_path'=>ini_get('sendmail_path'),'forced_parameters'=>ini_get('mail.force_extra_parameters')]);"
    proc = subprocess.run(['/opt/php/8.3/bin/php', '-r', code], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
    need(proc.returncode == 0, 'PHP_CONFIG_READ')
    return target, json.loads(proc.stdout)

def protected():
    result = {}
    for domain in (OLD, NEW):
        for path in (HOME / ('www/' + domain)).glob('*.php'):
            result[domain + '/' + path.name] = digest(path.read_bytes())
    old_ini, _ = selected(OLD)
    result['old_site_ini'] = digest(old_ini.read_bytes())
    return result

def install(path, raw, mode):
    fd, temporary = tempfile.mkstemp(prefix='.nsp-envelope-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

action = sys.argv[1] if len(sys.argv) == 2 else ''
need(action in ('dry-run', 'apply'), 'ARGS')
target, runtime_before = selected(NEW)
need(target.is_file() and not target.is_symlink(), 'INI_REGULAR')
source = target.read_bytes()
need(digest(source) == BEFORE_SHA and source.count(BEFORE) == 1, 'SOURCE_DRIFT')
expected_before = '/usr/sbin/sendmail -t -i -f ' + BEFORE.decode()
expected_after = '/usr/sbin/sendmail -t -i -f ' + AFTER.decode()
need(runtime_before == {'sendmail_path': expected_before, 'forced_parameters': ''}, 'RUNTIME_BEFORE')
next_bytes = source.replace(BEFORE, AFTER)
mode = stat.S_IMODE(target.stat().st_mode)
receipt = {'status': 'READY', 'action': action, 'from_before': BEFORE.decode(), 'from_after': AFTER.decode(),
           'before_sha256': BEFORE_SHA, 'after_sha256': digest(next_bytes), 'mail_attempts': 0,
           'public_writes': 0, 'protected_php': 'UNCHANGED', 'delivery': 'NOT_TESTED'}
writable = target.stat().st_uid == os.getuid() and os.access(str(target.parent), os.W_OK)
if not writable:
    receipt.update(status='BLOCKED_SETTINGS_NOT_WRITABLE', file_owner_matches_ssh_user=target.stat().st_uid == os.getuid(), parent_writable=os.access(str(target.parent), os.W_OK), setting_file='PHP 8.3 domain site.ini')
    print(json.dumps(receipt))
    sys.exit(0)
if action == 'dry-run':
    print(json.dumps(receipt))
    sys.exit(0)
before = protected()
private = HOME / 'nsp-migration-private'
need(private.is_dir() and not private.is_symlink() and stat.S_IMODE(private.stat().st_mode) == 0o700, 'PRIVATE_DIRECTORY')
backup = private / 'hosting-envelope-20261022'
backup.mkdir(mode=0o700)
with (backup / 'site.ini').open('xb') as stream:
    stream.write(source)
os.chmod(str(backup / 'site.ini'), 0o600)
need((backup / 'site.ini').read_bytes() == source and target.read_bytes() == source, 'BACKUP_OR_CONCURRENT_EDIT')
installed = False
try:
    install(target, next_bytes, mode)
    installed = True
    _, runtime_after = selected(NEW)
    need(target.read_bytes() == next_bytes and stat.S_IMODE(target.stat().st_mode) == mode, 'INSTALL_VERIFY')
    need(runtime_after == {'sendmail_path': expected_after, 'forced_parameters': ''}, 'RUNTIME_AFTER')
    need(protected() == before, 'UNRELATED_CHANGE')
    receipt.update(status='APPLIED_VERIFIED_RUNTIME', private_backup='VERIFIED', old_domain='UNCHANGED', permissions='UNCHANGED', config_writes=1)
    print(json.dumps(receipt))
except Exception:
    if installed and target.read_bytes() == next_bytes:
        install(target, source, mode)
    raise
