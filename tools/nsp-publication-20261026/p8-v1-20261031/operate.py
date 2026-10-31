#!/usr/bin/env python3
"""Existing targeted workflow: current P8 files only; payment code unchanged."""
from pathlib import Path
import base64,hashlib,io,json,os,shlex,subprocess,sys,tarfile,time,urllib.request,urllib.parse,zipfile
ROOT=Path(__file__).resolve().parent;E=Path('/tmp/nsp-final-evidence');E.mkdir(exist_ok=True)
action=sys.argv[1];assert action in ('p8-snapshot','p8-preflight','p8-publish')
request=json.loads(Path('tools/nsp-final/request.json').read_text())
SHA='31b4e22e5e3e006b0e1c5a1d40892efb2eff2cc8a582f4baa8cbbb2232e865aa'
assert request['sku']=='p8'and request['edition']=='P8-review-v1'and request['approved_archive_sha256']==SHA
port=os.environ['PORT'];assert port.isdigit()
common=['-i',str(Path.home()/'.ssh/nsp_final_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2']
remote=os.environ['SSH_USER']+'@'+os.environ['HOST'];ssh=['ssh','-p',port,*common,remote];scp=['scp','-P',port,*common]
def call(args,data=None,timeout=45):
 r=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-1800:]+r.stdout.decode(errors='replace')[-1000:])
 return r.stdout
H=lambda b:hashlib.sha256(b).hexdigest()
if action=='p8-snapshot':
 raw=call(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],(ROOT/'inspect.php').read_bytes())
 snapshot=json.loads(raw);assert snapshot['read_only'] is True;(E/'p8-production-snapshot.json').write_bytes(raw)
 out=E/'p8-before';out.mkdir(exist_ok=True)
 for name,row in snapshot['files'].items():
  data=base64.b64decode(row['base64']);assert H(data)==row['sha256']and len(data)==row['bytes']
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 print(json.dumps({'status':'P8_SNAPSHOT_PASS_NO_PRODUCTION_WRITES','files':len(snapshot['files'])}));sys.exit(0)

assert request['delivery_policy']=='NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'
assert request['method']=='EXACT_CURRENT_ARCHIVE_EXISTING_BUILDER'
assert '3600' in Path('docs/NSP_DELIVERY_POLICY.md').read_text()
C=ROOT/'current-only';manifest=json.loads((C/'release.json').read_text())
assert H((C/'release.json').read_bytes())==request['release_manifest_sha256']
assert manifest['archive_sha256']==SHA
# Private runtime snapshot gate: all bytes stay in runner files and private deployment stage.
fresh=json.loads(call(ssh+['php /dev/stdin "$HOME/www/nastoronepodryadchika.ru"'],(ROOT/'inspect.php').read_bytes()))
assert fresh['read_only'] is True and len(fresh['product_locations'])==1
assert {r['name']:r['sha256']for r in fresh['product_locations'][0]['p8_files']}==manifest['old_members']
for n,row in fresh['files'].items():
 expected=manifest['protected'].get(n) or manifest['pages'][n]['before']
 b=base64.b64decode(row['base64']);assert H(b)==row['sha256']==expected
 p=ROOT/'snapshot'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
config=(ROOT/'snapshot/products-config.php').read_text()
old='Система управления авансами и расчётами по договору подряда'
line=next(x for x in config.splitlines()if "if ($sku === 'p2'"in x)
assert "'p8'"not in line
config=config.replace(line,line.replace(') {'," || $sku === 'p8') {"),1)
anchor="            'p13' => ['0b1f777b9fb65952cd219d5e61e6b8500cdcd5f1c0039ceba80e3c8f6e67f955', '/P13-v1-current.zip'],"
assert config.count(anchor)==1
config=config.replace(anchor,anchor+"\n            'p8' => ['"+SHA+"', '/P8-v1-current.zip'],",1)
assert config.count(old)==1
config=config.replace(old,'Требование о досрочном погашении аванса',1)
assert config.count("'p8' => '00-START-HERE.txt'")==1
config=config.replace("'p8' => '00-START-HERE.txt'","'p8' => '00-INSTRUKCIYA.pdf'")
(C/'pages/products-config.php').write_text(config)
assert H((C/'pages/products-config.php').read_bytes())==manifest['pages']['products-config.php']['after']

# Exact source bytes and current explicit owner authorization.
owner=json.loads((ROOT/'OWNER_APPROVAL.json').read_text())
assert owner['owner_product_acceptance']=='APPROVED'and owner['release_permission']=='ALLOW_EXACT_EDITION_ONLY'and owner['archive_sha256']==SHA
ref='20e177bf950161e69248471d7df88970ca547b21'
call(['git','fetch','--no-tags','--depth=1','origin',ref],timeout=60)
source='tools/nsp-qa19-p8-20261030/review-v1/output/P8_Dosrochnoe_pogashenie_avansa_v1.zip'
archive=call(['git','show',ref+':'+source],timeout=20);assert H(archive)==SHA
with zipfile.ZipFile(io.BytesIO(archive))as z:
 assert z.testzip()is None and len(z.namelist())==12
 assert {n:H(z.read(n))for n in z.namelist()}=={r['name']:r['sha256']for r in manifest['members']}

