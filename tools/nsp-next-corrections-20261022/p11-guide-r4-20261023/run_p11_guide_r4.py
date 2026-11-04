from pathlib import Path
import base64,json,hashlib,shutil,subprocess,xml.etree.ElementTree as E,time,fcntl,zipfile
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');D=Q/'p11-guide-r4-20261023';D.mkdir(exist_ok=False);jid='nsp-p11-guide-r4-20261023';d=D/'inputs'/jid;d.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=E.Element('job',id=jid,qa_only='true');manifest=[]
for i,x in enumerate(json.loads((Q/'p11-guide-candidate-transfer.json').read_text()),1):
 p=d/x['file'];p.write_bytes(base64.b64decode(x['base64'],validate=True));assert sha(p)==x['sha256'];x.pop('base64');manifest.append(x)
 E.SubElement(j,'file',name=p.name,tag='pg'+str(i),sha256=x['sha256'])
E.ElementTree(j).write(d/'job.xml',encoding='utf-8',xml_declaration=True);(D/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert all(env['previous_is_complete'](N,c)for c in ['native','word']);dest=N/'word'/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,'word',dest);print('SUBMITTED',jid,flush=True)
rp=N/'results/word'/jid/'report.xml';deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/'word/current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
result={'job':jid,'status':'NO_RECEIPT','files':[]};(D/'RESULTS.json').write_text(json.dumps(result))
if not rp.exists():raise SystemExit('NO_RECEIPT; do not duplicate job')
shutil.copytree(rp.parent,D/'evidence');rt=E.parse(rp).getroot();assert rt.get('job')==jid;result.update(status=rt.get('status'),receipt_sha256=sha(rp),error=rt.findtext('error'));(D/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
if rt.get('status')!='PASS':raise SystemExit('NATIVE_WORD_FAIL')
assert len(rt.findall('file'))==4
for f in j.findall('file'):
 fr=next(x for x in rt.findall('file')if x.get('tag')==f.get('tag'));assert fr.get('status')=='PASS'and fr.find('result').get('source_sha256')==f.get('sha256');pdf=rp.parent/(f.get('tag')+'.pdf');assert sha(pdf)==fr.get('pdf_sha256')
 t=subprocess.check_output(['pdftotext',str(pdf),'-'],text=True,timeout=20);assert 'Адресату направляется заполненная форма'in ' '.join(t.split())and 'Заказчику направляется заполненная форма'not in ' '.join(t.split())
 first=subprocess.check_output(['pdftotext','-f','1','-l','1',str(pdf),'-'],text=True,timeout=20);assert ('[подпись]'in first or 'Иванов И. И.'in first)and 'Как пользоваться этим документом'not in first
 v=D/'visual'/f.get('tag');v.mkdir(parents=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(v/'page')],check=True,capture_output=True,timeout=60)
 result['files'].append({'file':f.get('name'),'sha256':f.get('sha256'),'pdf_sha256':sha(pdf),'native_pages':len(list(v.glob('*.png'))),'sendable_first_page_gate':'PASS','visual_review':'PENDING'})
(D/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('FINISHED',json.dumps(result,ensure_ascii=False),flush=True)
