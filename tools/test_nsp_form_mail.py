"""Exercise actual handlers with an offline sendmail capture and synthetic inputs."""
from pathlib import Path
import email, email.header, json, os, shutil, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as d:
    base=Path(d); site=base/'nastoronepodryadchika.ru'; site.mkdir(); backup=base/'private';backup.mkdir(mode=0o700)
    # Reconstruct the frozen production versions from only the approved edits.
    for name in ['contact.php','lead.php']:
        source=(ROOT/name).read_text().replace('nastoronepodryadchika@yandex.ru','marzhavbetone@yandex.ru').replace('Новый заказ с nastoronepodryadchika.ru','Новый заказ с marzhavbetone.ru')
        (site/name).write_text(source);(site/name).chmod(0o644)
    (site/'protected.php').write_text('<?php /* synthetic protected fixture */')
    before={p.name:p.read_bytes() for p in site.glob('*.php')}
    def run_patch(action,ok=True):
        p=subprocess.run(['php',str(ROOT/'tools/nsp_form_mail.php'),action,str(site),str(backup)],capture_output=True,text=True,timeout=15)
        assert (p.returncode==0)==ok,(action,p.stdout,p.stderr)
        if ok:return json.loads(p.stdout)
    assert run_patch('dry-run')['public_writes']==0
    assert {p.name:p.read_bytes() for p in site.glob('*.php')}==before
    receipt=run_patch('apply');assert receipt['all_other_php']=='UNCHANGED'
    assert (site/'protected.php').read_bytes()==before['protected.php']
    for name in ['contact.php','lead.php']:
        assert (site/name).read_bytes()==(ROOT/name).read_bytes()
    run_patch('apply',False)  # A repeated action rejects the now-different source.
    # A local fake sendmail consumes the bytes; it has no network implementation.
    capture=base/'mail.txt';fake=base/'capture.py'
    fake.write_text('import pathlib,sys\npathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())\n')
    shutil.copy(ROOT/'mvb_funnel.php',site/'mvb_funnel.php')
    shutil.copytree(ROOT/'taxonomy',site/'taxonomy')
    env=os.environ.copy();env['MVB_FUNNEL_OUTBOX']=str(base/'outbox')
    code='$_SERVER["REQUEST_METHOD"]=$argv[1]; $_POST=json_decode($argv[2],true); require $argv[3];'
    cases=0
    def invoke(handler,fields,method='POST'):
        global cases
        capture.unlink(missing_ok=True)
        p=subprocess.run(['php','-d',f'sendmail_path=python3 {fake} {capture}','-r',code,method,json.dumps(fields),str(site/handler)],capture_output=True,text=True,timeout=10,env=env)
        assert p.returncode==0,(handler,p.stderr)
        response=json.loads(p.stdout); message=email.message_from_bytes(capture.read_bytes()) if capture.exists() else None
        cases+=1;return response,message
    for handler in ['contact.php','lead.php']:
        assert invoke(handler,{})[0]['ok'] is False
        assert invoke(handler,{},'GET')[1] is None
    response,msg=invoke('contact.php',{'product':'Synthetic object','contact':'test@example.invalid','consent':'yes'})
    assert response['ok'] and msg['To']=='nastoronepodryadchika@yandex.ru'
    assert msg['Reply-To']=='nastoronepodryadchika@yandex.ru' and msg['From']=='site@marzhavbetone.ru'
    subject=str(email.header.make_header(email.header.decode_header(msg['Subject'])))
    assert subject=='Новый заказ с nastoronepodryadchika.ru'
    for key in ['checklist','dengi','dop-raboty','vozvrat-ks','uderzhaniya','dogovor','bankrotstvo','avans','raschet-metrami','ispolnitelnaya-dokumentaciya','akt-skrytyh-rabot']:
        response,msg=invoke('lead.php',{'name':'Synthetic user','contact':'test@example.invalid','consent':'yes','material':key})
        expected='/downloads/checklist-zakrytiya-rabot.pdf' if key=='checklist' else '/downloads/'+key+'.zip'
        assert response['ok'] and response['download']==expected
        assert msg['To']=='nastoronepodryadchika@yandex.ru' and msg['From']=='site@marzhavbetone.ru'
    print(json.dumps({'status':'PASS','handler_cases':cases,'transaction_cases':3,'real_messages_sent':0,'free_routes_verified':11,'sender':'UNCHANGED'}))
