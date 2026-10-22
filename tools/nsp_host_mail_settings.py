"""Read only mail-related hosting configuration for two exact project domains."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

HOME = Path.home().resolve()
DOMAINS = ('marzhavbetone.ru', 'nastoronepodryadchika.ru')
ALLOWED = {'site@' + d for d in DOMAINS}
ALLOWED.add('nastoronepodryadchika@yandex.ru')

def safe(value):
    value = str(value).replace(str(HOME), '[HOME]')
    user = os.environ.get('USER', '')
    if user:
        value = value.replace(user, '[hosting-user]')
    return re.sub(r'[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}',
                  lambda m: m[0] if m[0].lower() in ALLOWED or m[0].lower().split('@')[-1] in DOMAINS else '[OTHER_EMAIL]', value, flags=re.I)

def inspect(path):
    record = {'path': safe(path), 'symlink': path.is_symlink()}
    try:
        raw = path.read_bytes()
        record.update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
        if len(raw) > 2_000_000:
            record['skipped'] = 'SIZE_LIMIT'
            return record
        text = raw.decode('utf-8', errors='replace')
        matches = []
        for number, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s or s.startswith((';', '#')):
                continue
            if re.match(r'^(sendmail_path|mail\.force_extra_parameters|mail\.log|SMTP|smtp_port)\s*=', s, re.I):
                matches.append({'line': number, 'setting': safe(s)})
            elif re.match(r'^disable_functions\s*=', s, re.I):
                matches.append({'line': number, 'mail_disabled': bool(re.search(r'\bmail\b', s.split('=', 1)[1]))})
            elif any('@' + d in s for d in DOMAINS) and ('sendmail' in s or 'ServerAdmin' in s or 'php_admin' in s):
                matches.append({'line': number, 'setting': safe(s[:1000])})
            elif ('PHPRC' in s or 'PHP_INI_SCAN_DIR' in s or s.startswith('exec ')) and not re.search(r'pass|token|secret', s, re.I):
                matches.append({'line': number, 'setting': safe(s[:1000])})
        if path.name == 'php' and len(raw) < 1000:
            record['wrapper'] = safe(text)
        record['mail_settings'] = matches[:30]
    except (OSError, ValueError) as e:
        record['error'] = type(e).__name__
    return record

paths = set()
for pattern in ('php-bin*/php.ini', 'php-bin*/*/php.ini', 'php-bin*/*/php', 'php-bin*/*/*.sh',
                'php-bin*/php', 'php-bin*/.htaccess'):
    for path in HOME.glob(pattern):
        if path.is_file():
            paths.add(path)
runtime = []
for domain in DOMAINS:
    wrapper = HOME / f'php-bin-regru-php83/{domain}/php'
    if not wrapper.is_file():
        continue
    env = os.environ.copy()
    for line in wrapper.read_text().splitlines():
        if line.startswith(('PHPRC=', 'PHP_INI_SCAN_DIR=')):
            key, value = line.split('=', 1)
            env[key] = value.strip("'\"")
    for key in ('PHPRC', 'PHP_INI_SCAN_DIR'):
        for directory in env.get(key, '').split(':'):
            if directory and Path(directory).is_dir():
                paths.update(Path(directory).glob('*.ini'))
    php = Path('/opt/php/8.3/bin/php')
    code = "echo json_encode(['loaded_ini'=>php_ini_loaded_file(),'scanned_ini'=>php_ini_scanned_files(),'sendmail_path'=>ini_get('sendmail_path'),'forced_parameters'=>ini_get('mail.force_extra_parameters'),'mail_enabled'=>function_exists('mail')]);"
    try:
        proc = subprocess.run([str(php), '-r', code], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
        runtime.append({'domain': domain, 'exit': proc.returncode, 'selected_config_values': safe(proc.stdout[:6000])})
    except (OSError, subprocess.TimeoutExpired) as exc:
        runtime.append({'domain': domain, 'error': type(exc).__name__})
for domain in DOMAINS:
    for relative in (f'www/{domain}/.user.ini', f'www/{domain}/php.ini', f'www/{domain}/.htaccess'):
        path = HOME / relative
        if path.is_file():
            paths.add(path)
for pattern in ('/etc/httpd/conf/vhosts/*/*.conf', '/etc/apache2/vhosts/*/*.conf', '/etc/php*/*/fpm/pool.d/*.conf'):
    import glob
    for name in glob.glob(pattern):
        if any(d in name for d in DOMAINS):
            paths.add(Path(name))
mailboxes = {}
for domain in DOMAINS:
    mailboxes[domain] = {relative: (HOME / relative).is_dir() for relative in
        (f'email/{domain}/site', f'mail/{domain}/site', f'etc/{domain}', f'email/{domain}')}
result = {'status': 'READ_ONLY_HOST_MAIL_SETTINGS', 'mail_attempts': 0, 'public_writes': 0,
          'configs': [inspect(p) for p in sorted(paths)][:50],
          'mailbox_directory_hints_not_authoritative': mailboxes, 'wrapper_selected_php_config': runtime}
result['project_mailbox_entries'] = []
for directory in (HOME / 'passwd', HOME / 'etc/passwd', HOME / 'email/passwd'):
    if directory.is_file():
        try:
            text = directory.read_text(errors='replace')
            result['project_mailbox_entries'].append({'path': safe(directory), 'site_old_mentioned': 'site@marzhavbetone.ru' in text, 'site_new_mentioned': 'site@nastoronepodryadchika.ru' in text})
        except OSError:
            pass
def dkim_options(text):
    result = {}
    for line in text.splitlines():
        match = re.match(r'^\s*(dkim_domain|dkim_selector|dkim_private_key|dkim_strict|dkim_canon)\s*=\s*(.*)', line)
        if not match:
            continue
        name, value = match.groups()
        row = {'configured': True}
        if name == 'dkim_private_key':
            row['uses_authenticated_sender_condition'] = 'authenticated' in value.lower()
            row['uses_sender_domain'] = 'sender_address_domain' in value
            row['private_value'] = 'NOT_DISCLOSED'
        else:
            row['value'] = safe(value[:1000])
        result[name] = row
    return result

dkim = {'files': [], 'transport': None, 'private_keys_read': 0, 'writes': 0}
def path_metadata(name):
    row = {'path': name, 'readable': os.access(name, os.R_OK), 'writable': os.access(name, os.W_OK), 'executable': os.access(name, os.X_OK)}
    try:
        row['exists'] = Path(name).exists()
    except OSError as exc:
        row.update(exists=None, stat_error=type(exc).__name__)
    return row

for name in ('/etc/exim/exim.conf', '/etc/exim.conf', '/etc/exim4/exim4.conf', '/etc/exim4/exim4.conf.template'):
    path = Path(name)
    row = path_metadata(name)
    if row['exists'] and row['readable']:
        try:
            with path.open() as stream:
                row['dkim_options'] = dkim_options(stream.read(2_000_000))
        except OSError as exc:
            row['error'] = type(exc).__name__
    dkim['files'].append(row)
for binary in ('/usr/sbin/exim', '/usr/sbin/exim4'):
    if not os.access(binary, os.X_OK):
        continue
    try:
        proc = subprocess.run([binary, '-bP', 'transport', 'remote_smtp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=8)
        dkim['transport'] = {'exit': proc.returncode, 'dkim_options': dkim_options(proc.stdout), 'error': safe(proc.stderr[:500])}
    except (OSError, subprocess.TimeoutExpired) as exc:
        dkim['transport'] = {'error': type(exc).__name__}
    break
dkim['panel_cli'] = [path_metadata(p) for p in ('/usr/local/mgr5/sbin/mgrctl', '/usr/local/mgr5/bin/core')]
result['dkim_signing_readonly'] = dkim
print(json.dumps(result, ensure_ascii=False))
