from pathlib import Path
import xml.etree.ElementTree as E,json,hashlib,shutil,subprocess,time,copy,fcntl
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');A=Q/'avans-corrections-20261023';P=Q/'paid-followup-20261023';S=Q/'office-resumed-products-20261023';R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
assert (A/'NATIVE_RUN_FINISHED.txt').exists();assert all(r['status']=='PASS'for r in json.loads((A/'NATIVE_RESULTS.json').read_text()))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
S.mkdir(exist_ok=False)
jobs=[]
# Persistence check on the native saved copy; source candidate is not resaved.
jid='nsp-avans-reopen-v1-20261023';j=E.Element('job',id=jid,qa_only='true');src=N/'results/native/nsp-avans-xlsx-v1-20261023/av1-filled.xlsx';f=E.SubElement(j,'file',name='avans-native-saved.xlsx',tag='avr',sheet='Изъятия',sha256=sha(src),export_source_first='true',print_preflight='true');case=E.SubElement(f,'case',name='saved-blank-input-state')
for i in range(12,17):E.SubElement(case,'expect',cell='D'+str(i),kind='text',value='УКАЖИТЕ ДАТУ')
d=S/'inputs'/jid;d.mkdir(parents=True);shutil.copy2(src,d/f.get('name'));E.ElementTree(j).write(d/'job.xml',encoding='utf-8',xml_declaration=True);jobs.append(('native',jid,d,j))
for ch,old,jid in [('word','nsp-p11-final-letters-r1-20261023','nsp-p11-final-letters-r2-20261023'),('native','nsp-p5-final-print-r1-20261023','nsp-p5-final-print-r2-20261023')]:
 src=P/'deferred-office-jobs'/old;j=E.parse(src/'job.xml').getroot();j.set('id',jid);d=S/'inputs'/jid;d.mkdir(parents=True)
 for f in j.findall('file'):assert sha(src/f.get('name'))==f.get('sha256');shutil.copy2(src/f.get('name'),d/f.get('name'))
 E.ElementTree(j).write(d/'job.xml',encoding='utf-8',xml_declaration=True);jobs.append((ch,jid,d,j))
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
rows=[]
for ch,jid,d,j in jobs:
 assert all(env['previous_is_complete'](N,c)for c in ['native','word'])
 dest=N/ch/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,ch,dest);print('SUBMITTED',ch,jid,flush=True)
 rp=N/'results'/ch/jid/'report.xml';deadline=time.monotonic()+240
 while time.monotonic()<deadline:
  assert E.parse(N/ch/'current.xml').getroot().get('id')==jid
  if rp.exists():break
  time.sleep(3)
 row={'channel':ch,'job':jid,'status':'NO_RECEIPT','files':[]}
 if not rp.exists():
  rows.append(row);(S/'RESULTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('STOP_NO_RECEIPT',flush=True);break
 rt=E.parse(rp).getroot();assert rt.get('job')==jid;shutil.copytree(rp.parent,S/'evidence'/ch/jid);row.update(status=rt.get('status'),receipt_sha256=sha(rp),error=rt.findtext('error'),checks=[dict(c.attrib)for c in rt.findall('check')],file_receipts=[dict(f.attrib)for f in rt.findall('file')])
 if row['status']=='PASS':
  if ch=='native':assert rt.findall('check')and all(c.get('pass','').lower()=='true'for c in rt.findall('check'))
  for f in j.findall('file'):
   tag=f.get('tag');pdf=rp.parent/(tag+('-filled.pdf'if ch=='native'else'.pdf'));assert pdf.is_file()
   if ch=='word':
    fr=next(x for x in rt.findall('file')if x.get('tag')==tag);assert fr.get('status')=='PASS'and fr.find('result').get('source_sha256')==f.get('sha256')and sha(pdf)==fr.get('pdf_sha256')
   else:assert any(c.get('name')==tag+':source_unchanged'and c.get('actual')==f.get('sha256')for c in rt.findall('check'))
   vd=S/'visual'/jid/tag;vd.mkdir(parents=True);subprocess.run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(vd/'page')],check=True,capture_output=True,timeout=90);row['files'].append({'file':f.get('name'),'source_sha256':f.get('sha256'),'pdf_sha256':sha(pdf),'pdf_info':subprocess.check_output(['pdfinfo',str(pdf)],text=True,timeout=20),'visual_review':'PENDING'})
 rows.append(row);(S/'RESULTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print('RECEIVED',jid,row['status'],'CHECKS',len(row.get('checks',[])),flush=True)
 if row['status']!='PASS'and not row.get('checks'):print('STOP_RUNTIME_FAILURE',flush=True);break
print('FINISHED',str(S),flush=True)
