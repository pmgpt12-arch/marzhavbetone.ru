"""Run only after owner confirms normal Word/Excel startup. Uses existing reviewed transport."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess,time,xml.etree.ElementTree as E
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');R=Q.parent/'integration-20261022/repo';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert len(sys.argv)==2 and sys.argv[1]in('native','word'),'Usage: retry_office_after_owner.py native|word'
channel=sys.argv[1];jid={'native':'nsp-p5-final-print-r1-20261023','word':'nsp-p11-final-letters-r1-20261023'}[channel];d=P/'deferred-office-jobs'/jid;job=E.parse(d/'job.xml').getroot();assert job.get('id')==jid
files=job.findall('file');assert 1<=len(files)<=4
for f in files:
 p=d/f.get('name');assert p.is_file()and sha(p)==f.get('sha256')
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert env['previous_is_complete'](N,channel),'Active/unfinished previous job; do not overwrite'
dest=N/channel/jid;assert not dest.exists(),'Immutable id already used; inspect existing receipt instead of resubmitting'
shutil.copytree(d,dest);env['submit'](N,channel,dest);print('SUBMITTED',jid,flush=True)
rp=N/'results'/channel/jid/'report.xml';deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/channel/'current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
status={'job':jid,'channel':channel,'status':'NO_RECEIPT','files':[],'scope':'Only exact source SHA; no UI or manual locale claim'}
if not rp.exists():
 (P/('RETRY_'+channel.upper()+'.json')).write_text(json.dumps(status,ensure_ascii=False,indent=2));raise SystemExit('NO_RECEIPT; leave current.xml unchanged; no automatic retry')
rt=E.parse(rp).getroot();assert rt.get('job')==jid;shutil.copytree(rp.parent,P/'evidence'/channel/jid,dirs_exist_ok=True);status.update(status=rt.get('status'),receipt_sha256=sha(rp),error=rt.findtext('error'),checks=[dict(c.attrib)for c in rt.findall('check')])
# Primary failure recorded before touching optional output files.
if rt.get('status')!='PASS':
 status['file_receipts']=[dict(f.attrib)for f in rt.findall('file')];(P/('RETRY_'+channel.upper()+'.json')).write_text(json.dumps(status,ensure_ascii=False,indent=2));print(json.dumps(status,ensure_ascii=False),flush=True);raise SystemExit(2)
for f in files:
 tag=f.get('tag')
 if channel=='word':
  fr=next(x for x in rt.findall('file')if x.get('tag')==tag);assert fr.get('status')=='PASS'and fr.find('result').get('source_sha256')==f.get('sha256')
  pdf=rp.parent/(tag+'.pdf');assert sha(pdf)==fr.get('pdf_sha256')
 else:
  assert all(c.get('pass','').lower()=='true'for c in rt.findall('check'))
  assert any(c.get('name')==tag+':source_unchanged'and c.get('actual')==f.get('sha256')for c in rt.findall('check'))
  pdf=rp.parent/(tag+'-filled.pdf')
 assert pdf.is_file();v=P/('visual-'+jid);v.mkdir(exist_ok=True);subprocess.run(['pdftoppm','-scale-to','1400','-png',str(pdf),str(v/tag)],check=True,capture_output=True,timeout=60)
 status['files'].append({'file':f.get('name'),'source_sha256':f.get('sha256'),'pdf_sha256':sha(pdf),'pdf_info':subprocess.check_output(['pdfinfo',str(pdf)],text=True),'visual_review':'PENDING'})
(P/('RETRY_'+channel.upper()+'.json')).write_text(json.dumps(status,ensure_ascii=False,indent=2));print(json.dumps(status,ensure_ascii=False),flush=True)
