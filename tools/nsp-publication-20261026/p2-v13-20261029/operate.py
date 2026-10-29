#!/usr/bin/env python3
"""Approved P2 v13 through the EXISTING targeted GitHub Actions SSH route."""
from pathlib import Path
import base64, hashlib, io, json, os, re, subprocess, sys, tarfile, time, urllib.request, zipfile

ROOT = Path(__file__).resolve().parent
EVIDENCE = Path('/tmp/nsp-final-evidence')
EVIDENCE.mkdir(exist_ok=True)
EXPECTED = '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'
COMMIT = '46005303b5b0f4ca27d9742d23cb9456669034e5'
APPROVAL = '29a73bea7783c52924a3b85c4dfbeb563e3e550d'
NAME = 'P2-NSP-v13-13-files-20261029.zip'
BRANCH = 'tools/nsp-qa14-20261024/owner-review-v13-20261029/'
BASE_SHA = {
    'products/p2-dopolnitelnye-raboty.html': '92ff966a94c07a152dfaa62d5d6a849142deae41548894550951b119df0f1efe',
    'katalog.html': 'a4346219b8d1c266f25cac8f93787dbebfe2a127b9c5a0c884648b9b5d8cd340',
    'products-config.php': '10739a7aff2a98e676c1e15b3499c64ad82703d0d6a3c6650b3dab751ce70551',
}
sha = lambda b: hashlib.sha256(b).hexdigest()
def command(args, *, data=None, timeout=45):
    r = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if r.returncode: raise RuntimeError('COMMAND_FAILED '+str(args[:2])+' '+r.stderr.decode(errors='replace')[-700:])
    return r.stdout
def exact_replace(s,old,new):
    if s.count(old)!=1: raise ValueError('REPLACEMENT_CARDINALITY '+str(s.count(old))+' '+old[:70])
    return s.replace(old,new,1)
