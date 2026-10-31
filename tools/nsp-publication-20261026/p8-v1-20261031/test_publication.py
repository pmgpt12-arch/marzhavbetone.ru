from pathlib import Path
import json,hashlib,shutil,subprocess,copy,zipfile
from html.parser import HTMLParser
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.active=None;self.buf="";self.codes=[];self.scripts=[]
 def handle_starttag(self,tag,attrs):
  if tag=="code"or(tag=="script"and dict(attrs).get("type")=="application/ld+json"):self.active=tag;self.buf=""
 def handle_data(self,data):
  if self.active:self.buf+=data
 def handle_endtag(self,tag):
  if tag==self.active:
   (self.codes if tag=="code"else self.scripts).append(self.buf);self.active=None
D=Path(__file__).resolve().parent;T=D/'current-only';B=D/'test-snapshot';m=json.loads((T/'release.json').read_text());SHA=m['archive_sha256'];H=lambda b:hashlib.sha256(b).hexdigest();checks=[]
def make(name):
 F=T/name;assert not F.exists()
 s=F/'www/nastoronepodryadchika.ru';(s/'products').mkdir(parents=True)
 root=F/'products';src=root/'10-avans-usloviya-i-pribyl';src.mkdir(parents=True);orders=F/'orders';delivery=orders/'delivery';delivery.mkdir(parents=True);stage=F/'stage';stage.mkdir()
 for n in list(m['protected'])+list(m['pages']):
  (s/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(B/n,s/n)
 (s/'index.html').write_text('ISOLATED')
 (s/'config.php').write_text('<?php define("ORDERS_DIR",'+json.dumps(str(orders))+');define("PRODUCTS_DIR",'+json.dumps(str(root))+');define("SITE_URL","https://example.invalid");define("ADMIN_EMAIL","qa@example.invalid");')
 before={}
 for n in m['old_members']:
  raw=('FIXTURE OLD '+n).encode();(src/n).write_bytes(raw);before[n]=H(raw)
 (delivery/'10-avans-usloviya-i-pribyl.zip').write_bytes(b'OLD CACHE')
 for master in (D/'fixtures').glob('*.zip'):shutil.copyfile(master,root/master.name)
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
master=root/'P8-v1-current.zip';master.write_bytes(b'UNKNOWN EXISTING MASTER')
assert 'MASTER_ALREADY_PRESENT'in task('preflight',s,st,False)
assert {p.name:H(p.read_bytes())for p in src.iterdir()}==before;master.unlink();checks.append('unknown_existing_master_blocks_before_mutation')
assert json.loads(task('preflight',s,st))['status']=='PREFLIGHT_PASS'
assert json.loads(task('apply',s,st))['status']=='P8_APPLIED_PENDING_FRESH_VERIFY'
assert json.loads(task('verify',s,st))['builder_exact_archive']
assert H(task('read-current',s,st))==SHA;checks.append('transaction_fresh_runtime_readback_exact')
setup='<?php require '+json.dumps(str(s/'config.php'))+';require '+json.dumps(str(s/'products-config.php'))+';'
cache=delivery/'10-avans-usloviya-i-pribyl.zip';cache.unlink()
assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("p8"));').decode()==SHA;checks.append('missing_cache_restores_exact_archive')
cache.write_bytes(b'CORRUPTED CACHE')
assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("p8"));').decode()==SHA;checks.append('corrupted_cache_restores_exact_archive')
master.write_bytes(b'CORRUPTED MASTER')
assert php(setup+'echo mvb_build_product_zip("p8")===null?"PASS":"FAIL";')==b'PASS';checks.append('corrupted_master_rejected')
shutil.copyfile(T/'current.zip',master)
for sku,sha in [('p1','99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada'),('p2','42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'),('p3','54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b'),('p4','a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea'),('p5','1a0ab501a008c9cae1b1baaaa6570d1123291630ac8ecff1db74fad411431286'),('p7','99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24'),('p9', '34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9'),('p10', '90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594'),('p11', 'ff6cf9a7056cab90ee1203a93ddb964e0308b8bd418394f4ebd672a9b8b860da'),('p13', '0b1f777b9fb65952cd219d5e61e6b8500cdcd5f1c0039ceba80e3c8f6e67f955')]:
 assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("'+sku+'"));').decode()==sha;checks.append(sku+'_delivery_unchanged')
