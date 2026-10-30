from pathlib import Path
import copy,json,hashlib,shutil,subprocess
D=Path('/home/denis/projects/nsp-qa13-20261024/p1-publication-20261030');T=D/'current-only';B=D/'snapshot'
m=json.loads((T/'release.json').read_text());SHA=m['archive_sha256'];H=lambda b:hashlib.sha256(b).hexdigest();checks=[]
def fixture(name):
 F=T/name;assert not F.exists()
 site=F/'www/nastoronepodryadchika.ru';(site/'products').mkdir(parents=True)
 root=F/'products';src=root/'01-zakrytie-rabot';src.mkdir(parents=True);orders=F/'orders';delivery=orders/'delivery';delivery.mkdir(parents=True)
 for n in list(m['protected'])+list(m['pages']):
  dst=site/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(B/n,dst)
 (site/'index.html').write_text('ISOLATED')
 (site/'config.php').write_text('<?php define("ORDERS_DIR",'+json.dumps(str(orders))+');define("PRODUCTS_DIR",'+json.dumps(str(root))+');define("SITE_URL","https://example.invalid");define("ADMIN_EMAIL","qa@example.invalid");')
 before={}
 for n in m['old_members']:
  raw=('OLD FIXTURE '+n).encode();(src/n).write_bytes(raw);before[n]=H(raw)
 (delivery/'01-ks-podpisany-deneg-net.zip').write_bytes(b'OLD CACHE')
 (delivery/('p1-'+'a'*64+'.zip')).write_bytes(b'OLD HASH CACHE')
 p2=Path('/home/denis/projects/nsp-qa14-20261024/p2-v13-publication-20261029/current-only/current.zip')
 shutil.copyfile(p2,root/'P2-v13-current.zip')
 stage=F/'stage';stage.mkdir();shutil.copytree(T/'pages',stage/'pages');shutil.copyfile(T/'current.zip',stage/'current.zip')
 manifest=copy.deepcopy(m);manifest['old_members']=before;(stage/'release.json').write_text(json.dumps(manifest))
 return F,site,root,src,orders,delivery,stage,before
def run(mode,site,stage):
 r=subprocess.run(['php',str(T/'publish.php'),mode,str(site),str(stage)],capture_output=True,timeout=10)
 if r.returncode:raise RuntimeError(mode+': '+r.stderr.decode())
 return r.stdout
def php(src):
 r=subprocess.run(['php'],input=src.encode(),capture_output=True,timeout=10)
 if r.returncode:raise RuntimeError(r.stderr.decode())
 return r.stdout
F,site,root,src,orders,delivery,stage,before=fixture('fixture-r3')
assert json.loads(run('preflight',site,stage))['status']=='PREFLIGHT_PASS'
assert json.loads(run('apply',site,stage))['status']=='P1_APPLIED_PENDING_FRESH_VERIFY'
assert json.loads(run('verify',site,stage))['builder_exact_archive']
assert H(run('read-current',site,stage))==SHA
checks.append('transaction_and_server_readback_exact')
cache=delivery/('p1-'+SHA+'.zip');cache.unlink()
setup='<?php require '+json.dumps(str(site/'config.php'))+';require '+json.dumps(str(site/'products-config.php'))+';'
raw=php(setup+'$e=mvb_capture_p1_edition(); if($e===null)exit(2);echo json_encode($e);')
assert json.loads(raw)['sha256']==SHA and H(cache.read_bytes())==SHA
checks.append('missing_cache_rebuilt_from_exact_master')
orderid='order_20261030_0001_nspqa'
baseOrder={'id':orderid,'status':'paid','items':[{'sku':'p1','edition':{'zip':cache.name,'sha256':SHA}}]}
order_json=json.dumps(baseOrder)
raw=php(setup+'$o=json_decode('+json.dumps(order_json)+',true);$a=mvb_prepare_delivery($o);$e=$o["delivery"]["expires_at"];$t=$o["delivery"]["token"];$b=mvb_prepare_delivery($o);if($a["missing"]||$b["missing"]||$e!==$o["delivery"]["expires_at"]||$t!==$o["delivery"]["token"]||strtotime($e)-strtotime($o["delivery"]["created_at"])!==3600)exit(3); echo json_encode($o);')
order=json.loads(raw);assert order['delivery']['items']['p1']==cache.name
checks.append('capture_prepare_repeat_callback_ttl3600_not_extended')
for kind,status in [('current',200),('boundary',410),('past',410),('wrong_token',403)]:
 o=copy.deepcopy(order)
 if kind in ('boundary','past'):
  # Use PHP time at request generation to avoid a race around the boundary.
  expiry='$o["delivery"]["expires_at"]=date("c",time()'+('-1'if kind=='past'else'')+');'
 else:expiry=''
 script='<?php $o=json_decode('+json.dumps(json.dumps(o))+',true);'+expiry+'file_put_contents('+json.dumps(str(orders))+'."/'+orderid+'.json",json_encode($o)); $_GET=["o"=>"'+orderid+'","t"=>'+json.dumps('wrong'if kind=='wrong_token'else o['delivery']['token'])+',"f"=>"p1"];register_shutdown_function(function(){file_put_contents('+json.dumps(str(F/'http.json'))+',json_encode(["http"=>http_response_code()?:200]));});require '+json.dumps(str(site/'download.php'))+';'
 body=php(script);assert json.loads((F/'http.json').read_text())['http']==status,kind
 if kind=='current':assert H(body)==SHA
 checks.append('download_'+kind+'_'+str(status))
p2sha='42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'
assert php(setup+'echo hash_file("sha256",mvb_build_product_zip("p2"));').decode()==p2sha
checks.append('p2_existing_delivery_unchanged')
assert json.loads(run('finalize',site,stage))['previous_cache_retained']is False
assert not (delivery/'01-ks-podpisany-deneg-net.zip').exists()
assert not (delivery/('p1-'+'a'*64+'.zip')).exists()
assert not (stage/'rollback').exists()
assert set(p.name for p in src.iterdir())=={r['name']for r in m['members']}
assert all(H((site/n).read_bytes())==sha for n,sha in m['protected'].items())
checks.append('old_sources_and_caches_removed_protected_files_unchanged')
F2,s2,r2,src2,o2,d2,st2,old=fixture('rollback-fixture-r3')
run('preflight',s2,st2);run('apply',s2,st2);assert json.loads(run('rollback',s2,st2))['status']=='ROLLBACK_VERIFIED'
assert {p.name:H(p.read_bytes())for p in src2.iterdir()}==old
assert all(H((s2/n).read_bytes())==row['before']for n,row in m['pages'].items())
assert (d2/'01-ks-podpisany-deneg-net.zip').read_bytes()==b'OLD CACHE'
assert not (r2/'P1-v1-current.zip').exists()
checks.append('rollback_restores_old_sources_pages_config')
receipt={'status':'P1_LOCAL_RELEASE_ACCEPTANCE_PASS','checks':checks,'check_count':len(checks),'archive_sha256':SHA,'file_count':18,'real_payment_performed':False,'production_modified':False,'release_manifest_sha256':H((T/'release.json').read_bytes())}
(T/'LOCAL_TEST_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
