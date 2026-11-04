from pathlib import Path
import json,hashlib,shutil,subprocess,time,xml.etree.ElementTree as E
Q=Path(__file__).resolve().parents[1];O=Q/'paid-followup-20261023';R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert env['previous_is_complete'](N,'word')
jid='nsp-p11-letter-layout-v3-20261023';d=O/'frozen-inputs'/jid;d.mkdir(exist_ok=False);root=E.Element('job',id=jid,qa_only='true')
rows=json.loads((O/'P11_LAYOUT_V3.json').read_text())
for i,r in enumerate(rows,1):
 p=O/'p11-layout-v3'/r['path'];assert sha(p)==r['new_sha256'];shutil.copyfile(p,d/p.name);E.SubElement(root,'file',name=p.name,tag='pv'+str(i),sha256=r['new_sha256'])
E.ElementTree(root).write(d/'job.xml',encoding='utf-8',xml_declaration=True)
dest=N/'word'/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,'word',dest);print('SUBMITTED',jid,flush=True)
rp=N/'results/word'/jid/'report.xml';deadline=time.monotonic()+240
while time.monotonic()<deadline:
 assert E.parse(N/'word/current.xml').getroot().get('id')==jid
 if rp.exists():break
 time.sleep(3)
assert rp.exists(),'NO_RECEIPT_AFTER_240S'
report=E.parse(rp).getroot();assert report.get('job')==jid;shutil.copytree(rp.parent,O/'evidence/word'/jid,dirs_exist_ok=True)
out=[]
for f in report.findall('file'):
 tag=f.get('tag');p=rp.parent/(tag+'.pdf');assert sha(p)==f.get('pdf_sha256');src=next(x for x in root.findall('file')if x.get('tag')==tag);assert f.find('result').get('source_sha256')==src.get('sha256')
 vd=O/'visual-p11-layout-v3';vd.mkdir(exist_ok=True);subprocess.run(['pdftoppm','-scale-to','1200','-png',str(p),str(vd/tag)],check=True,capture_output=True,timeout=40)
 out.append({'file':src.get('name'),'sha256':src.get('sha256'),'status':f.get('status'),'pdf_sha256':sha(p),'actual_pages':len(list(vd.glob(tag+'-*.png'))),'native_word_job':jid,'links':subprocess.check_output(['pdfinfo','-url',str(p)],text=True),'visual_review':'PENDING'})
(O/'P11_LAYOUT_NATIVE_V3.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('RECEIVED',report.get('status'),out,flush=True)
