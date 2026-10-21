#!/usr/bin/env python3
"""One explicit static release, with source hashes, private backups and rollback."""
import concurrent.futures, hashlib, json, os, re, shlex, subprocess, sys, tarfile, time
from pathlib import Path
import urllib.request, urllib.parse
from validate import ROOT, validate

EVIDENCE=Path('/tmp/nsp-final-evidence'); EVIDENCE.mkdir(exist_ok=True)
def call(args,*,data=None,timeout=60):
    p=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode: raise RuntimeError(p.stderr.decode(errors='replace')[-3000:]+p.stdout.decode(errors='replace')[-1500:])
    return p.stdout

def main(action):
    assert action in ['dry-run','publish']
    validation=validate(); (EVIDENCE/'source-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    call(['php','-l','tools/nsp-final/transaction.php'])
    call(['python3','tools/nsp-final/test_transaction.py'])
    call(['node','--check','app.js'])
    (EVIDENCE/'email-checkout.json').write_bytes(call(['python3','tools/nsp-ui-audit-20261021/test_email_checkout.py']))
    call(['sh','-n','tools/nsp_backup_config.sh'])
    run=os.environ['GITHUB_RUN_ID']; attempt=os.environ['GITHUB_RUN_ATTEMPT']; assert run.isdigit() and attempt.isdigit()
    port=os.environ['PORT']; host=os.environ['HOST']; user=os.environ['SSH_USER']; assert port.isdigit()
    common=['-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3']
    ssh=['ssh','-p',port,*common,user+'@'+host]
    scp=['scp','-P',port,*common]
    relative='nsp-migration-private/final-'+run+'-'+attempt
    remote_dir='"$HOME/'+relative+'"'
    site='"$HOME/www/nastoronepodryadchika.ru"'
    manifest=json.loads((ROOT/'tools/nsp-final/manifest.json').read_text())
    archive=Path('/tmp/nsp-final-candidate.tar')
    with tarfile.open(archive,'w') as tar:
        tar.add(ROOT/'tools/nsp-final/manifest.json',arcname='manifest.json')
        tar.add(ROOT/'tools/nsp-final/transaction.php',arcname='transaction.php')
        for row in manifest: tar.add(ROOT/row['path'],arcname='candidate/'+row['path'])
    # Only a new private stage is written before the public dry-run.
    call(ssh+['umask 077; test -d "$HOME/nsp-migration-private" && mkdir '+remote_dir])
    call(scp+[str(archive),user+'@'+host+':'+relative+'/candidate.tar'],timeout=90)
    call(ssh+['umask 077; cd '+remote_dir+' && tar -xf candidate.tar && chmod -R go-rwx .'])
    def transaction(mode):
        return call(ssh+['php '+remote_dir+'/transaction.php '+shlex.quote(mode)+' '+site+' '+remote_dir],timeout=90)
    plan=transaction('dry-run'); (EVIDENCE/'dry-run.json').write_bytes(plan); print(plan.decode().strip())
    if action=='dry-run': return
    backups=[]
    for _ in range(2):
        receipt=call(ssh+['sh -s -- '+shlex.quote(run)+' '+shlex.quote(attempt)],data=(ROOT/'tools/nsp_backup_config.sh').read_bytes())
        backups.append(receipt.decode())
    names=[re.search(r'CONFIG_BACKUP_UNIQUE=(.+)',b)[1] for b in backups]
    assert len(set(names))==2,'CONFIG_BACKUPS_NOT_UNIQUE'
    (EVIDENCE/'backup-receipts.txt').write_text('\n'.join(backups))
    rollback_needed=False
    try:
        rollback_needed=True
        (EVIDENCE/'apply.json').write_bytes(transaction('apply'))
        # Exact HTTPS bytes for every changed file and the effective JS endpoint.
        paths=[r['path'] for r in manifest]
        deadline=time.monotonic()+180
        def inspect(path):
            assert time.monotonic()<deadline, 'HTTP_BUDGET'
            url='https://nastoronepodryadchika.ru/'+path+'?nsp_final='+run
            req=urllib.request.Request(url,headers={'User-Agent':'NSP-Final-Cutover-QA/1.0','Accept-Encoding':'identity','Cache-Control':'no-cache'})
            with urllib.request.urlopen(req,timeout=15) as response:
                assert response.status==200 and urllib.parse.urlsplit(response.url).hostname=='nastoronepodryadchika.ru','HTTP_OR_REDIRECT'
                data=response.read(2000001); assert len(data)<=2000000
            expected=(ROOT/path).read_bytes(); assert data==expected,'HTTPS_BYTES_'+path
            return {'path':path,'status':200,'sha256':hashlib.sha256(data).hexdigest()}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(inspect,paths))
        req=urllib.request.Request('https://nastoronepodryadchika.ru/app-script.php?nsp_final='+run,headers={'Cache-Control':'no-cache'})
        with urllib.request.urlopen(req,timeout=15) as response: assert response.read()==(ROOT/'app.js').read_bytes(),'EFFECTIVE_JS_BYTES'
        (EVIDENCE/'https.json').write_text(json.dumps({'status':'PASS','files':rows,'effective_app_script':'PASS'},indent=2)+'\n')
        (EVIDENCE/'verify.json').write_bytes(transaction('verify'))
        rollback_needed=False
        print('NSP_PUBLICATION=VERIFIED; HTTPS_FILES='+str(len(rows)))
    except BaseException:
        if rollback_needed:
            (EVIDENCE/'rollback.txt').write_bytes(transaction('rollback'))
            print('NSP_PUBLICATION_ROLLBACK=PASS')
        raise

if __name__=='__main__': main(sys.argv[1])
