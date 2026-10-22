"""Check narrow config edits, mandatory private backups, drift and rollback."""
import hashlib, json, os, pathlib, subprocess, tempfile

SCRIPT=pathlib.Path(__file__).with_name('nsp_admin_email.php')
BASE="""<?php
define('ADMIN_EMAIL', 'marzhavbetone@yandex.ru');
define('SITE_URL', 'https://nastoronepodryadchika.ru');
define('YOOKASSA_SHOP_ID', '1502106');
define('DELIVERY_TTL_SECONDS', 3600);
define('SYNTHETIC_SECRET', 'never-print-this-fixture');
// products-marzhavbetone is a preserved compatibility path.
"""

def check(name, *, change=None, action='apply', expected_ok=False, backup_kind='valid', bad_hash=False):
    with tempfile.TemporaryDirectory() as d:
        root=pathlib.Path(d); site=root/'site'; site.mkdir(); config=site/'config.php'
        text=change(BASE) if change else BASE; data=text.encode(); config.write_bytes(data); config.chmod(0o640)
        backup=(site if backup_kind=='public' else root)/'backup.php'
        backup.write_bytes(b'wrong' if backup_kind=='corrupt' else data); backup.chmod(0o644 if backup_kind=='mode' else 0o600)
        if backup_kind=='missing': backup.unlink()
        digest='0'*64 if bad_hash else hashlib.sha256(data).hexdigest()
        p=subprocess.run(['php',str(SCRIPT),action,str(config),digest,str(backup)],capture_output=True,text=True,timeout=15)
        assert (p.returncode==0)==expected_ok,(name,p.stdout,p.stderr)
        assert 'never-print-this-fixture' not in p.stdout+p.stderr
        if expected_ok:
            receipt=json.loads(p.stdout); assert receipt['non_admin_bytes']=='UNCHANGED'
        expected=data.replace(b'marzhavbetone@yandex.ru',b'nastoronepodryadchika@yandex.ru') if expected_ok and action=='apply' else data
        assert config.read_bytes()==expected,name
        assert config.stat().st_mode&0o777==0o640,name
        assert not list(site.glob('.nsp-admin-*')),name
        return name

done=[
 check('apply-only-one-literal',expected_ok=True),
 check('dry-run-has-no-write',action='dry-run',expected_ok=True,backup_kind='missing'),
 check('source-drift',bad_hash=True),
 check('unknown-mailbox',change=lambda s:s.replace('marzhavbetone@yandex.ru','other@example.invalid')),
 check('duplicate-definition',change=lambda s:s+"define('ADMIN_EMAIL', 'marzhavbetone@yandex.ru');\n"),
 check('public-backup',backup_kind='public'),
 check('backup-corruption',backup_kind='corrupt'),
 check('backup-mode',backup_kind='mode'),
 check('missing-backup',backup_kind='missing'),
 check('wrong-runtime',change=lambda s:s.replace('3600','7200')),
 check('candidate-runtime-refused-before-write',change=lambda s:s+"if (ADMIN_EMAIL === 'nastoronepodryadchika@yandex.ru') { exit(9); }\n"),
 check('double-quoted-literal',change=lambda s:s.replace("define('ADMIN_EMAIL', 'marzhavbetone@yandex.ru');",'define("ADMIN_EMAIL", "marzhavbetone@yandex.ru");'),expected_ok=True),
]
print(json.dumps({'status':'PASS','tests':len(done),'cases':done}))