oid='order_20261030_0003_nspqa'
o={'id':oid,'status':'paid','items':[{'sku':'p8'}]}
b=php(setup+'$o=json_decode('+json.dumps(json.dumps(o))+',true);$a=mvb_prepare_delivery($o);$expiry=$o["delivery"]["expires_at"];$token=$o["delivery"]["token"];$b=mvb_prepare_delivery($o);if($a["missing"]||$b["missing"]||$expiry!==$o["delivery"]["expires_at"]||$token!==$o["delivery"]["token"]||strtotime($expiry)-strtotime($o["delivery"]["created_at"])!==3600)exit(2);echo json_encode($o);')
order=json.loads(b);checks.append('delivery_ttl_3600_and_repeat_not_extended')
other={'id':'order_20261031_0004_nspqa','status':'paid','items':[{'sku':'p8'}]}
second=json.loads(php(setup+'$o=json_decode('+json.dumps(json.dumps(other))+',true);mvb_prepare_delivery($o);echo json_encode($o);'))
assert second['delivery']['token']!=order['delivery']['token']
old_order=json.loads(json.dumps(order));old_order['delivery']['expires_at']='2026-01-01T00:00:00+00:00'
repeat=json.loads(php(setup+'$o=json_decode('+json.dumps(json.dumps(old_order))+',true);mvb_prepare_delivery($o);echo json_encode($o);'))
assert repeat['delivery']['expires_at']==old_order['delivery']['expires_at'] and repeat['delivery']['token']==old_order['delivery']['token']
assert second['delivery']['expires_at']!=repeat['delivery']['expires_at']
checks.append('separate_paid_orders_independent_tokens_and_expiry')
email=php(setup+'$o=json_decode('+json.dumps(json.dumps(order))+',true);$plan=mvb_prepare_delivery($o);echo mvb_delivery_email($o,$plan["links"]);').decode()
assert '00-INSTRUKCIYA.pdf'in email and '00-START-HERE'not in email and '1 час'in email
checks.append('buyer_email_exact_entry_file_and_one_hour')
for kind,status in [('current',200),('boundary',410),('past',410),('wrong_token',403)]:
 expiry='$o["delivery"]["expires_at"]=date("c",time()'+('-1'if kind=='past'else'')+');'if kind in ['boundary','past']else''
 script='<?php $o=json_decode('+json.dumps(json.dumps(order))+',true);'+expiry+'file_put_contents('+json.dumps(str(orders/(oid+'.json')))+',json_encode($o));$_GET=["o"=>"'+oid+'","t"=>'+json.dumps('wrong'if kind=='wrong_token'else order['delivery']['token'])+',"f"=>"p8"];register_shutdown_function(function(){file_put_contents('+json.dumps(str(F/'http.json'))+',json_encode(["http"=>http_response_code()?:200]));});require '+json.dumps(str(s/'download.php'))+';'
 body=php(script);assert json.loads((F/'http.json').read_text())['http']==status
 if status==200:assert H(body)==SHA
 checks.append('download_'+kind+'_'+str(status))
assert json.loads(task('finalize',s,st))['previous_product_files_retained']is False
assert not (st/'rollback').exists();assert set(p.name for p in src.iterdir())=={r['name']for r in m['members']}
assert all(H((s/n).read_bytes())==sha for n,sha in m['protected'].items());checks.append('current_only_cleanup_and_protected_handlers')
F2,s2,r2,src2,o2,d2,st2,before2=make('rollback-fixture')
task('preflight',s2,st2);task('apply',s2,st2);assert json.loads(task('rollback',s2,st2))['status']=='ROLLBACK_VERIFIED'
assert {p.name:H(p.read_bytes())for p in src2.iterdir()}==before2
assert (d2/'10-avans-usloviya-i-pribyl.zip').read_bytes()==b'OLD CACHE'
assert all(H((s2/n).read_bytes())==r['before']for n,r in m['pages'].items());checks.append('rollback_restores_source_config_pages_and_cache')
for n in [next(n for n in m['pages']if n.startswith('products/')),'katalog.html']:
 doc=Parse();doc.feed((T/'pages'/n).read_text())
 for script in doc.scripts:json.loads(script)
 if n.startswith('products/'):assert set(doc.codes)=={r['name']for r in m['members']}
checks.append('HTML_exact_composition_and_valid_JSONLD')
receipt={'status':'P8_SCOPED_PUBLICATION_ACCEPTANCE_PASS','check_count':len(checks),'checks':checks,'archive_sha256':SHA,'files':12,'release_manifest_sha256':H((T/'release.json').read_bytes()),'production_modified':False,'real_payment_performed':False}
(T/'LOCAL_TEST_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(receipt,ensure_ascii=False,indent=2))

