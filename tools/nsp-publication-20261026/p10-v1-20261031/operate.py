#!/usr/bin/env python3
"""Existing targeted workflow: current P10 files only; payment code unchanged."""
from pathlib import Path
import base64,hashlib,io,json,os,shlex,subprocess,sys,tarfile,time,urllib.request,urllib.parse,zipfile
ROOT=Path(__file__).resolve().parent;E=Path('/tmp/nsp-final-evidence');E.mkdir(exist_ok=True)
action=sys.argv[1];assert action in ('p10-snapshot','p10-publish')
request=json.loads(Path('tools/nsp-final/request.json').read_text())
SHA='90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594'
assert request['sku']=='p10'and request['edition']=='P10-review-v1'and request['approved_archive_sha256']==SHA
port=os.environ['PORT'];assert port.isdigit()
common=['-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2']
remote=os.environ['SSH_USER']+'@'+os.environ['HOST'];ssh=['ssh','-p',port,*common,remote];scp=['scp','-P',port,*common]
def call(args,data=None,timeout=45):
 r=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-1800:]+r.stdout.decode(errors='replace')[-1000:])
 return r.stdout
H=lambda b:hashlib.sha256(b).hexdigest()
if action=='p10-snapshot':
 raw=call(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],(ROOT/'inspect.php').read_bytes())
 snapshot=json.loads(raw);assert snapshot['read_only'] is True;(E/'p10-production-snapshot.json').write_bytes(raw)
 out=E/'p10-before';out.mkdir(exist_ok=True)
 for name,row in snapshot['files'].items():
  data=base64.b64decode(row['base64']);assert H(data)==row['sha256']and len(data)==row['bytes']
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 print(json.dumps({'status':'P10_SNAPSHOT_PASS_NO_PRODUCTION_WRITES','files':len(snapshot['files'])}));sys.exit(0)

assert request['delivery_policy']=='NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'
assert request['method']=='EXACT_CURRENT_ARCHIVE_EXISTING_BUILDER'
assert '3600' in Path('docs/NSP_DELIVERY_POLICY.md').read_text()
C=ROOT/'current-only';manifest=json.loads((C/'release.json').read_text())
assert H((C/'release.json').read_bytes())==request['release_manifest_sha256']
assert manifest['archive_sha256']==SHA
# Exact source bytes and current explicit owner authorization.
owner=json.loads((ROOT/'OWNER_APPROVAL.json').read_text())
assert owner['owner_product_acceptance']=='APPROVED'and owner['release_permission']=='ALLOW_EXACT_EDITION_ONLY'and owner['archive_sha256']==SHA
ref='8335d9e7d241d9ccdcc75db7d134cbed703600a6'
call(['git','fetch','--no-tags','--depth=1','origin',ref],timeout=60)
source='tools/nsp-qa21-p10-20261031/review-v1/output/P10_Pretenziya_k_podryadchiku_v1.zip'
archive=call(['git','show',ref+':'+source],timeout=20);assert H(archive)==SHA
with zipfile.ZipFile(io.BytesIO(archive))as z:
 assert z.testzip()is None and len(z.namelist())==10
 assert {n:H(z.read(n))for n in z.namelist()}=={r['name']:r['sha256']for r in manifest['members']}
local=json.loads((C/'LOCAL_TEST_RECEIPT.json').read_text());assert local['status']=='P10_SCOPED_PUBLICATION_ACCEPTANCE_PASS'and local['archive_sha256']==SHA
(E/'p10-source-gate.json').write_text(json.dumps({'status':'EXACT_APPROVED_SOURCE_VERIFIED','archive_sha256':SHA,'files':10})+'\n')
(C/'current.zip').write_bytes(archive)
call(['php','-l',str(C/'publish.php')],timeout=8)
run=os.environ['GITHUB_RUN_ID'];attempt=os.environ['GITHUB_RUN_ATTEMPT'];assert run.isdigit()and attempt.isdigit()
relative='nsp-migration-private/p10-current-'+run+'-'+attempt;stage='"$HOME/'+relative+'"';site='"$HOME/www/nastoronepodryadchika.ru"'
pack=E/'p10-current-upload.tar.gz'
with tarfile.open(pack,'w:gz')as t:
 for name in ['publish.php','release.json','current.zip','pages/products/p10-otvet-na-pretenziyu.html','pages/katalog.html','pages/products-config.php']:
  assert (C/name).is_file();t.add(C/name,arcname=name)
