from pathlib import Path
import json,hashlib,shutil,subprocess,copy,zipfile
from lxml import html
D=Path('/home/denis/projects/nsp-qa22-p11-20261031/publication');T=D/'current-only';B=D/'snapshot';m=json.loads((T/'release.json').read_text());SHA=m['archive_sha256'];H=lambda b:hashlib.sha256(b).hexdigest();checks=[]
def make(name):
 F=T/name;assert not F.exists()
 s=F/'www/nastoronepodryadchika.ru';(s/'products').mkdir(parents=True)
 root=F/'products';src=root/'13-raschet-metrami';src.mkdir(parents=True);orders=F/'orders';delivery=orders/'delivery';delivery.mkdir(parents=True);stage=F/'stage';stage.mkdir()
 for n in list(m['protected'])+list(m['pages']):
  (s/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(B/n,s/n)
 (s/'index.html').write_text('ISOLATED')
 (s/'config.php').write_text('<?php define("ORDERS_DIR",'+json.dumps(str(orders))+');define("PRODUCTS_DIR",'+json.dumps(str(root))+');define("SITE_URL","https://example.invalid");define("ADMIN_EMAIL","qa@example.invalid");')
 before={}
 for n in m['old_members']:
  raw=('FIXTURE OLD '+n).encode();(src/n).write_bytes(raw);before[n]=H(raw)
 (delivery/'13-raschet-metrami.zip').write_bytes(b'OLD CACHE')
 shutil.copyfile('/home/denis/projects/nsp-qa13-20261024/owner-layout-review-20261029/QA13_P1_V1_18_FILES_NONRELEASE_20261029.zip',root/'P1-v1-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa14-20261024/p2-v13-publication-20261029/current-only/current.zip',root/'P2-v13-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa15-p3-20261030/publication/current-only/current.zip',root/'P3-v1-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa16-p4-20261030/publication/current-only/current.zip',root/'P4-v1-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa17-p5-20261030/publication/current-only/current.zip',root/'P5-v1-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa18-p7-20261030/publication/current-only/current.zip',root/'P7-v2-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa20-p9-20261030/publication/current-only/current.zip',root/'P9-v1-current.zip')
 shutil.copyfile('/home/denis/projects/nsp-qa21-p10-20261031/publication/current-only/current.zip',root/'P10-v1-current.zip')
 shutil.copytree(T/'pages',stage/'pages');shutil.copyfile(T/'current.zip',stage/'current.zip')
 mm=copy.deepcopy(m);mm['old_members']=before;(stage/'release.json').write_text(json.dumps(mm))
 return F,s,root,src,orders,delivery,stage,before
def task(mode,s,st,success=True):
 r=subprocess.run(['php',str(T/'publish.php'),mode,str(s),str(st)],capture_output=True,timeout=10)
 if success and r.returncode:raise RuntimeError(mode+': '+r.stderr.decode())
 if not success:assert r.returncode!=0;return r.stderr.decode()
 return r.stdout
def php(b):
 r=subprocess.run(['php'],input=b.encode(),capture_output=True,timeout=10)
 if r.returncode:raise RuntimeError(r.stderr.decode())
 return r.stdout
F,s,root,src,orders,delivery,st,before=make('fixture')
master=root/'P11-v1-current.zip';master.write_bytes(b'UNKNOWN EXISTING MASTER')
assert 'MASTER_ALREADY_PRESENT'in task('preflight',s,st,False)
assert {p.name:H(p.read_bytes())for p in src.iterdir()}==before;master.unlink();checks.append('unknown_existing_master_blocks_before_mutation')
assert json.loads(task('preflight',s,st))['status']=='PREFLIGHT_PASS'
assert json.loads(task('apply',s,st))['status']=='P11_APPLIED_PENDING_FRESH_VERIFY'
assert json.loads(task('verify',s,st))['builder_exact_archive']
assert H(task('read-current',s,st))==SHA;checks.append('transaction_fresh_runtime_readback_exact')
setup='<?php require '+json.dumps(str(s/'config.php'))+';require '+json.dumps(str(s/'products-config.php'))+';'
cache=delivery/'13-raschet-metrami.zip';cache.unlink()
assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("p11"));').decode()==SHA;checks.append('missing_cache_restores_exact_archive')
cache.write_bytes(b'CORRUPTED CACHE')
assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("p11"));').decode()==SHA;checks.append('corrupted_cache_restores_exact_archive')
master.write_bytes(b'CORRUPTED MASTER')
assert php(setup+'echo mvb_build_product_zip("p11")===null?"PASS":"FAIL";')==b'PASS';checks.append('corrupted_master_rejected')
shutil.copyfile(T/'current.zip',master)
for sku,sha in [('p1','99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada'),('p2','42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'),('p3','54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b'),('p4','a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea'),('p5','1a0ab501a008c9cae1b1baaaa6570d1123291630ac8ecff1db74fad411431286'),('p7','99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24'),('p9', '34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9'),('p10', '90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594')]:
 assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("'+sku+'"));').decode()==sha;checks.append(sku+'_delivery_unchanged')
