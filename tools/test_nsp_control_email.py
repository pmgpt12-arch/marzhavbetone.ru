"""Capture the one-shot PHP mail locally; test no-repeat semantics without a network."""
import email
import json
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    base=Path(directory);site=base/'nastoronepodryadchika.ru';site.mkdir();private=base/'private';private.mkdir(mode=0o700)
    (site/'config.php').write_text("<?php define('SITE_URL','https://nastoronepodryadchika.ru'); define('ADMIN_EMAIL','nastoronepodryadchika@yandex.ru');")
    capture=base/'capture.eml';fake=base/'capture.py';fake.write_text('import sys,pathlib\nwith pathlib.Path(sys.argv[1]).open("ab") as f:f.write(sys.stdin.buffer.read())\n')
    def run(mode):
        p=subprocess.run(['php','-d',f'sendmail_path=python3 {fake} {capture}',str(ROOT/'tools/nsp_control_email.php'),mode,str(site),str(private)],capture_output=True,text=True,timeout=10)
        assert p.returncode==0,(mode,p.stdout,p.stderr)
        return json.loads(p.stdout)
    assert run('dry-run')['mail_attempts']==0 and not list(private.iterdir()) and not capture.exists()
    receipt=run('send');assert receipt['status']=='ACCEPTED_BY_LOCAL_MAIL_TRANSPORT' and receipt['protected_php']=='UNCHANGED'
    raw=capture.read_bytes();message=email.message_from_bytes(raw)
    assert message['From']=='site@nastoronepodryadchika.ru' and message['To']=='nastoronepodryadchika@yandex.ru'
    assert message['Reply-To']=='nastoronepodryadchika@yandex.ru'
    assert message['Message-ID']==receipt['message_id']
    for mode in ['send','inspect']:
        assert run(mode)['status']=='EXISTING_NO_RESEND' and capture.read_bytes()==raw
    assert len(list(private.iterdir()))==1
    assert sorted(p.name for p in site.iterdir())==['config.php']
print(json.dumps({'status':'PASS','real_messages_sent':0,'captured_messages':1,'repeat_and_inspect_no_resend':True}))
