from pathlib import Path
import xml.etree.ElementTree as E,json,hashlib,shutil,subprocess,time,datetime,copy,fcntl
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022')
N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
R=Q.parent/'integration-20261022/repo'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
D=Q/('office-control-'+stamp)
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={'__name__':'reviewed_submitter'}
exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
for ch in ['native','word']:assert env['previous_is_complete'](N,ch),'Unfinished '+ch
states={}
for ch in ['native','word']:
 states[ch]=json.loads((N/'results'/(ch+'-laptop-status.json')).read_text())
 assert states[ch]['state']=='ONLINE','Agent status not ONLINE'
 prior=json.loads((Q/'office-control-20261022-233620/RESULTS.json').read_text());last=next(r for r in prior if r['channel']==ch);assert states[ch]['time']>datetime.datetime.fromisoformat(last['checked_utc']).timestamp(),'No observed agent reconnection after last failure'
# ONLINE is startup telemetry, not a periodic heartbeat. Verify connection from actual recent requests.
assert str(N/'transport.py')in Path('/proc/1606/cmdline').read_bytes().replace(b'\0',b' ').decode()
poll=subprocess.run(['journalctl','_PID=1606','--since','-2 min','-n','80','--no-pager','-o','json'],capture_output=True,text=True,timeout=15);assert poll.returncode==0
latest_polls={}
for line in poll.stdout.splitlines():
 r=json.loads(line);msg=r.get('MESSAGE','');ts=int(r['__REALTIME_TIMESTAMP'])/1e6
 for ch in ['native','word']:
  if '192.168.1.140'in msg and 'GET /'+ch+'/current.xml HTTP/'in msg and (' 200 'in msg or ' 204 'in msg):latest_polls[ch]=max(latest_polls.get(ch,0),ts)
assert all(0<=time.time()-latest_polls.get(ch,0)<120 for ch in ['native','word']),'No fresh authenticated channel polling'
D.mkdir()
# Isolate a minimal known-good source from the previously accepted control receipts.
jobs=[]
for ch,old in [('native','nsp-free-print-v2-20261022'),('word','nsp-p11-remaining-word-20261023')]:
 oldroot=E.parse(N/ch/old/'job.xml').getroot()
 assert E.parse(N/'results'/ch/old/'report.xml').getroot().get('status')=='PASS'
 f=copy.deepcopy(oldroot.findall('file')[0])
 if ch=='native':
  for c in list(f):
   if c.tag=='case'and c.get('name')not in ['empty','single']:f.remove(c)
  assert len(f.findall('case'))==2 and sum(len(c.findall('expect'))for c in f.findall('case'))==4
  f.set('tag','controlx')
 else:f.set('tag','controlw')
 jid='nsp-office-control-'+ch+'-'+stamp
 j=E.Element('job',id=jid,qa_only='true',scope='One previously passing file; runtime smoke only, not product acceptance')
 j.append(f);p=N/ch/old/f.get('name');assert sha(p)==f.get('sha256')
 d=D/'inputs'/ch;d.mkdir(parents=True);shutil.copy2(p,d/p.name)
 E.ElementTree(j).write(d/'job.xml',encoding='utf-8',xml_declaration=True)
 jobs.append((ch,jid,d,j))
pre={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hypothesis':'Observed new ONLINE timestamps after previous FAIL receipts; actual recent channel GETs verified. One known-good control per channel checks possible recovery without assuming application startup.','states':states,'latest_channel_polls':latest_polls,'task_validity':'Explicit request to check Word and Excel','atomicity':'One source file per channel, sequential','contract':'PASS requires exact source SHA, native opening and PDF; Excel additionally calculates four expected values','budget_seconds_per_channel':240,'source_authoring':False,'office_or_worker_settings_changed':False,'preflight':'PASS'}
(D/'PREFLIGHT.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2))
print('EVIDENCE_DIR',str(D),flush=True)
out=[]
for ch,jid,d,job in jobs:
 assert all(env['previous_is_complete'](N,c)for c in ['native','word'])
 dest=N/ch/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,ch,dest)
 print('SUBMITTED',ch,jid,flush=True)
 rp=N/'results'/ch/jid/'report.xml';deadline=time.monotonic()+240
 while time.monotonic()<deadline:
  assert E.parse(N/ch/'current.xml').getroot().get('id')==jid,'Queue changed externally'
  if rp.exists():break
  time.sleep(3)
 row={'channel':ch,'job':jid,'status':'NO_RECEIPT','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if not rp.exists():
  out.append(row);(D/'RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('STOP_NO_RECEIPT',ch,flush=True);break
 rt=E.parse(rp).getroot();assert rt.get('job')==jid
 shutil.copytree(rp.parent,D/'evidence'/ch/jid)
 row.update(status=rt.get('status'),receipt_sha256=sha(rp),error=rt.findtext('error'),file_receipts=[dict(f.attrib)for f in rt.findall('file')],checks=[dict(c.attrib)for c in rt.findall('check')])
 if row['status']=='PASS':
  f=job.find('file');tag=f.get('tag');pdf=rp.parent/(tag+('-filled.pdf'if ch=='native'else'.pdf'))
  assert pdf.is_file()and pdf.read_bytes().startswith(b'%PDF-')
  assert sha(d/f.get('name'))==f.get('sha256')
  if ch=='native':
   checks=rt.findall('check');assert checks and all(c.get('pass','').lower()=='true'for c in checks)
   assert any(c.get('name')==tag+':source_unchanged'and c.get('actual')==f.get('sha256')for c in checks)
   assert len([c for c in checks if ':empty:'in c.get('name','')or ':single:'in c.get('name','')])==4
  else:
   fr=rt.find('file');assert fr.get('status')=='PASS'and fr.find('result').get('source_sha256')==f.get('sha256')and sha(pdf)==fr.get('pdf_sha256')
  row.update(source_sha256=f.get('sha256'),pdf_sha256=sha(pdf),pdf_info=subprocess.check_output(['pdfinfo',str(pdf)],text=True,timeout=20))
  vd=D/'visual'/ch;vd.mkdir(parents=True);subprocess.run(['pdftoppm','-scale-to','1400','-png',str(pdf),str(vd/'page')],capture_output=True,check=True,timeout=45)
 out.append(row);(D/'RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(('RECEIVED '+ch+' '+row['status']+' CHECKS '+str(len(row.get('checks',[])))+(' ERROR '+row['error'][:180] if row.get('error') else '')),flush=True)
(D/'COMPLETED.txt').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n')
print('COMPLETED',str(D),flush=True)