def fetch(url, max_bytes=900000):
    req=urllib.request.Request(url,headers={'User-Agent':'NSP-P2-v13-release','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=18) as r:
        b=r.read(max_bytes+1)
    if len(b)>max_bytes: raise ValueError('SOURCE_TOO_LARGE')
    return b
def git_raw(commit,path):
    return fetch('https://raw.githubusercontent.com/pmgpt12-arch/marzhavbetone.ru/'+commit+'/'+path)
def check_approved_zip():
    approved=git_raw(COMMIT,BRANCH+NAME)
    if sha(approved)!=EXPECTED: raise ValueError('OWNER_ZIP_SHA')
    manifest_raw=git_raw(COMMIT,BRANCH+'REVIEW_MANIFEST.json')
    if sha(manifest_raw)!='0b21feede98c5833cce447ac47c4e648cb51d8178199c2fe16ff6316bded3a96': raise ValueError('OWNER_MANIFEST_SHA')
    m=json.loads(manifest_raw)
    with zipfile.ZipFile(io.BytesIO(approved)) as z:
        if z.testzip() is not None or len(z.namelist())!=13 or len(set(z.namelist()))!=13: raise ValueError('ZIP_STRUCTURE')
        if {x['name']:x['sha256'] for x in m['members']} != {n:sha(z.read(n)) for n in z.namelist()}: raise ValueError('ZIP_MEMBER_SHAS')
    owner=json.loads(git_raw(APPROVAL,BRANCH+'OWNER_PUBLICATION_APPROVAL_20261029.json'))
    if owner['owner_product_acceptance']!='APPROVED' or owner['release_permission']!='ALLOW_EXACT_EDITION_ONLY' or owner['archive_sha256']!=EXPECTED: raise ValueError('OWNER_PERMISSION')
    return approved,m

action=sys.argv[1]
if action not in ('p2-snapshot','p2-publish'): raise ValueError('ACTION')
request=json.loads(Path('tools/nsp-final/request.json').read_text())
assert request['sku']=='p2' and request['edition']=='P2-v13' and request['approved_archive_sha256']==EXPECTED
port=os.environ['PORT']
assert port.isdigit()
remote=os.environ['SSH_USER']+'@'+os.environ['HOST']
opts=['-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2']
ssh=['ssh','-p',port,*opts,remote]
def remote_exec(s,data=None,timeout=65):
    return command(ssh+[s],data=data,timeout=timeout)
def snapshot():
    raw=remote_exec('php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"',(ROOT/'inspect.php').read_bytes(),timeout=50)
    x=json.loads(raw)
    if x.get('read_only') is not True: raise ValueError('NOT_READ_ONLY')
    (EVIDENCE/'p2-production-snapshot.json').write_bytes(raw)
    out=EVIDENCE/'p2-before';out.mkdir(exist_ok=True)
    for n,row in x['files'].items():
        b=base64.b64decode(row['base64'])
        if len(b)!=row['bytes'] or sha(b)!=row['sha256']: raise ValueError('SNAPSHOT_SHA_'+n)
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    return x
if action=='p2-snapshot':
    s=snapshot()
    print(json.dumps({'status':'P2_SNAPSHOT_PASS_NO_PRODUCTION_WRITES','files':{n:{'sha256':r['sha256'],'bytes':r['bytes']} for n,r in s['files'].items()}},ensure_ascii=False))
    raise SystemExit(0)

# One bounded, owner-authorized P2-only publication. No changes to unrelated SKUs or payment/download handlers.
approved,member_manifest=check_approved_zip()
s=snapshot()
for n,expected in BASE_SHA.items():
    if s['files'][n]['sha256']!=expected: raise ValueError('PRODUCTION_BASELINE_DRIFT '+n)
before=EVIDENCE/'p2-before'
page=(ROOT/'materials/P2_PRODUCT_PAGE.html').read_bytes()
if sha(page)!='f91cca6b2e3db1a3a22555ffdf14e08f670790de8a5fa711b93af65126144242': raise ValueError('P2_PAGE_NOT_REVIEWED')
card=(ROOT/'materials/P2_CATALOG_CARD.html').read_text().strip()
if sha((ROOT/'materials/P2_CATALOG_CARD.html').read_bytes())!='4dc0d6a3783722abcadc802a9bdbab31470906367b615d121165194a70a61cda': raise ValueError('P2_CARD_NOT_REVIEWED')
names=re.findall(r'<code[^>]*>([^<]+)</code>',page.decode())
if len(names)!=13 or set(names)!={r['name'] for r in member_manifest['members']}: raise ValueError('PAGE_LIST')
catalog=(before/'katalog.html').read_text()
card_pattern=r'<article class="product-card"><div class="product-number">P2</div>.*?</article>'
catalog,n=re.subn(card_pattern,lambda m:card,catalog,flags=re.S)
if n!=1:raise ValueError('P2_CARD_COUNT')
description_pattern=r'("name"\s*:\s*"Система оформления и получения оплаты за дополнительные работы"\s*,\s*"description"\s*:\s*")([^"]+)(")'
matches=list(re.finditer(description_pattern,catalog,re.S))
if len(matches)!=1 or '15 файлов, включая инструкции.' not in matches[0][2]: raise ValueError('P2_CATALOG_JSONLD')
m=matches[0]
catalog=catalog[:m.start(2)]+m[2].replace('15 файлов, включая инструкции.','13 файлов: 8 DOCX, 2 XLSX и 3 PDF.')+catalog[m.end(2):]
original=(before/'products-config.php').read_text()
needle="    $zipPath = DELIVERY_DIR . '/' . $catalog[$sku]['zip'];\n"
branch="""    // P2 v13: only the owner-approved current archive. No historical versions.
    if ($sku === 'p2') {
        $approved = '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da';
        $master = PRODUCTS_DIR . '/P2-v13-current.zip';
        if (!is_file($master) || !hash_equals($approved,(string)@hash_file('sha256',$master))) return null;
        if (is_file($zipPath) && hash_equals($approved,(string)@hash_file('sha256',$zipPath))) return $zipPath;
        $tmp = @tempnam(DELIVERY_DIR,'.p2-current-');
        if ($tmp === false) return null;
        try {
            if (!copy($master,$tmp) || !hash_equals($approved,(string)@hash_file('sha256',$tmp)) || !chmod($tmp,0644) || !@rename($tmp,$zipPath)) return null;
            return $zipPath;
        } finally { if (is_file($tmp)) @unlink($tmp); }
    }
"""
# Only the named function receives this patch.
anchor=original.index('function mvb_build_product_zip(string $sku): ?string')
head=original[:anchor];body=original[anchor:]
body=exact_replace(body,needle,needle+branch)
config=head+body
if original.replace('','',1)!=original: raise ValueError('INTERNAL_ASSERT')
candidate={
    'products/p2-dopolnitelnye-raboty.html':page,
    'katalog.html':catalog.encode(),
    'products-config.php':config.encode()
}
if len(candidate)!=3:raise ValueError('FILE_SCOPE')
if sha(candidate['products-config.php'])==BASE_SHA['products-config.php']: raise ValueError('NO_CONFIG_PATCH')
work=EVIDENCE/'p2-publish-stage';work.mkdir(exist_ok=True)
for n,b in candidate.items():
    p=work/'candidate'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
command(['php','-l',str(work/'candidate/products-config.php')],timeout=8)
command(['php','-l',str(ROOT/'release.php')],timeout=8)
manifest={
    'sku':'p2','edition':'P2-v13','archive_sha256':EXPECTED,
    'files':{n:{'before':BASE_SHA[n],'after':sha(b)} for n,b in candidate.items()},
    'members':member_manifest['members'],
    'owner_approval_commit':APPROVAL
}
(work/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(work/NAME).write_bytes(approved)
(work/'release.php').write_bytes((ROOT/'release.php').read_bytes())
stage='$HOME/nsp-migration-private/p2-v13-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
remote_exec('test -d "$HOME/nsp-migration-private" && mkdir "'+stage+'"',timeout=18)
tarfile_name=EVIDENCE/'p2-release-stage.tar'
with tarfile.open(tarfile_name,'w') as tf:
    for p in [work/'manifest.json',work/NAME,work/'release.php',*[(work/'candidate'/n) for n in candidate]]:
        tf.add(p,arcname=str(p.relative_to(work)))
scp=['scp','-P',port,*opts]
command(scp+[str(tarfile_name),remote+':nsp-migration-private/p2-v13-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']+'/stage.tar'],timeout=65)
remote_exec('cd "'+stage+'" && tar -xf stage.tar && chmod 600 manifest.json release.php '+NAME+' && chmod -R go-rwx candidate',timeout=20)
site='"$HOME/www/nastoronepodryadchika.ru"'
def task(mode,timeout=55):
    cmd='php "'+stage+'/release.php" '+mode+' '+site+' "'+stage+'"'
    output=remote_exec(cmd,timeout=timeout)
    (EVIDENCE/('p2-'+mode+'.json')).write_bytes(output)
    val=json.loads(output)
    if not val.get('status','').endswith('_PASS'):raise RuntimeError('P2_GATE_'+mode)
    return val
task('preflight')
print('P2_DRY_RUN_VERIFIED',flush=True)
applied=False
try:
    applied=True  # rollback even if apply fails after the first atomic write
    task('apply',timeout=65)
    task('verify',timeout=45)
    for n in ('products/p2-dopolnitelnye-raboty.html','katalog.html'):
        url='https://nastoronepodryadchika.ru/'+n+'?p2_v13='+os.environ['GITHUB_RUN_ID']
        live=fetch(url,1000000)
        if live!=candidate[n]:raise RuntimeError('PUBLIC_HTTPS_MISMATCH '+n)
    receipt={'status':'P2_V13_PUBLICATION_VERIFIED','edition':'P2-v13','archive_sha256':EXPECTED,'members':13,'ttl_seconds':3600,'https_files':2,'other_skus_modified':False,'paid_checkout_not_run':True}
    (EVIDENCE/'p2-live-readback.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False),flush=True)
except BaseException:
    if applied:
        try: task('rollback',timeout=65);print('P2_ROLLBACK_PASS',flush=True)
        except BaseException as exc:print('P2_ROLLBACK_FAILED '+str(exc)[:300],flush=True)
    raise
