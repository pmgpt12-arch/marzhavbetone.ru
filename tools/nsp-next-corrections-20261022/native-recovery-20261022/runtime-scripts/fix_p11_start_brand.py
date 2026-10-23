"""P11 Start branding defect: exact textual delta and scoped eight-member QA archive."""
from pathlib import Path
from zipfile import ZipFile
import subprocess,json,hashlib,shutil
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';O=Q/'native-recovery-20261022';HEAD='637a22fe1b34ded1db64a929a363f0fad14d466e';folder='13-raschet-metrami';rel='products-storage/'+folder+'/00-START-HERE.txt'
sha=lambda b:hashlib.sha256(b).hexdigest()
base=subprocess.check_output(['git','-C',str(R),'show',HEAD+':'+rel]);assert base==(Q/'package-sources'/rel).read_bytes()
old=base.decode();assert old.count('marzhavbetone.ru')==2 and old.count('marzhavbetone@yandex.ru')==1 and old.count('Маржа в бетоне')==1
new=old.replace('marzhavbetone.ru','nastoronepodryadchika.ru').replace('marzhavbetone@yandex.ru','nastoronepodryadchika@yandex.ru').replace('Маржа в бетоне','На стороне подрядчика')
assert not any(x in new.lower()for x in ['marzhavbetone','маржа в бетоне'])
assert new.replace('nastoronepodryadchika.ru','marzhavbetone.ru').replace('nastoronepodryadchika@yandex.ru','marzhavbetone@yandex.ru').replace('На стороне подрядчика','Маржа в бетоне')==old
out=O/'additional-candidates'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(new)
staged=O/'p11-package-sources/products-storage'/folder;shutil.copytree(Q/'package-sources/products-storage'/folder,staged,dirs_exist_ok=True);(staged/'00-START-HERE.txt').write_bytes(out.read_bytes())
orders=O/'orders-qa';delivery=O/'buyer-candidates';orders.mkdir(exist_ok=True);delivery.mkdir(exist_ok=True)
code="define('ORDERS_DIR',"+json.dumps(str(orders))+");define('PRODUCTS_DIR',"+json.dumps(str(staged.parent))+");define('DELIVERY_DIR',"+json.dumps(str(delivery))+");require "+json.dumps(str(R/'products-config.php'))+";echo mvb_build_product_zip('p11');"
p=subprocess.run(['php','-r',code],capture_output=True,text=True,check=True,timeout=15);zip_path=Path(p.stdout);assert zip_path.is_file()
prior=json.loads(subprocess.check_output(['git','-C',str(R),'show',HEAD+':tools/nsp-next-corrections-20261022/CANDIDATE_ARCHIVES.json'],text=True));arc=next(x for x in prior['archives']if x['sku']=='P11');before={m['name']:m for m in arc['members']}
protected=json.loads(subprocess.check_output(['git','-C',str(R),'show',HEAD+':tools/nsp-next-corrections-20261022/PROTECTED_ACCEPTED_MANIFEST.json'],text=True))['files'];accepted={Path(x['path']).name:x['accepted_sha256']for x in protected if x['sku']=='P11'}
members=[];changed=[]
with ZipFile(zip_path)as z:
 assert z.testzip()is None and len(z.namelist())==8 and set(z.namelist())==set(before)
 for n in z.namelist():
  h=sha(z.read(n));members.append({'name':n,'sha256':h})
  if h!=before[n]['sha256']:changed.append(n)
  if n in accepted:assert h==accepted[n]
assert changed==['00-START-HERE.txt']
rec={'id':'P11-START-old-brand','sku':'P11','path':rel,'source_head':HEAD,'base_sha256':sha(base),'new_sha256':sha(out.read_bytes()),'new_git_blob':hashlib.sha1(b'blob '+str(out.stat().st_size).encode()+b'\0'+out.read_bytes()).hexdigest(),'reproduction':'Two old site URLs, old support email and old brand in P11 Start','fix':'Four exact text replacements only; legal and numeric content preserved','acceptance':'Inverse delta equality; zero old-brand matches; official builder eight-member ZIP; only Start changed; two protected P11 DOCX SHA unchanged','status':'TEXT_DELTA_AND_PACKAGE_VERIFIED','full_product_status':'RELEASE_BLOCKED','archive':{'file':zip_path.name,'sha256':sha(zip_path.read_bytes()),'member_count':8,'members':members},'publication':False}
(O/'P11_START_CORRECTION.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in rec.items()if k!='archive'},ensure_ascii=False));print('P11_QA_ZIP',zip_path,'SHA',rec['archive']['sha256'])
