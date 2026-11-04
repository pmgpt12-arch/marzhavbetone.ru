"""Resume immutable native jobs after verified late receipt; no product edits."""
from pathlib import Path
import json,hashlib,subprocess,xml.etree.ElementTree as E,time,datetime,shutil,fcntl
Q=Path(__file__).resolve().parents[1]; R=Q.parent/'integration-20261022/repo'; H=R/'tools/nsp-next-corrections-20261022'
N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
O=Q/'native-recovery-20261022';O.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert env['previous_is_complete'](N,'native'),'PREVIOUS_JOB_PENDING'
protected={f['accepted_sha256']for f in json.loads((H/'PROTECTED_ACCEPTED_MANIFEST.json').read_text())['files']}
jobs=[H/'prepared-office/native'/('nsp-next-excel-'+str(i)+'-20261022')for i in range(7,12)]
jobs += [Q/'native-resume-20261022/prepared-native/nsp-next-excel-5-coercion-v2-20261022']
records=[]
def save():
 (O/'STATE.json').write_text(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':records,'masters_changed':False,'accepted_13_retested':False},ensure_ascii=False,indent=2))
for src in jobs:
 rt=E.parse(src/'job.xml').getroot();jid=rt.get('id');dest=N/'native'/jid;rp=N/'results/native'/jid/'report.xml'
 assert env['previous_is_complete'](N,'native'),'PREVIOUS_PENDING'
 for f in rt.findall('file'):assert sha(src/f.get('name'))==f.get('sha256')and f.get('sha256')not in protected
 rec={'id':jid,'files':[{**f.attrib}for f in rt.findall('file')]}
 records.append(rec)
 if not rp.exists():
  if dest.exists():
   for p in src.iterdir():assert (dest/p.name).is_file()and sha(dest/p.name)==sha(p),'JOB_DIVERGED'
  else:shutil.copytree(src,dest)
  env['submit'](N,'native',dest);rec['status']='SUBMITTED';save();print('SUBMITTED',jid,flush=True)
  until=time.monotonic()+240
  while time.monotonic()<until:
   assert E.parse(N/'native/current.xml').getroot().get('id')==jid,'FOREIGN_QUEUE_CHANGE'
   if rp.exists():break
   time.sleep(3)
  if not rp.exists():rec['status']='NO_RECEIPT_AFTER_240S';save();print('STOP_NO_RECEIPT',jid,flush=True);break
 receipt=E.parse(rp).getroot();assert receipt.get('job')==jid
 rec.update(status=receipt.get('status'),receipt_sha256=sha(rp),checks=len(receipt.findall('check')),failed=[dict(x.attrib)for x in receipt.findall('check')if x.get('pass','').lower()!='true'])
 shutil.copytree(rp.parent,O/'evidence/native'/jid,dirs_exist_ok=True);save();print('RECEIVED',jid,rec['status'],'CHECKS',rec['checks'],'FAILED',rec['failed'],flush=True)
print('FINISHED',flush=True)
