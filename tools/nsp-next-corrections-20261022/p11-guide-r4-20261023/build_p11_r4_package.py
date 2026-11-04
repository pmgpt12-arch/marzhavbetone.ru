from pathlib import Path
from zipfile import ZipFile
import hashlib,json,subprocess,shutil
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo';P=Q/'paid-followup-20261023';D=Q/'p11-guide-r4-20261023';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();bs=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((D/'MANIFEST.json').read_text());assert len(m)==4;rr=json.loads((D/'RESULTS.json').read_text());assert rr['status']=='PASS'and len(rr['files'])==4
proof=json.loads((Q/'p11-guide-authoring-proof.json').read_text());(D/'fix_guide.py').write_text(proof['builder']);(D/'CANONICAL_QA.json').write_text(json.dumps(proof['canonical'],ensure_ascii=False,indent=2)+'\n')
assert all(x['status']=='PASS_ALL_PAGES_VIEWED'and len(x['pages'])==3 for x in proof['canonical'])
dest=D/'package-sources/products-storage/13-raschet-metrami';assert not dest.exists();shutil.copytree(P/'package-sources/products-storage/13-raschet-metrami',dest)
for x in m:
 if x['role']=='BUYER_CANDIDATE':
  src=D/'inputs/nsp-p11-guide-r4-20261023'/x['file'];assert sha(src)==x['sha256'];assert sha(dest/src.name)==x['base_sha256'];shutil.copy2(src,dest/src.name)
protected=json.loads(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/nsp-next-corrections-20261022/PROTECTED_ACCEPTED_MANIFEST.json'],text=True,timeout=20))['files']
pp=[x for x in protected if x['sku']=='P11'];assert len(pp)==2
for x in pp:assert sha(dest/x['filename'])==x['accepted_sha256']
orders=D/'orders-qa';delivery=D/'candidate-archives';orders.mkdir(exist_ok=True);delivery.mkdir(exist_ok=True)
php="define('ORDERS_DIR',"+json.dumps(str(orders))+");define('PRODUCTS_DIR',"+json.dumps(str(dest.parent))+");define('DELIVERY_DIR',"+json.dumps(str(delivery))+");require "+json.dumps(str(R/'products-config.php'))+";echo mvb_build_product_zip('p11');"
p=subprocess.run(['php','-r',php],capture_output=True,text=True,check=True,timeout=20);zp=Path(p.stdout);previous=P/'candidate-archives/13-raschet-metrami.zip';assert sha(previous)=='f1414ae6a94d00d240d69e08178fe3f99ee414d7ff9f9bbd28cef90edd8ca030'
changed=[];members=[]
with ZipFile(previous)as a,ZipFile(zp)as z:
 assert z.testzip()is None and len(z.namelist())==8 and z.namelist()==a.namelist()
 for name in z.namelist():
  data=z.read(name);h=bs(data);assert h==sha(dest/name);members.append({'name':name,'sha256':h})
  if data!=a.read(name):changed.append(name)
assert set(changed)=={x['file']for x in m if x['role']=='BUYER_CANDIDATE'}
assert not any(x['name'].startswith('example-')for x in members)
gate={'status':'FULL_P11_PACKAGE_REBUILT; CURRENT_53_54_NATIVE_VERIFIED; LINE_RELEASE_NOT_CLAIMED','archive':str(zp.relative_to(D)),'sha256':sha(zp),'members':members,'member_count':8,'changed_vs_previous_full_p11_qa':changed,'new_forms_native':'PASS_EXACT_SHA_2_BLANK_2_FILLED','synthetic_examples_in_buyer_archive':False,'protected_52_56':'UNCHANGED_EXACT_SHA; prior acceptance reused','unchanged_00_50_51_52_55_56':'EXACT_BYTES_FROM_PREVIOUS_FULL_QA; historical review proof retained in prior commits','prior_norm_review':'paid-followup-20261023/P11_NORM_REVIEW.json; no new legal claims in this one-word patch','public_or_canonical_switch':False}
(D/'PACKAGE_GATE.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n');shutil.copy2(P/'P11_NORM_REVIEW.json',D/'PRIOR_P11_NORM_REVIEW.json')
print('PACKAGE',sha(zp),'MEMBERS',len(members),'CHANGED',changed,flush=True)