call(ssh+['umask 077; test -d "$HOME/nsp-migration-private" && mkdir '+stage],timeout=25)
call(scp+[str(pack),remote+':'+relative+'/upload.tar.gz'],timeout=45)
call(ssh+['umask 077; cd '+stage+' && tar -xzf upload.tar.gz && chmod -R go-rwx .'],timeout=25)
def transaction(mode):
 return call(ssh+['php '+stage+'/publish.php '+shlex.quote(mode)+' '+site+' '+stage],timeout=35)
(E/'p10-preflight.json').write_bytes(transaction('preflight'))
started=False;verified=False
try:
 started=True;(E/'p10-apply.json').write_bytes(transaction('apply'))
 # Retrieve the actual current cache through the live existing server builder.
 actual=transaction('read-current');assert H(actual)==SHA and actual==archive
 with zipfile.ZipFile(io.BytesIO(actual))as z:
  assert z.testzip()is None and len(z.namelist())==10 and len(set(z.namelist()))==10
  for member in manifest['members']:assert H(z.read(member['name']))==member['sha256']
 (E/'p10-current-delivered.zip').write_bytes(actual)
 http=[]
 for name,row in manifest['pages'].items():
  if name.endswith('.php'):continue
  url='https://nastoronepodryadchika.ru/'+name+'?nsp_p10_release='+run
  req=urllib.request.Request(url,headers={'Accept-Encoding':'identity','Cache-Control':'no-cache','User-Agent':'NSP-P10-release-check/1.0'})
  with urllib.request.urlopen(req,timeout=15)as response:
   assert response.status==200 and urllib.parse.urlsplit(response.url).hostname=='nastoronepodryadchika.ru'
   b=response.read(200001);assert H(b)==row['after'],name+' HTTPS content differs'
  http.append({'path':name,'status':200,'sha256':H(b)})
 (E/'p10-https.json').write_text(json.dumps(http,indent=2)+'\n')
 current=json.loads(transaction('verify'));assert current['builder_exact_archive']and current['ttl_seconds']==3600
 verified=True
except BaseException:
 if started and not verified:
  try:(E/'p10-rollback.json').write_bytes(transaction('rollback'))
  except BaseException as error:(E/'p10-rollback-error.txt').write_text(str(error));raise
 raise
# Only after all checks: remove temporary old P10 files/cache. Never historical retention.
final=json.loads(transaction('finalize'));assert final['previous_product_files_retained']is False and final['previous_cache_retained']is False
(E/'p10-finalize.json').write_text(json.dumps(final,indent=2)+'\n')
receipt={'status':'P10_REVIEW_V1_DEPLOYED_CURRENT_ARCHIVE_AND_HTTPS_VERIFIED','edition':'P10-review-v1','archive_sha256':SHA,'file_count':10,'source_gate':'PASS','actual_server_builder_bytes':'EXACT_MATCH','public_pages':http,'ttl_seconds':3600,'price_kopeks':1790000,'old_product_files_retained':False,'old_cache_retained':False,'payment_and_download_unchanged':True,'config_change':'extend existing exact-current archive branch to P10; P1, P2 and P3 preserved','real_payment_tested':False,'run_id':run,'commit':os.environ['GITHUB_SHA'],'owner_permission':'APPROVED','scope':'P10 current source/master/cache and page/catalog; existing current-archive builder extended to P10'}
(E/'P10_PUBLICATION_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))
