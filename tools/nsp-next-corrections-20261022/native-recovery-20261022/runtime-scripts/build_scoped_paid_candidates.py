"""Scoped paid QA archives reuse exact native-reviewed held Word bytes; no canonical source mutation."""
from pathlib import Path
from zipfile import ZipFile
import subprocess,json,hashlib,shutil
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';R=Q.parent/'integration-20261022/repo';H='637a22fe1b34ded1db64a929a363f0fad14d466e'
SEED=Path('/home/denis/projects/nsp-audit-fixes-20261021/tools/nsp-product-audit-fixes-20261021/remaining-review-20261022/candidates')
sha=lambda b:hashlib.sha256(b).hexdigest()
held=json.loads((Q/'HELD_SIX.json').read_text());previous=json.loads(subprocess.check_output(['git','-C',str(R),'show',H+':tools/nsp-next-corrections-20261022/CANDIDATE_ARCHIVES.json'],text=True,timeout=12))
receipt=O/'evidence/word/nsp-next-word-b2-20261022/report.xml'
if not receipt.exists():
 receipt=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011/results/word/nsp-next-word-b2-20261022/report.xml')
import xml.etree.ElementTree as E
rt=E.parse(receipt).getroot();native={f.find('result').get('source_sha256')for f in rt.findall('file')if f.get('status')=='PASS'};assert len(native)==4
out=[]
for sku,folder in [('P7','03-dogovor-podryada'),('T2','14-peredacha-id-pod-podpis')]:
 dest=O/'scoped-paid-sources/products-storage'/folder;shutil.copytree(Q/'package-sources/products-storage'/folder,dest,dirs_exist_ok=True)
 chosen=[x for x in held if x['path'].startswith('products-storage/'+folder+'/')];assert len(chosen)==2
 for f in chosen:
  raw=(SEED/f['path']).read_bytes();assert sha(raw)==f['sha256']and f['sha256']in native
  (dest/Path(f['path']).name).write_bytes(raw)
 orders=O/'scoped-paid-orders';delivery=O/'scoped-paid-candidates';orders.mkdir(exist_ok=True);delivery.mkdir(exist_ok=True)
 php="define('ORDERS_DIR',"+json.dumps(str(orders))+");define('PRODUCTS_DIR',"+json.dumps(str(dest.parent))+");define('DELIVERY_DIR',"+json.dumps(str(delivery))+");require "+json.dumps(str(R/'products-config.php'))+";echo mvb_build_product_zip("+json.dumps(sku.lower())+");"
 result=subprocess.run(['php','-r',php],capture_output=True,text=True,check=True,timeout=15);zp=Path(result.stdout);assert zp.is_file()
 before=next(x for x in previous['archives']if x['sku']==sku);old={x['name']:x['sha256']for x in before['members']};changed=[];members=[]
 with ZipFile(zp)as z:
  assert z.testzip()is None and set(z.namelist())==set(old)
  for n in z.namelist():
   h=sha(z.read(n));members.append({'name':n,'sha256':h})
   if h!=old[n]:changed.append(n)
 assert set(changed)=={Path(x['path']).name for x in chosen}
 out.append({'sku':sku,'builder':'mvb_build_product_zip','archive':zp.name,'sha256':sha(zp.read_bytes()),'member_count':len(members),'members':members,'changed_files':changed,'exact_held_docx_reused':[{'path':x['path'],'sha256':x['sha256'],'native_word_receipt_sha256':sha(receipt.read_bytes())}for x in chosen],'status':'PACKAGE_VERIFIED_WITH_NATIVE_REVIEWED_DOCX','full_product_status':'RELEASE_BLOCKED_REMAINING_FULL_QA','canonical_sources_changed':False,'publication':False})
(O/'SCOPED_PAID_ARCHIVES.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps([{k:v for k,v in x.items()if k not in ['members','exact_held_docx_reused']}for x in out],ensure_ascii=False))
