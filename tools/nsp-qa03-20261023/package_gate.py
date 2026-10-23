"""Fail closed: frozen inputs, native receipts, reviewed pages and exactly five ZIP files."""
from pathlib import Path
import hashlib,json,zipfile,io,subprocess,xml.etree.ElementTree as E
from docx import Document
O=Path(__file__).resolve().parent;R=O.parent.parent;B=json.loads((O/'BASELINE.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def blob(path):return subprocess.check_output(['git','show',B['source_head']+':'+path],cwd=R,timeout=15)
checks=[]
for f in B['source_files']:assert sha(O/'source'/f['name'])==f['sha256']
for f in B['protected_13']:
 assert sha(R.parent/'qa01-repo'/f['path'])==f['sha256']
 assert subprocess.check_output(['git','rev-parse',B['source_head']+':'+f['path']],cwd=R,text=True,timeout=10).strip()==f['git_blob']
checks.append('protected13 exact file SHA and baseline git blob IDs')
q1=R/'tools/nsp-qa01-20261023/retention';q2=R/'tools/nsp-qa02-20261023'
assert sha(q1/'candidate/04-pismo-o-vozvrate-uderzhaniya.docx')==B['accepted_qa01_letter_sha256']
assert sha(q1/'uderzhaniya-QA-only.zip')==B['qa01_zip_sha256']
assert sha(q2/'MANIFEST.json')==B['qa02_manifest_sha256']
m2=json.loads((q2/'MANIFEST.json').read_text());assert sha(q2/m2['archive'])==B['qa02_archive_sha256']
for f in m2['entries']:assert sha(q2/'candidate'/f['name'])==f['candidate_sha256']
# All older tracked QA artifacts must still equal their base bytes; no accepted candidate exceptions here.
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',B['source_head'],'tools/nsp-qa01-20261023','tools/nsp-qa02-20261023'],cwd=R).decode().split('\0')
for path in filter(None,paths):
 p=R/path
 if p.exists():assert p.read_bytes()==blob(path),path
checks.append('all present tracked QA01/QA02 files unchanged')
assert hashlib.sha256(blob('downloads/uderzhaniya.zip')).hexdigest()==B['source_zip_sha256']
assert sha(O/'candidate/99-chto-dalshe.pdf')==next(f['sha256']for f in B['source_files']if f['name'].endswith('.pdf'))
accepted='Итог по колонке «Разница» — сумма вашего обращения: возвраты уже учтены в каждой строке. Повторно их не вычитайте. Итог должен совпадать с суммой в письме.'
assert accepted in [p.text for p in Document(O/'candidate/04-pismo-o-vozvrate-uderzhaniya.docx').paragraphs]
receipts=[];case_names=set();native_checks=0
plans=[json.loads((O/f'{p}/PLAN.json').read_text())for p in ['native-jobs','native-extra']]
for plan,prefix in zip(plans,['native-jobs','native-extra']):
 for j in plan['jobs']:
  folder=O/'native-evidence'/j['channel']/j['id'];report=folder/'report.xml';r=E.parse(report).getroot();assert r.get('status')=='PASS'and r.get('job')==j['id']
  job=E.parse(O/prefix/j['channel']/j['id']/'job.xml').getroot()
  for c in r.findall('check'):assert c.get('pass','').lower()=='true',c.attrib
  native_checks+=len(r.findall('check'))
  if j['channel']=='native':
   assert r.get('excel_version')=='16.0'
   for f in job.findall('file'):
    tag=f.get('tag');s=next(x for x in r.findall('check')if x.get('name')==tag+':input_sha');assert s.get('actual')==f.get('sha256')
    for c in f.findall('case'):
     cc=[x for x in r.findall('check')if x.get('name','').startswith(tag+':'+c.get('name')+':')];assert len(cc)==len(c.findall('expect'))
     case_names.add(c.get('name'))
  else:
   for f in job.findall('file'):
    fr=next(x for x in r.findall('file')if x.get('tag')==f.get('tag'));res=fr.find('result');assert res.get('source_sha256')==f.get('sha256')and res.get('word_version')=='16.0'and res.get('status')=='PASS'
    assert sha(folder/(f.get('tag')+'.pdf'))==fr.get('pdf_sha256')
  receipts.append(dict(channel=j['channel'],job=j['id'],sha256=sha(report),status='PASS'))
cases=json.loads((O/'CASES.json').read_text())['cases'];assert case_names=={c['name']for c in cases}
reopen=O/'native-evidence/native/nsp-qa03-excel-reopen-v1-20261023';rr=E.parse(reopen/'report.xml').getroot();assert rr.get('status')=='PASS'and rr.get('excel_version')=='16.0'
for c in rr.findall('check'):assert c.get('pass','').lower()=='true'
saved=O/'native-evidence/native/nsp-qa03-excel-b3c-v2-20261023/q3x-filled.xlsx';savedsha=sha(saved)
assert next(c for c in rr.findall('check')if c.get('name')=='q3r:input_sha').get('actual')==savedsha
receipts.append(dict(channel='native',job=rr.get('job'),sha256=sha(reopen/'report.xml'),status='PASS',native_saved_input_sha256=savedsha))
bridge=json.loads((O/'proof/HEADER_ONLY_CHANGE.json').read_text())
assert bridge['formula_and_all_other_cell_payloads_identical'] is True
assert bridge['before_sha256']==sha(O/'proof/previous-xlsx-before-header-fix/02-reestr-uderzhaniy-po-obektu.xlsx')
assert bridge['after_sha256']==sha(O/'candidate/02-reestr-uderzhaniy-po-obektu.xlsx')
assert len(bridge['diff'])==1 and bridge['diff'][0]['cell']=='I8'
finalplan=json.loads((O/'native-final/PLAN.json').read_text());final_cases=0
for j in finalplan['jobs']:
 folder=O/'native-evidence/native'/j['id'];r=E.parse(folder/'report.xml').getroot();assert r.get('status')=='PASS'and r.get('excel_version')=='16.0'
 job=E.parse(O/'native-final/native'/j['id']/'job.xml').getroot()
 for f in job.findall('file'):
  assert f.get('sha256')==bridge['after_sha256']
  assert next(c for c in r.findall('check')if c.get('name')==f.get('tag')+':input_sha').get('actual')==bridge['after_sha256']
  for c in f.findall('case'):
   cc=[x for x in r.findall('check')if x.get('name','').startswith(f.get('tag')+':'+c.get('name')+':')];assert len(cc)==len(c.findall('expect'));final_cases+=1
 for c in r.findall('check'):assert c.get('pass','').lower()=='true'
 receipts.append(dict(channel='native',job=j['id'],sha256=sha(folder/'report.xml'),status='PASS',candidate_sha256=bridge['after_sha256']))
reopen=O/'native-evidence/native/nsp-qa03-excel-final-reopen-v3-20261023';rr=E.parse(reopen/'report.xml').getroot();assert rr.get('status')=='PASS'and rr.get('excel_version')=='16.0'
for c in rr.findall('check'):assert c.get('pass','').lower()=='true'
saved=O/'native-evidence/native'/finalplan['filled_source_job']/'q3f-filled.xlsx'
assert next(c for c in rr.findall('check')if c.get('name')=='q3fr:input_sha').get('actual')==sha(saved)
receipts.append(dict(channel='native',job=rr.get('job'),sha256=sha(reopen/'report.xml'),status='PASS',native_saved_input_sha256=sha(saved)))
assert final_cases==6
visual=json.loads((O/'proof/VISUAL_REVIEW.json').read_text());assert visual['status']=='PASS'
for f in visual['pdfs']:
 assert sha(O/f['path'])==f['sha256']and f['reviewed_pages']==list(range(1,f['pages']+1))
local=json.loads((O/'proof/ARTIFACT_SCENARIOS.json').read_text());assert local['passed']==local['cases']==len(cases)
expected={f['name']for f in B['source_files']};assert {p.name for p in(O/'candidate').iterdir()}==expected
archive=O/'uderzhaniya-QA03-only.zip';entries=[]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
 for f in sorted(expected):z.write(O/'candidate'/f,arcname=f)
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None and set(z.namelist())==expected and len(z.infolist())==5
 for f in B['source_files']:
  name=f['name'];b=z.read(name);assert b==(O/'candidate'/name).read_bytes();xmlcount=0
  if name.endswith(('.docx','.xlsx')):
   with zipfile.ZipFile(io.BytesIO(b))as inner:
    assert inner.testzip()is None
    for n in inner.namelist():
     if n.endswith(('.xml','.rels')):E.fromstring(inner.read(n));xmlcount+=1
  entries.append(dict(name=name,status='PASS',basis='UNCHANGED_ACCEPTED; exact PDF SHA and fresh visual review'if name.endswith('.pdf')else'CHANGED_NATIVE_AND_VISUAL_PASS',source_sha256=f['sha256'],starting_candidate_sha256=f['starting_candidate_sha256'],candidate_sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),crc32=f'{z.getinfo(name).CRC:08x}',xml_parts_checked=xmlcount))
manifest=dict(status='FULL_QA_PASS',source_head=B['source_head'],branch=B['branch'],archive=archive.name,archive_sha256=sha(archive),entries=entries,native_scenarios=len(cases),final_sha_native_regression_cases=final_cases,local_checks=local['checks'],native_receipts=receipts,visual_pages=sum(f['pages']for f in visual['pdfs']),preservation_checks=checks,remaining_product_blockers=[],release='HOLD; supervising review outstanding; no publication authorized')
(O/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:manifest[k]for k in ['status','archive_sha256','native_scenarios','visual_pages']},indent=2))
