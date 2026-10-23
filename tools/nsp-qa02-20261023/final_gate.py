"""Check immutable evidence, member hashes and all 56 independent expected cases."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as E,zipfile,subprocess
O=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((O/n).read_text())
manifest=read('MANIFEST.json');base=read('BASELINE.json');cases=read('CASES.json')['cases'];art=read('proof/ARTIFACT_SCENARIOS.json');assert art['passed']==56 and art['checks']==106
assert sha(O/manifest['archive'])==manifest['archive_sha256']
for x in manifest['entries']:
 assert sha(O/'candidate'/x['name'])==x['candidate_sha256']
 assert sha(O/'source'/x['name'])==x['source_sha256']
with zipfile.ZipFile(O/manifest['archive'])as z:
 assert z.testzip()is None and len(z.infolist())==5
 for x in manifest['entries']:assert hashlib.sha256(z.read(x['name'])).hexdigest()==x['candidate_sha256']
native=[];receipts=[]
for p in sorted((O/'native-evidence/native').glob('*/report.xml')):
 r=E.parse(p).getroot()
 receipts.append(dict(job=r.get('job'),status=r.get('status'),sha256=sha(p),path=str(p.relative_to(O))))
 if r.get('status')=='PASS':
  assert r.get('excel_version')=='16.0'
  assert not r.findall('error')and all(x.get('pass')=='True'for x in r.findall('check'))
  native.append((p,r))
rows=[];failed=[]
for c in cases:
 expected=c['expected'][read('CASES.json')['main_sheet']];matched=[]
 for p,r in native:
  checks=r.findall('check');names={x.get('name'):x for x in checks}
  tags={x.get('name').split(':')[0]for x in checks if ':'+c['name']+':'in x.get('name','')}
  for tag in tags:
   values=[]
   for cell,v in expected.items():
    x=names.get(tag+':'+c['name']+':'+cell)
    if x is None:break
    ev=x.get('expected','');kind,_,value=ev.partition(':')
    assert (kind=='number'and abs(float(value)-v)<1e-9)if isinstance(v,(int,float))else(kind=='text'and value==v)
    values.append(dict(cell=cell,expected=v,actual=x.get('actual'),passed=x.get('pass')=='True'))
   else:
    for suffix in ['input_sha','source_unchanged']:assert names[tag+':'+suffix].get('pass')=='True'
    matched.append(dict(job=r.get('job'),receipt_sha256=sha(p),tag=tag,checks=values))
 if not matched:failed.append(c['name'])
 rows.append(dict(name=c['name'],status='PASS'if matched else'BLOCKED',evidence=matched))
# Bind every saved/reopened input to the exact output saved by the native fill job.
plan=read('native-phase2/PLAN.json');chains=[]
for g in plan['cross']:
 filldir=O/'native-evidence/native'/g['fill']['id'];receipt=filldir/'report.xml'
 if not receipt.exists():continue
 fr=E.parse(receipt).getroot();checks={x.get('name'):x for x in fr.findall('check')}
 for e in g['entries']:
  p=filldir/(e['tag']+'-filled.xlsx')
  if not p.exists():continue
  x=checks.get(e['tag']+':input_sha');assert x is not None and x.get('actual')==manifest['entries'][1]['candidate_sha256']and x.get('pass')=='True'
  filehash=sha(p)
  for row in rows:
   if row['name']!=e['case']['name']:continue
   for ev in row['evidence']:
    rp=O/'native-evidence/native'/ev['job']/'report.xml';rr=E.parse(rp).getroot();ic=next(x for x in rr.findall('check')if x.get('name')==ev['tag']+':input_sha');assert ic.get('actual')==filehash
    chains.append(dict(case=row['name'],source_candidate_sha256=x.get('actual'),native_saved_sha256=filehash,fill_job=g['fill']['id'],reopen_job=ev['job'],status='PASS'))
word=O/'native-evidence/word/nsp-qa02-word-v2-20261023';wr=E.parse(word/'report.xml').getroot();assert wr.get('status')=='PASS';wrows=[]
docs=sorted((O/'candidate').glob('*.docx'))
for i,p in enumerate(docs,1):
 f=next(x for x in wr.findall('file')if x.get('tag')=='q2d'+str(i));res=f.find('result');assert f.get('status')=='PASS'and res.get('word_version')=='16.0'and res.get('source_sha256')==sha(p)
 pdf=word/('q2d'+str(i)+'.pdf');assert sha(pdf)==f.get('pdf_sha256')
 pages=int(subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True).stdout.split('Pages:')[1].splitlines()[0].strip());assert pages==[3,2,2][i-1]
 wrows.append(dict(file=p.name,source_sha256=sha(p),receipt_sha256=sha(word/'report.xml'),pdf_sha256=sha(pdf),actual_pdf_pages=pages,status='PASS'))
for n in ['proof/VISUAL_INITIAL.json','proof/VISUAL_WORKED.json','proof/VISUAL_FILLED_LETTER.json']:assert read(n)['status']=='PASS'
pres=read('proof/PRESERVATION_GATE.json');assert len(pres['preserved_13'])==13 and pres['status']=='PASS'
refs=read('PROTECTED_REFS_BEFORE.json')['commands'];assert all(x.get('returncode')==0 for x in refs)
pr=json.loads(next(x['stdout']for x in refs if x['args'][0]=='gh'))
assert pr['headRefOid']=='792d6467e81e2c46dabd93b3c2f18bc972d8cb94'
assert sum(x['conclusion']=='SUCCESS'for x in pr['statusCheckRollup'])==13 and sum(x['conclusion']=='SKIPPED'for x in pr['statusCheckRollup'])==1
assert len(cases)==56 and len(chains)==19 and not failed,(failed,len(chains))
result=dict(status='FULL_QA_PASS',scope='Exact QA candidate only; supervising review and separate publication approval remain required.',source_head=base['source_head'],archive_sha256=manifest['archive_sha256'],artifact_cases=56,artifact_checks=106,native_cases=56,native_checks=sum(len(c['expected'][read('CASES.json')['main_sheet']])for c in cases),native_version='Microsoft Excel / Word 2016 16.0 build 4324',native_cases_detail=rows,native_fill_save_reopen_chains=chains,word=wrows,all_native_receipts=receipts,known_failed_attempts='Preserved unmodified: cross-sheet preflight checks wrong sheet; >20 case agent limit; multi-file COM NULL on third reopen. Final accepted jobs isolate these harness limits without changing candidate, protection, Office worker or OS.',remaining_product_blockers=[],release_status='HOLD_NO_MERGE_DEPLOY_PUBLIC_REPLACEMENT',ui_typing_paste='Not manually exercised; direct native COM input and formula-level rejection tested. Physical paper output not tested; native print PDF pages visually accepted.')
(O/'FINAL_GATE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('FULL_QA_PASS: 56 native cases, 106 checks, 19 native save/reopen chains, 3 DOCX, unchanged PDF, exact ZIP5')
