#!/usr/bin/env python3
from pathlib import Path
from lxml import etree as ET
import hashlib,json,os,re,shutil,subprocess,time
from datetime import datetime,timezone,timedelta
ROOT=Path('/home/denis/projects/mb001-p11-ics-cleanup-20261014');C=ROOT/'tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami';E=ROOT/'tools/candidates/portfolio-owner-pdf-20261013/p11-50-53-ics-cleanup-20261014';B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
JOB='p11-50-53-ics-cleanup-word-20261014-v1';FILES=[('50-slovar-poley-raschet-metrami.docx','50','6f40e5d3757d77d6460efb990f459167220f5fb9f3f36a6a6bcfb92b415869d5'),('53-zapros-status-obekta.docx','53','c3fccbdc5e7e6841ca8c48b5ab1c199bdebe0d2f4990c232040d20f70bfc023e')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fd(p):
 with p.open('rb') as f:os.fsync(f.fileno())
def dd(p):d=os.open(p,os.O_RDONLY);os.fsync(d);os.close(d)
def atomic(p,b):
 t=p.with_name(p.name+'.tmp')
 with t.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p);dd(p.parent)
def aj(p,o):atomic(p,(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 D=B/'word'/JOB;R=B/'results/word'/JOB;current=B/'word/current.xml';assert not D.exists() and not R.exists()
 old=current.read_bytes();prev=ET.fromstring(old).get('id');assert (B/'results/word'/prev/'report.xml').exists()
 log=max(B.glob('transport*.log'),key=lambda p:p.stat().st_mtime);polls=[x for x in log.read_text(errors='replace').splitlines()[-120:] if '192.168.1.140' in x and 'GET /word/current.xml HTTP/1.0" 204' in x];assert polls
 stamp=re.search(r'\[(.*?)\]',polls[-1]).group(1);at=datetime.strptime(stamp,'%d/%b/%Y %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=7))).timestamp();assert 0<=time.time()-at<=90
 aj(E/'native-passport.json',{'schema_version':1,'id':'P11-50-53-ICS-NATIVE','status':'PREPARED','prepared_at':datetime.now(timezone.utc).isoformat(),'job':JOB,'inputs':{n:s for n,t,s in FILES},'executor':{'path':str(Path(__file__)),'sha256':sha(Path(__file__))},'previous_job':prev,'idle_poll':polls[-1],'acceptance':['exact SHA Word PASS 2/2','50 remains 2 pages, 53 remains 3 pages','all five pages visually reviewed','no clipping/overlap; graphite/no italic','independent review pending'],'checkpoint_policy':'verified_only','release':'HOLD'})
 job=ET.Element('job',id=JOB);D.mkdir()
 for n,t,s in FILES:
  src=C/n;assert sha(src)==s;dst=D/n;shutil.copy2(src,dst);fd(dst);ET.SubElement(job,'file',name=n,tag=t,sha256=s)
 xml=ET.tostring(job,encoding='utf-8',xml_declaration=True);atomic(D/'job.xml',xml);stage={'schema_version':1,'job':JOB,'status':'STAGED_NOT_SUBMITTED','previous_job':prev,'idle_poll':polls[-1],'inputs':{n:s for n,t,s in FILES}}
 aj(D/'stage-receipt.json',stage);assert current.read_bytes()==old;atomic(current,xml);stage['status']='SUBMITTED_AWAITING_RESULT';stage['submitted_at']=datetime.now(timezone.utc).isoformat();aj(D/'stage-receipt.json',stage)
 start=time.monotonic()
 while not (R/'report.xml').exists() and time.monotonic()-start<120:time.sleep(4)
 if not (R/'report.xml').exists():raise TimeoutError('No result; inspect late result, do not retry')
 rep=ET.parse(str(R/'report.xml')).getroot();assert rep.get('job')==JOB;N=E/'native';N.mkdir()
 for p in R.iterdir():
  if p.is_file():shutil.copy2(p,N/p.name);fd(N/p.name)
 for pdf in N.glob('*.pdf'):subprocess.run(['pdftoppm','-png','-r','120',str(pdf),str(N/pdf.stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 for p in N.glob('*.png'):fd(p)
 dd(N);outs={p.name:sha(p) for p in sorted(N.iterdir()) if p.is_file()};aj(E/'native-receipt.json',{'schema_version':1,'job':JOB,'status':rep.get('status'),'inputs':{n:s for n,t,s in FILES},'outputs':outs,'finished_at':datetime.now(timezone.utc).isoformat(),'visual_review':'PENDING','release':'HOLD'});atomic(E/'native-exit.code',b'0\n' if rep.get('status')=='PASS' else b'1\n')
 print(json.dumps({'job':JOB,'status':rep.get('status'),'outputs':outs},ensure_ascii=False));return 0 if rep.get('status')=='PASS' else 1
try:raise SystemExit(main())
except Exception as exc:aj(E/'native-failure.json',{'schema_version':1,'job':JOB,'status':'FAIL','error_type':type(exc).__name__,'error':str(exc),'finished_at':datetime.now(timezone.utc).isoformat(),'release':'HOLD'});atomic(E/'native-exit.code',b'1\n');raise
