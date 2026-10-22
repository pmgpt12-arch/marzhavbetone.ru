from pathlib import Path
from zipfile import ZipFile
import json,hashlib,shutil,subprocess,xml.etree.ElementTree as E,sys
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';ROOT=Q.parents[1];SEED=ROOT/'tools/nsp-product-audit-fixes-20261021/remaining-review-20261022';OUT=R/'tools/nsp-next-corrections-20261022';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(n):return json.loads((Q/n).read_text())
def save(n,d):(Q/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
ledger=load('ISSUE_LEDGER.json')
for r in ledger['issues']:
 if r.get('id','').startswith('free-product-checklist'):r['file']='downloads/checklist-zakrytiya-rabot.pdf'
save('ISSUE_LEDGER.json',ledger)
proof=load('P8_REUSED_NATIVE_PROOFS.json');assert len(proof['files'])==5
for f in proof['files']:assert sha((R/'products-storage/10-avans-usloviya-i-pribyl'/f['file']).read_bytes())==f['sha256']
protected=json.loads((Q.parent/'integration-20261022/MANIFEST_VERIFIED_FILES.json').read_text())['files'];p8accepted=[x for x in protected if x['sku']=='P8'];assert len(p8accepted)==5
walk={'sku':'P8','status':'FULL_PRODUCT_QA_CANDIDATE','source_head':'203b39a390c09157adcd6760aa04318df332bedc','steps':[{'files':['00','01'],'result':'Read order, field mapping and evidence of delivery; Start gains source links, support, example and exception route'},{'files':['02','03','04'],'result':'Compare funding and guarantee cost; no recalculation/reopening of accepted unchanged workbooks'},{'files':['05','06'],'result':'Proposed terms need agreement; existing contract amendment is separated from negotiations'},{'files':['07'],'result':'Use only for agreed advance, satisfied payout condition and elapsed deadline'},{'files':['08','09','10'],'result':'Separate termination ground, documented work and payments; statement is not a court decision'}],'example':{'unit':'million RUB','work':4,'advance':3,'additional_paid':.5,'balance_due_to_contractor':.5,'method':'Independent arithmetic illustration, not a new Excel acceptance'},'reused_word_native':proof['files'],'accepted_unchanged':p8accepted,'manual_recheck_requested':False,'production_release':False}
save('P8_WALKTHROUGH.json',walk)
# Compare print contracts on final bytes; no Office worker or source workbook is changed.
sys.path.insert(0,str(R/'tools'));from check_xlsx_print_contract import snapshot,compare
prints=[]
for f in load('new-workbook-manifest.json'):
 diff=compare(snapshot(R/f['path']),snapshot(Q/'candidates'/f['path']));assert not diff,(f['path'],diff);prints.append({'path':f['path'],'sha256':f['sha256'],'print_metadata':('EXISTING_PRESERVED_ADDED_SCOPED_PRINT_AREAS' if '/22-reestr-garantiynyh-uderzhaniy.xlsx' in f['path'] else 'UNCHANGED'),'native_print':'BLOCKED'})
save('PRINT_CONTRACTS.json',prints)
# Bounded native manifests are prepared in QA only. Nothing is sent to current.xml.
word=[]
for p in sorted((Q/'candidates').rglob('*.docx')):word.append(p)
for p in sorted((SEED/'candidates/products-storage').rglob('*.docx')):word.append(p)
jobs=[]
for offset in range(0,len(word),4):
 ident='nsp-next-word-b'+str(offset//4+1)+'-20261022';d=Q/'prepared-office/word'/ident;d.mkdir(parents=True,exist_ok=True);job=E.Element('job',id=ident,qa_only='true')
 for i,p in enumerate(word[offset:offset+4]):
  shutil.copyfile(p,d/p.name);E.SubElement(job,'file',name=p.name,tag='w'+str(offset+i+1),sha256=sha(p.read_bytes()))
 E.ElementTree(job).write(d/'job.xml',encoding='utf-8',xml_declaration=True);jobs.append({'id':ident,'channel':'word','files':len(job),'status':'PREPARED_NOT_SUBMITTED'})
cases=load('regression-cases.json');lo=load('lo-regression-results.json');books=[]
for p in sorted((Q/'plans').glob('*.json')):
 spec=json.loads(p.read_text());books.append((Q/'candidates/products-storage'/spec['path'],cases[spec['issue']],spec['issue']))
for p in sorted((SEED/'candidates/free').rglob('*.xlsx')):
 with ZipFile(p)as z:sheet=E.fromstring(z.read('xl/workbook.xml')).find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets')[0].get('name')
 if p.name.startswith('04-'):cs=[{'name':'baseline','inputs':{sheet:{'D2':150,'F2':850}},'expect':{sheet+'!G5':127500}},{'name':'additional','inputs':{sheet:{'D2':150,'F2':850,'C3':'Дополнительная работа','D3':20,'E3':'шт','F3':1000}},'expect':{sheet+'!G5':147500}}]
 else:cs=[{'name':'baseline','inputs':{},'expect':{sheet+'!E7':11}},{'name':'additional','inputs':{sheet:{'B6':'Пятое приложение','E6':4}},'expect':{sheet+'!E7':15}}]
 books.append((p,cs,'held-free-'+p.name))
for bi,(p,cs,issue)in enumerate(books):
 ident='nsp-next-excel-'+str(bi+1)+'-20261022';d=Q/'prepared-office/native'/ident;d.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d/p.name)
 with ZipFile(p)as z:sheet=E.fromstring(z.read('xl/workbook.xml')).find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets')[0].get('name')
 job=E.Element('job',id=ident,qa_only='true');f=E.SubElement(job,'file',name=p.name,tag='n'+str(bi+1),sheet=sheet,sha256=sha(p.read_bytes()),export_source_first='true',print_preflight='true');prior=set()
 for c in cs:
  node=E.SubElement(f,'case',name=c['name']);keys={(s,a)for s,vs in c['inputs'].items()for a in vs}
  for s,a in sorted(prior|keys):E.SubElement(node,'set',sheet=s,cell=a,kind='blank',value='')
  for s,vs in c['inputs'].items():
   for a,v in vs.items():E.SubElement(node,'set',sheet=s,cell=a,kind='blank'if v is None else'text'if isinstance(v,str)else'number',value=''if v is None else str(v))
  for ref,value in c['expect'].items():
   s,a=ref.rsplit('!',1)
   if isinstance(value,dict):value=next(x['actual']for row in lo if row['phase']=='after'and row['issue']==issue and row['case']==c['name']for x in row['checks']if x['cell']==ref)
   E.SubElement(node,'expect',sheet=s,cell=a,kind='blank'if value==''else'text'if isinstance(value,str)else'number',value=str(value))
  prior=keys
 raw=E.tostring(job,encoding='utf-8',xml_declaration=True);assert len(raw)<=65536;(d/'job.xml').write_bytes(raw);jobs.append({'id':ident,'channel':'native','files':1,'cases':len(cs),'bytes':len(raw),'sha256':sha(p.read_bytes()),'status':'PREPARED_NOT_SUBMITTED'})
save('PREPARED_OFFICE_JOBS.json',{'jobs':jobs,'queue_changed':False,'accepted_13_included':False})
# Keep paid master sources and historical registry intact. All changes live under this one audit directory.
for folder in ['candidates','scripts','plans','prepared-office']:
 shutil.copytree(Q/folder,OUT/folder,dirs_exist_ok=True)
shutil.copytree(SEED/'candidates',OUT/'held-six',dirs_exist_ok=True)
for f in Q.glob('*.json'):shutil.copyfile(f,OUT/f.name)
shutil.copyfile(Q/'build_candidates.php',OUT/'build_candidates.php');shutil.copyfile(Q.parent/'integration-20261022/MANIFEST_VERIFIED_FILES.json',OUT/'PROTECTED_ACCEPTED_MANIFEST.json')
for f in (Q/'buyer-candidates').glob('*.zip'):
 d=OUT/'candidate-archives'/f.name;d.parent.mkdir(exist_ok=True);shutil.copyfile(f,d)
for f in (Q/'proof').glob('*.log'):
 d=OUT/'evidence'/f.name;d.parent.mkdir(exist_ok=True);shutil.copyfile(f,d)
for f in (Q/'rendered').glob('*/*.pdf'):
 d=OUT/'evidence/docx-render'/f.name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,d)
for f in (Q/'rendered').glob('*/render.log'):
 d=OUT/'evidence/docx-render'/(f.parent.name+'-render.log');shutil.copyfile(f,d)
assert sha((R/'products-storage/ARTIFACT-INVENTORY.json').read_bytes())=='f9ea9acb1c39826599787ebdc9372765863a48b8f812eb14c41a39d12627da5f'
for f in protected:assert sha((R/f['path']).read_bytes())==f['accepted_sha256']
print('ARTIFACTS_PREPARED',OUT,'OFFICE_JOBS',len(jobs),'NEW_SOURCE_MASTERS_CHANGED',False)
