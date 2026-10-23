"""Serial Office queue client. Holds shared QA lock; never overwrites live foreign work."""
from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as E,fcntl,time,subprocess
O=Path('/home/denis/projects/nsp-qa03-20261023')
B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
PLAN=json.loads((O/'native-jobs/PLAN.json').read_text());log=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(x):
    log.append(x);(O/'NATIVE_PROGRESS.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n');print(json.dumps(x,ensure_ascii=False),flush=True)
def complete(ch):
    p=B/ch/'current.xml'
    if not p.exists():return True
    jid=E.parse(p).getroot().get('id');r=B/'results'/ch/jid/'report.xml'
    return r.exists()and E.parse(r).getroot().get('job')==jid and E.parse(r).getroot().get('status')in{'PASS','FAIL','TIMEOUT'}
def run(ch,ident):
    if not complete(ch):raise RuntimeError('Foreign incomplete queue: '+ch)
    p=B/ch/'current.xml';old=p.read_bytes()if p.exists()else None
    src=O/'native-jobs'/ch/ident;dst=B/ch/ident
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
    lines=subprocess.run(['journalctl','--user','-u','mb-excel-transport.service','--since','2 minutes ago','--no-pager'],capture_output=True,text=True,timeout=10).stdout
    if not all('GET /'+ch+'/current.xml' in lines for ch in['native','word']):raise RuntimeError('No fresh dual-channel laptop polling')
    (O/'PREFLIGHT_POLLING.txt').write_text(lines)
    for job in PLAN['jobs']:run(job['channel'],job['id'])
    # Reopen the file actually saved by Excel; do not regenerate it in Python.
    origin=O/'native-evidence/native'/PLAN['filled_source_job']/'q3x-filled.xlsx'
    ident='nsp-qa03-excel-reopen-v1-20261023';p=O/'native-jobs/native'/ident;p.mkdir(parents=True)
    shutil.copyfile(origin,p/'native-saved.xlsx')
    root=E.Element('job',id=ident,qa_only='true');f=E.SubElement(root,'file',name='native-saved.xlsx',tag='q3r',sheet='Реестр удержаний',sha256=sha(origin),export_source_first='true',print_preflight='true')
    c=E.SubElement(f,'case',name='native-saved-worked-example')
    for s,cs in PLAN['reopen_expected'].items():
        for cell,v in cs.items():E.SubElement(c,'expect',sheet=s,cell=cell,kind='number'if isinstance(v,(int,float))else'text',value=str(v))
    E.indent(root);E.ElementTree(root).write(p/'job.xml',encoding='utf-8',xml_declaration=True)
    run('native',ident)
    emit(dict(stage='ALL_NATIVE_JOBS_PASS',jobs=5))
except Exception as exc:
    emit(dict(stage='STOPPED',error=str(exc)))
    raise
finally:lock.close()
