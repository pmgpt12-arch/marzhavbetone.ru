"""Submit existing immutable jobs through existing transport; preserve masters and active work."""
from pathlib import Path
import subprocess,json,hashlib,xml.etree.ElementTree as E,shutil,time,datetime
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';H=R/'tools/nsp-next-corrections-20261022';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');OUT=Q/'native-resume-20261022';OUT.mkdir(exist_ok=True)
helper=subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True);env={'__name__':'reviewed_existing_submitter'};exec(compile(helper,'existing_submitter','exec'),env)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={f['accepted_sha256']for f in json.loads((H/'PROTECTED_ACCEPTED_MANIFEST.json').read_text())['files']}
jobs=json.loads((H/'PREPARED_OFFICE_JOBS.json').read_text())['jobs'];pending={c:[j for j in jobs if j['channel']==c]for c in ['word','native']};active={};records=[]
def save():
 (OUT/'RESUME_STATUS.json').write_text(json.dumps({'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'jobs':records,'active':active,'remaining':{c:len(v)for c,v in pending.items()},'masters_changed':False,'accepted_13_included':False},ensure_ascii=False,indent=2))
for c in pending:assert env['previous_is_complete'](N,c),('ACTIVE_PREVIOUS_JOB',c)
start=time.time()
while any(pending.values())or active:
 for c in list(pending):
  if c in active:
   a=active[c];p=N/'results'/c/a['id']/'report.xml'
   if p.exists():
    rt=E.parse(p).getroot();assert rt.get('job')==a['id'];st=rt.get('status');assert st in ['PASS','FAIL','TIMEOUT'],st
    dest=OUT/'evidence'/c/a['id'];shutil.copytree(p.parent,dest,dirs_exist_ok=True);records.append({'channel':c,'id':a['id'],'status':st,'report_sha256':sha(p),'evidence':str(dest),'elapsed':round(time.time()-a['started'],1)});del active[c];print('RECEIVED',c,a['id'],st,flush=True)
   elif time.time()-a['started']>240:
    records.append({'channel':c,'id':a['id'],'status':'NO_RECEIPT_AFTER_240S','remaining_jobs_not_submitted':[j['id']for j in pending[c]]});pending[c]=[];del active[c];print('BLOCKED_NO_RECEIPT',c,flush=True)
  if c not in active and pending[c]:
   assert env['previous_is_complete'](N,c),('PREVIOUS_NOT_COMPLETE',c)
   j=pending[c].pop(0);src=H/'prepared-office'/c/j['id'];rt=E.parse(src/'job.xml').getroot();assert rt.get('id')==j['id'];assert (src/'job.xml').stat().st_size<=65536;assert 1<=len(rt.findall('file'))<=4
   for f in rt.findall('file'):assert sha(src/f.get('name'))==f.get('sha256')and f.get('sha256')not in protected
   d=N/c/j['id'];rp=N/'results'/c/j['id']/'report.xml'
   if rp.exists():
    rt=E.parse(rp).getroot();assert rt.get('job')==j['id'];dest=OUT/'evidence'/c/j['id'];shutil.copytree(rp.parent,dest,dirs_exist_ok=True);records.append({'channel':c,'id':j['id'],'status':rt.get('status'),'reused_existing_receipt':True,'report_sha256':sha(rp),'evidence':str(dest)});continue
   if d.exists():
    for p in src.iterdir():assert (d/p.name).is_file()and sha(p)==sha(d/p.name),('JOB_DIRECTORY_DIVERGED',str(d))
   else:shutil.copytree(src,d)
   env['submit'](N,c,d);active[c]={'id':j['id'],'started':time.time()};print('SUBMITTED',c,j['id'],flush=True)
 save()
 if time.time()-start>1800:raise TimeoutError('Bounded resume deadline')
 if active:time.sleep(4)
print('FINISHED',json.dumps({c:sum(x['status']==c for x in records)for c in ['PASS','FAIL','TIMEOUT','NO_RECEIPT_AFTER_240S']}),flush=True)