# Isolated PHP delivery regression gate before production writes.
import shutil
(C/'current.zip').write_bytes(archive)
shutil.copytree(ROOT.parent/'p13-v1-20261031/fixtures',ROOT/'fixtures')
priorref='ed26b2e9988ef6137e9c8835d39887d979466957'
call(['git','fetch','--no-tags','--depth=1','origin',priorref],timeout=60)
prior=call(['git','show',priorref+':tools/nsp-publication-20261026/p13-v1-20261031/accepted/P13_Proverka_smety_do_podpisaniya_v1.zip'],timeout=20)
assert H(prior)=='0b1f777b9fb65952cd219d5e61e6b8500cdcd5f1c0039ceba80e3c8f6e67f955'
(ROOT/'fixtures/P13-v1-current.zip').write_bytes(prior)
shutil.copytree(ROOT/'snapshot',ROOT/'test-snapshot',dirs_exist_ok=True)
call(['python3',str(ROOT/'test_publication.py')],timeout=100)
shutil.copyfile(C/'LOCAL_TEST_RECEIPT.json',E/'P8_LOCAL_TEST_RECEIPT.json')
if action=='p8-preflight':
 print((C/'LOCAL_TEST_RECEIPT.json').read_text());sys.exit(0)

local=json.loads((C/'LOCAL_TEST_RECEIPT.json').read_text());assert local['status']=='P8_SCOPED_PUBLICATION_ACCEPTANCE_PASS'and local['archive_sha256']==SHA
(E/'p8-source-gate.json').write_text(json.dumps({'status':'EXACT_APPROVED_SOURCE_VERIFIED','archive_sha256':SHA,'files':12})+'\n')
(C/'current.zip').write_bytes(archive)
call(['php','-l',str(C/'publish.php')],timeout=8)
run=os.environ['GITHUB_RUN_ID'];attempt=os.environ['GITHUB_RUN_ATTEMPT'];assert run.isdigit()and attempt.isdigit()
relative='nsp-migration-private/p8-current-'+run+'-'+attempt;stage='"$HOME/'+relative+'"';site='"$HOME/www/nastoronepodryadchika.ru"'
pack=E/'p8-current-upload.tar.gz'
with tarfile.open(pack,'w:gz')as t:
 for name in ['publish.php','release.json','current.zip','pages/products/p8-avans-po-dogovoru-subpodryada.html','pages/katalog.html','pages/products-config.php']:
  assert (C/name).is_file();t.add(C/name,arcname=name)
call(ssh+['umask 077; test -d "$HOME/nsp-migration-private" && mkdir '+stage],timeout=25)
call(scp+[str(pack),remote+':'+relative+'/upload.tar.gz'],timeout=45)
call(ssh+['umask 077; cd '+stage+' && tar -xzf upload.tar.gz && chmod -R go-rwx .'],timeout=25)
def transaction(mode):
 return call(ssh+['php '+stage+'/publish.php '+shlex.quote(mode)+' '+site+' '+stage],timeout=35)
(E/'p8-preflight.json').write_bytes(transaction('preflight'))
started=False;verified=False
try:
 started=True;(E/'p8-apply.json').write_bytes(transaction('apply'))
 # Retrieve the actual current cache through the live existing server builder.
 actual=transaction('read-current');assert H(actual)==SHA and actual==archive
 with zipfile.ZipFile(io.BytesIO(actual))as z:
  assert z.testzip()is None and len(z.namelist())==12 and len(set(z.namelist()))==12
  for member in manifest['members']:assert H(z.read(member['name']))==member['sha256']
 (E/'p8-current-delivered.zip').write_bytes(actual)
 http=[]
 for name,row in manifest['pages'].items():
  if name.endswith('.php'):continue
  url='https://nastoronepodryadchika.ru/'+name+'?nsp_p8_release='+run
  req=urllib.request.Request(url,headers={'Accept-Encoding':'identity','Cache-Control':'no-cache','User-Agent':'NSP-P8-release-check/1.0'})
  with urllib.request.urlopen(req,timeout=15)as response:
   assert response.status==200 and urllib.parse.urlsplit(response.url).hostname=='nastoronepodryadchika.ru'
   b=response.read(200001);assert H(b)==row['after'],name+' HTTPS content differs'
  http.append({'path':name,'status':200,'sha256':H(b)})
 (E/'p8-https.json').write_text(json.dumps(http,indent=2)+'\n')
 current=json.loads(transaction('verify'));assert current['builder_exact_archive']and current['ttl_seconds']==3600
 verified=True
except BaseException:
 if started and not verified:
  try:(E/'p8-rollback.json').write_bytes(transaction('rollback'))
  except BaseException as error:(E/'p8-rollback-error.txt').write_text(str(error));raise
 raise
# Only after all checks: remove temporary old P8 files/cache. Never historical retention.
final=json.loads(transaction('finalize'));assert final['previous_product_files_retained']is False and final['previous_cache_retained']is False
(E/'p8-finalize.json').write_text(json.dumps(final,indent=2)+'\n')
receipt={'status':'P8_REVIEW_V1_DEPLOYED_CURRENT_ARCHIVE_AND_HTTPS_VERIFIED','edition':'P8-review-v1','archive_sha256':SHA,'file_count':12,'source_gate':'PASS','actual_server_builder_bytes':'EXACT_MATCH','public_pages':http,'ttl_seconds':3600,'price_kopeks':2490000,'old_product_files_retained':False,'old_cache_retained':False,'payment_and_download_unchanged':True,'config_change':'extend existing exact-current archive branch to P8; P1, P2 and P3 preserved','real_payment_tested':False,'run_id':run,'commit':os.environ['GITHUB_SHA'],'owner_permission':'APPROVED','scope':'P8 current source/master/cache and page/catalog; existing current-archive builder extended to P8'}
(E/'P8_PUBLICATION_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))

