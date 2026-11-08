#!/usr/bin/env python3
"""Bounded production HTML-only release through GitHub Secrets; no generic deploy."""
import os,pathlib,subprocess,hashlib,re,sys,datetime,shlex,json
root=pathlib.Path.cwd();files=(root/'tools/nsp_pr719_paths.txt').read_text().splitlines()
assert len(files)==28 and all(f.endswith('.html') and '..' not in f for f in files),files
site=os.environ['SITE_PATH'];host=os.environ['HOST'];user=os.environ['USER'];port=os.environ['SSH_PORT'];apply=os.environ.get('APPLY')=='true'
ssh=['ssh','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=12','-i',str(pathlib.Path.home()/'.ssh/deploy_key'),'-p',port,f'{user}@{host}']
scp=['scp','-q','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-i',str(pathlib.Path.home()/'.ssh/deploy_key'),'-P',port]
def run(cmd,timeout=20,**kw):return subprocess.run(cmd,check=True,timeout=timeout,**kw)
def remote(command,timeout=20):return run(ssh+[command],timeout=timeout,stdout=subprocess.PIPE).stdout
base=pathlib.Path('/tmp/pr719-live');dest=pathlib.Path('/tmp/pr719-candidate');base.mkdir(exist_ok=True);dest.mkdir(exist_ok=True)
original={};candidates={}
for path in files:
    data=remote('cat '+shlex.quote(site+'/'+path),timeout=16)
    original[path]=data
    p=base/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    o=dest/path;o.parent.mkdir(parents=True,exist_ok=True)
    run(['python3','tools/nsp_pr719_prod_patch.py',path,str(p),str(o)],stdout=subprocess.DEVNULL)
    newer=o.read_bytes();candidates[path]=newer
    before=data.decode('utf-8');after=newer.decode('utf-8')
    for pat in [r'data-sku="[^"]*"',r'data-price="[^"]*"',r'href="[^"]*"',r'src="[^"]*"',r'data-product-id="[^"]*"']:
        assert re.findall(pat,before)==re.findall(pat,after),(path,pat)
    assert before!=after,('expected changed',path)
print('PREFLIGHT_PASS: 28/28 live HTML files patched; all SKU/price/href/src attributes unchanged')
cat=candidates['katalog.html'].decode()
from importlib.machinery import SourceFileLoader
patch=SourceFileLoader('nsp_patch','tools/nsp_pr719_prod_patch.py').load_module()
for sku,(_,name,sub) in patch.paid.items():
    match=re.search(r'<article class="product-card"[^>]*>.*?data-sku="'+sku+r'".*?</article>',cat,re.S)
    assert match and name in match.group() and sub in match.group(),('paid catalog',sku)
for name in patch.free.values():assert name in cat,('free catalog',name)
assert 'data-sku="t2"' not in cat and 'data-sku="t3"' not in cat
for sku,(_,name,sub) in patch.paid.items():
    path=next(p for p in files if p.startswith('products/'+sku+'-'))
    page=candidates[path].decode()
    assert '<h1>'+name+'</h1>' in page and sub in page,('paid page',sku)
print('NAME_GATE_PASS: 11/11 paid, 10/10 free, 11/11 subtitles; retired T2/T3 absent')
if not apply:
    print('DRY_RUN_PASS: no remote files changed')
    sys.exit(0)
# Confirm no concurrent modification, then immutable remote backup outside document root.
for path in files:
    assert remote('sha256sum '+shlex.quote(site+'/'+path)).decode().split()[0]==hashlib.sha256(original[path]).hexdigest(),('concurrent update',path)
backup='nsp-pr719-backup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
cmd='mkdir -m 700 -p '+shlex.quote('$HOME/'+backup)
# Do not quote $HOME expansion; backup is a fixed safe filename.
remote('mkdir -m 700 -p "$HOME/'+backup+'"',timeout=20)
for path in files:
    parent=str(pathlib.PurePosixPath(path).parent)
    remote('mkdir -p "$HOME/'+backup+'/'+parent+'" && cp '+shlex.quote(site+'/'+path)+' "$HOME/'+backup+'/'+path+'"',timeout=20)
print('BACKUP_PASS: 28 original files stored outside webroot in',backup)
applied=[]
try:
    for path in files:
        # Optimistic concurrency gate at moment of write.
        assert remote('sha256sum '+shlex.quote(site+'/'+path)).decode().split()[0]==hashlib.sha256(original[path]).hexdigest(),('changed during deploy',path)
        temp=site+'/'+path+'.nsp-pr719-incoming'
        run(scp+[str(dest/path),f'{user}@{host}:'+temp],timeout=25)
        assert remote('sha256sum '+shlex.quote(temp)).decode().split()[0]==hashlib.sha256(candidates[path]).hexdigest(),('stage hash',path)
        remote('mv '+shlex.quote(temp)+' '+shlex.quote(site+'/'+path),timeout=20)
        applied.append(path)
    for path in files:
        assert remote('sha256sum '+shlex.quote(site+'/'+path)).decode().split()[0]==hashlib.sha256(candidates[path]).hexdigest(),('published mismatch',path)
    print('UPLOAD_PASS: 28/28 HTML files updated; SHA-256 match')
except BaseException:
    print('UPLOAD_FAILED: attempting rollback',len(applied),'files',file=sys.stderr)
    for path in reversed(applied):
        try:remote('cp "$HOME/'+backup+'/'+path+'" '+shlex.quote(site+'/'+path))
        except Exception as e:print('ROLLBACK_ERROR',path,type(e).__name__,file=sys.stderr)
    raise
