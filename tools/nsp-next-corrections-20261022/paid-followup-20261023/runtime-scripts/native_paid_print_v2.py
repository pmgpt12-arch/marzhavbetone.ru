from pathlib import Path
import xml.etree.ElementTree as E,hashlib,json,subprocess,shutil,time,copy
import re
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';O=Q/'native-recovery-20261022';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');R=Q.parent/'integration-20261022/repo';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert env['previous_is_complete'](N,'native')
jid='nsp-p5-print-v2-20261023';rt=E.Element('job',id=jid,qa_only='true',scope='Metadata-only print repair, unchanged 14 source scenarios, source-first PDF')
D=P/'frozen-inputs'/jid;D.mkdir(exist_ok=False)
rows=json.loads((P/'paid-print-v2/MANIFEST.json').read_text())
for r in rows:
 src=P/'paid-print-v2'/r['file'];assert sha(src)==r['new_sha256'];old=O/'frozen-inputs'/('nsp-next-excel-'+str(r['source_job'])+'-20261022')/'job.xml';f=copy.deepcopy(E.parse(old).getroot().find('file'));f.set('tag','pp'+str(r['source_job']));f.set('sha256',r['new_sha256']);f.set('export_source_first','true');f.set('print_preflight','true');rt.append(f);shutil.copy2(src,D/src.name)
E.ElementTree(rt).write(D/'job.xml',encoding='utf-8',xml_declaration=True)
dest=N/'native'/jid;assert not dest.exists();shutil.copytree(D,dest);env['submit'](N,'native',dest);print('SUBMITTED',jid,flush=True)
rp=N/'results/native'/jid/'report.xml';deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/'native/current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
assert rp.exists(),'NO_RECEIPT_AFTER_240S'
report=E.parse(rp).getroot();assert report.get('job')==jid;shutil.copytree(rp.parent,P/'evidence/native'/jid,dirs_exist_ok=True)
results={'job':jid,'status':report.get('status'),'scenarios':len(rt.findall('file/case')),'checks':len(report.findall('check')),'failed':[dict(c.attrib)for c in report.findall('check')if c.get('pass','').lower()!='true'],'report_sha256':sha(rp),'files':[]}
V=P/'visual-paid-print-v2';V.mkdir(exist_ok=True)
for f in rt.findall('file'):
 tag=f.get('tag');pdf=rp.parent/(tag+'-filled.pdf');assert pdf.exists()
 info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);pages=int(re.search(r'Pages:\\s+(\\d+)',info).group(1));txt=subprocess.check_output(['pdftotext',str(pdf),'-'],text=True)
 areas=[dict(n.attrib)for n in report.findall('print_preflight')if n.get('tag')==tag for n in n.findall('sheet')]
 subprocess.run(['pdftoppm','-scale-to','1400','-png',str(pdf),str(V/tag)],capture_output=True,check=True,timeout=60)
 results['files'].append({'file':f.get('name'),'source_sha256':f.get('sha256'),'pdf_sha256':sha(pdf),'pages':pages,'pdf_info':info,'helper_O_visible':'Ключ отбора'in txt if tag=='pp2'else None,'native_print_areas':areas,'visual_review':'PENDING'})
(P/'P5_PRINT_V2_NATIVE.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False),flush=True)