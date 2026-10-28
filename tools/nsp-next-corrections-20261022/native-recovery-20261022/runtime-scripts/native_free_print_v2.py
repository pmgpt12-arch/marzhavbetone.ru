from pathlib import Path
import xml.etree.ElementTree as E,hashlib,json,subprocess,shutil,time
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');R=Q.parent/'integration-20261022/repo'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert env['previous_is_complete'](N,'native'),'PREVIOUS_PENDING'
rt=E.parse(O/'frozen-inputs/nsp-free-negative-controls-20261022/job.xml').getroot();jid='nsp-free-print-v2-20261022';rt.set('id',jid);rt.set('scope','Exact formulas retained; metadata-only print revision plus same 16 native numeric/negative scenarios')
d=O/'frozen-inputs'/jid;d.mkdir(exist_ok=False)
manifest=json.loads((O/'free-print-v2/PRINT_PATCH_MANIFEST.json').read_text())
for f in rt.findall('file'):
 r=next(x for x in manifest if x['file']==f.get('name'));src=O/'free-print-v2'/r['file'];assert sha(src)==r['new_sha256'];f.set('sha256',r['new_sha256']);f.set('tag','fp'+f.get('tag')[4:]);shutil.copyfile(src,d/src.name)
E.ElementTree(rt).write(d/'job.xml',encoding='utf-8',xml_declaration=True)
dest=N/'native'/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,'native',dest);print('SUBMITTED',jid,flush=True)
rp=N/'results/native'/jid/'report.xml';deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/'native/current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
assert rp.exists(),'NO_RECEIPT_AFTER_240S'
r=E.parse(rp).getroot();assert r.get('job')==jid;shutil.copytree(rp.parent,O/'evidence/native'/jid,dirs_exist_ok=True)
results={'job':jid,'status':r.get('status'),'report_sha256':sha(rp),'checks':len(r.findall('check')),'failed':[dict(x.attrib)for x in r.findall('check')if x.get('pass','').lower()!='true'],'pdfs':[]}
for f in rt.findall('file'):
 p=rp.parent/(f.get('tag')+'-filled.pdf');info=subprocess.check_output(['pdfinfo',str(p)],text=True);out=O/'visual-free-print-v2';out.mkdir(exist_ok=True)
 subprocess.run(['pdftoppm','-scale-to','1400','-png',str(p),str(out/f.get('tag'))],check=True,capture_output=True,timeout=30)
 results['pdfs'].append({'file':f.get('name'),'source_sha256':f.get('sha256'),'pdf_sha256':sha(p),'pdf_info':info,'visual_review':'PENDING'})
(O/'FREE_EXCEL_PRINT_V2_NATIVE.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False),flush=True)