oid='order_20261030_0003_nspqa'
o={'id':oid,'status':'paid','items':[{'sku':'p11'}]}
b=php(setup+'$o=json_decode('+json.dumps(json.dumps(o))+',true);$a=mvb_prepare_delivery($o);$expiry=$o["delivery"]["expires_at"];$token=$o["delivery"]["token"];$b=mvb_prepare_delivery($o);if($a["missing"]||$b["missing"]||$expiry!==$o["delivery"]["expires_at"]||$token!==$o["delivery"]["token"]||strtotime($expiry)-strtotime($o["delivery"]["created_at"])!==3600)exit(2);echo json_encode($o);')
order=json.loads(b);checks.append('delivery_ttl_3600_and_repeat_not_extended')
for kind,status in [('current',200),('boundary',410),('past',410),('wrong_token',403)]:
 expiry='$o["delivery"]["expires_at"]=date("c",time()'+('-1'if kind=='past'else'')+');'if kind in ['boundary','past']else''
 script='<?php $o=json_decode('+json.dumps(json.dumps(order))+',true);'+expiry+'file_put_contents('+json.dumps(str(orders/(oid+'.json')))+',json_encode($o));$_GET=["o"=>"'+oid+'","t"=>'+json.dumps('wrong'if kind=='wrong_token'else order['delivery']['token'])+',"f"=>"p11"];register_shutdown_function(function(){file_put_contents('+json.dumps(str(F/'http.json'))+',json_encode(["http"=>http_response_code()?:200]));});require '+json.dumps(str(s/'download.php'))+';'
 body=php(script);assert json.loads((F/'http.json').read_text())['http']==status
 if status==200:assert H(body)==SHA
 checks.append('download_'+kind+'_'+str(status))
assert json.loads(task('finalize',s,st))['previous_product_files_retained']is False
assert not (st/'rollback').exists();assert set(p.name for p in src.iterdir())=={r['name']for r in m['members']}
assert all(H((s/n).read_bytes())==sha for n,sha in m['protected'].items());checks.append('current_only_cleanup_and_protected_handlers')
F2,s2,r2,src2,o2,d2,st2,before2=make('rollback-fixture')
task('preflight',s2,st2);task('apply',s2,st2);assert json.loads(task('rollback',s2,st2))['status']=='ROLLBACK_VERIFIED'
assert {p.name:H(p.read_bytes())for p in src2.iterdir()}==before2
assert (d2/'13-raschet-metrami.zip').read_bytes()==b'OLD CACHE'
assert all(H((s2/n).read_bytes())==r['before']for n,r in m['pages'].items());checks.append('rollback_restores_source_config_pages_and_cache')
for n in [next(n for n in m['pages']if n.startswith('products/')),'katalog.html']:
 doc=html.fromstring((T/'pages'/n).read_bytes())
 for scripttag in doc.xpath('//script[@type="application/ld+json"]'):json.loads(scripttag.text)
 if n.startswith('products/'):assert set(doc.xpath('//code/text()'))=={r['name']for r in m['members']}
checks.append('HTML_exact_composition_and_valid_JSONLD')
receipt={'status':'P11_SCOPED_PUBLICATION_ACCEPTANCE_PASS','check_count':len(checks),'checks':checks,'archive_sha256':SHA,'files':10,'release_manifest_sha256':H((T/'release.json').read_bytes()),'production_modified':False,'real_payment_performed':False}
(T/'LOCAL_TEST_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))
