"""Serial Office queue client. Holds shared QA lock; never overwrites live foreign work."""
from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as E,fcntl,time,subprocess
O=Path('/home/denis/projects/nsp-qa03-20261023')
B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
PLAN=json.loads((O/'native-extra/PLAN.json').read_text());log=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(x):
    log.append(x);(O/'NATIVE_EXTRA_PROGRESS.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n');print(json.dumps(x,ensure_ascii=False),flush=True)
def complete(ch):
    p=B/ch/'current.xml'
    if not p.exists():return True
    jid=E.parse(p).getroot().get('id');r=B/'results'/ch/jid/'report.xml'
    return r.exists()and E.parse(r).getroot().get('job')==jid and E.parse(r).getroot().get('status')in{'PASS','FAIL','TIMEOUT'}
def run(ch,ident):
    if not complete(ch):raise RuntimeError('Foreign incomplete queue: '+ch)
    p=B/ch/'current.xml';old=p.read_bytes()if p.exists()else None
    src=O/'native-extra'/ch/ident;dst=B/ch/ident
    if dst.exists():raise RuntimeError('Immutable job already exists: '+ident)
    shutil.copytree(src,dst);new=(dst/'job.xml').read_bytes()
    if (p.read_bytes()if p.exists()else None)!=old:raise RuntimeError('Concurrent queue change before submit')
    p.write_bytes(new);emit(dict(stage='SUBMITTED',channel=ch,id=ident))
    receipt=B/'results'/ch/ident/'report.xml';start=time.monotonic()
    while time.monotonic()-start<240:
        if p.read_bytes()!=new:raise RuntimeError('Foreign queue replaced current job; no restore')
        if receipt.exists():
            r=E.parse(receipt).getroot()
            if r.get('job')!=ident:raise RuntimeError('Receipt job mismatch')
            if r.get('status')not in{'PASS','FAIL','TIMEOUT'}:time.sleep(2);continue
            out=O/'native-evidence'/ch/ident;shutil.copytree(receipt.parent,out)
            emit(dict(stage='RECEIPT',channel=ch,id=ident,status=r.get('status'),receipt_sha256=sha(receipt),seconds=round(time.monotonic()-start,1)))
            if p.read_bytes()!=new:raise RuntimeError('Concurrent queue change before restore')
            if old is None:p.unlink()
            else:p.write_bytes(old)
            if r.get('status')!='PASS':raise RuntimeError('Native job did not pass: '+ident)
            return out
        time.sleep(2)
    emit(dict(stage='BLOCKED_NO_RECEIPT',channel=ch,id=ident,seconds=240));raise RuntimeError('No receipt; current job left intact. Do not blindly resubmit.')
lock=(B/'diagnostics/office-access-20261021-222308/check.lock').open('a+')
try:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for job in PLAN['jobs']:run(job['channel'],job['id'])
 emit(dict(stage='EXTRA_NATIVE_PASS'))
finally:lock.close()
