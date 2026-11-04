from pathlib import Path
import json,hashlib,shutil,subprocess,time,xml.etree.ElementTree as E,fcntl
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');S=Q/'avans-corrections-20261023';R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
control=json.loads((Q/'office-control-20261023-001210/RESULTS.json').read_text());assert len(control)==2 and all(r['status']=='PASS'for r in control),'Runtime gate not passed'
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
rows=[]
for ch,jid in [('native','nsp-avans-xlsx-v1-20261023'),('word','nsp-avans-docx-v2-20261023')]:
 assert all(env['previous_is_complete'](N,c)for c in ['native','word']),'Unfinished queue'
 d=S/'deferred-office-jobs'/jid;root=E.parse(d/'job.xml').getroot();assert root.get('id')==jid
 for f in root.findall('file'):assert sha(d/f.get('name'))==f.get('sha256')
 dest=N/ch/jid;assert not dest.exists(),'Immutable id already used'
 shutil.copytree(d,dest);env['submit'](N,ch,dest);print('SUBMITTED',ch,jid,flush=True)
 rp=N/'results'/ch/jid/'report.xml';deadline=time.monotonic()+240
 while time.monotonic()<deadline:
  assert E.parse(N/ch/'current.xml').getroot().get('id')==jid
  if rp.exists():break
  time.sleep(3)
 row={'channel':ch,'job':jid,'status':'NO_RECEIPT','files':[]}
 if not rp.exists():
  rows.append(row);(S/'NATIVE_RESULTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('STOP_NO_RECEIPT',ch,flush=True);break
 rt=E.parse(rp).getroot();assert rt.get('job')==jid
 shutil.copytree(rp.parent,S/'evidence'/ch/jid);row.update(status=rt.get('status'),receipt_sha256=sha(rp),error=rt.findtext('error'),checks=[dict(c.attrib)for c in rt.findall('check')],file_receipts=[dict(f.attrib)for f in rt.findall('file')])
 if row['status']=='PASS':
  if ch=='native':
   checks=rt.findall('check');assert checks and all(c.get('pass','').lower()=='true'for c in checks)
   assert len([c for c in checks if any(':'+case+':'in c.get('name','')for case in ['missing-date','verified-zero','advance-only','separate-categories','missing-held-only','negative-held','text-fee','boolean-advance','work-includes-retention','offset-is-separate','money-decimals','invalid-date'])])==60
  for f in root.findall('file'):
   tag=f.get('tag');pdf=rp.parent/(tag+('-filled.pdf'if ch=='native'else'.pdf'));assert pdf.is_file()
   if ch=='word':
    fr=next(x for x in rt.findall('file')if x.get('tag')==tag);assert fr.get('status')=='PASS'and fr.find('result').get('source_sha256')==f.get('sha256')and sha(pdf)==fr.get('pdf_sha256')
   else:assert any(c.get('name')==tag+':source_unchanged'and c.get('actual')==f.get('sha256')for c in rt.findall('check'))
   vd=S/'visual-native'/tag;vd.mkdir(parents=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(vd/'page')],check=True,capture_output=True,timeout=60)
   row['files'].append({'file':f.get('name'),'source_sha256':f.get('sha256'),'pdf_sha256':sha(pdf),'pdf_info':subprocess.check_output(['pdfinfo',str(pdf)],text=True,timeout=20),'visual_review':'PENDING'})
 rows.append(row);(S/'NATIVE_RESULTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('RECEIVED',ch,row['status'],'CHECKS',len(row.get('checks',[])),flush=True)
(S/'NATIVE_RUN_FINISHED.txt').write_text('Controllers completed; inspect receipts and every native PDF page before acceptance.\n')
