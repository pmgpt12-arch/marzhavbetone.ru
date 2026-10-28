"""Reopen native saved copies; verify cached output equivalence and source identities."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as E,subprocess,json,hashlib,shutil,time,fcntl
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011');O=Q/'native-recovery-20261022'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert env['previous_is_complete'](N,'native'),'PREVIOUS_PENDING'
items=[]
for i in range(1,12):
 jp=Q/'prepared-office/native'/('nsp-next-excel-'+str(i)+'-20261022')/'job.xml';f=E.parse(jp).getroot().find('file');job=jp.parent.name;tag=f.get('tag')
 if i==10:job='nsp-free-negative-controls-20261022';tag='free10'
 if i==11:job='nsp-free-negative-controls-20261022';tag='free11'
 p=N/'results/native'/job/(tag+'-filled.xlsx');assert p.is_file()
 with ZipFile(p)as z:
  assert z.testzip()is None
  wb=E.fromstring(z.read('xl/workbook.xml'));rels={x.get('Id'):x.get('Target')for x in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))};sheets={}
  for s in wb.find('s:sheets',ns):
   target=rels[s.get('{'+ns['r']+'}id')];part=target.lstrip('/')if target.startswith('/')else'xl/'+target
   sheets[s.get('name')]=E.fromstring(z.read(part))
  ss=[''.join(t.itertext())for t in E.fromstring(z.read('xl/sharedStrings.xml'))]if'xl/sharedStrings.xml'in z.namelist()else[]
  ex=[]
  pairs=[]
  for x in f.findall('.//expect'):
   pair=(x.get('sheet',f.get('sheet')),x.get('cell'))
   if pair not in pairs:pairs.append(pair)
  if i==10:pairs=[(f.get('sheet'),'G5'),(f.get('sheet'),'I5')]
  if i==11:pairs=[(f.get('sheet'),'E7'),(f.get('sheet'),'G7')]
  for sn,addr in pairs[:6]:
   c=sheets[sn].find('.//s:c[@r="'+addr+'"]',ns);typ=c.get('t')if c is not None else None;v=c.findtext('s:v',default='',namespaces=ns)if c is not None else''
   assert typ!='e',('CACHED_ERROR',i,sn,addr,v)
   if typ=='s':v=ss[int(v)]
   if typ=='inlineStr':v=''.join(c.find('s:is',ns).itertext())
   kind='blank'if v==''else'text'if typ in ['s','inlineStr','str']else'number'
   ex.append({'sheet':sn,'cell':addr,'kind':kind,'value':v})
 items.append({'i':i,'path':str(p),'sha256':sha(p),'source_candidate_sha256':f.get('sha256'),'sheet':f.get('sheet'),'expectations':ex})
(O/'REOPEN_INPUTS.json').write_text(json.dumps(items,ensure_ascii=False,indent=2))
prepared=[]
for batch,start in enumerate(range(0,len(items),4),1):
 jid='nsp-native-reopen-b'+str(batch)+'-20261022';d=O/'frozen-inputs'/jid;d.mkdir(exist_ok=False);rt=E.Element('job',id=jid,qa_only='true',scope='REOPEN_NATIVE_SAVED_COPIES_CACHED_OUTPUT_EQUIVALENCE_NOT_INDEPENDENT_FORMULA_OR_PRINT_ACCEPTANCE')
 for it in items[start:start+4]:
  name='reopen-'+str(it['i'])+'.xlsx';p=Path(it['path']);shutil.copyfile(p,d/name);assert sha(d/name)==it['sha256'];f=E.SubElement(rt,'file',name=name,tag='r'+str(it['i']),sheet=it['sheet'],sha256=it['sha256'],export_source_first='true');c=E.SubElement(f,'case',name='saved-output-equivalence')
  for ex in it['expectations']:E.SubElement(c,'expect',ex)
 E.ElementTree(rt).write(d/'job.xml',encoding='utf-8',xml_declaration=True);prepared.append(d)
records=[]
def save():(O/'REOPEN_STATE.json').write_text(json.dumps({'records':records,'scope':'Saved-copy reopen and output equivalence; print still requires acceptance'},ensure_ascii=False,indent=2))
for d in prepared:
 jid=d.name;rp=N/'results/native'/jid/'report.xml';assert env['previous_is_complete'](N,'native');assert not rp.exists();dest=N/'native'/jid;assert not dest.exists();shutil.copytree(d,dest);env['submit'](N,'native',dest);rec={'id':jid,'status':'SUBMITTED'};records.append(rec);save();print('SUBMITTED',jid,flush=True);until=time.monotonic()+240
 while time.monotonic()<until:
  assert E.parse(N/'native/current.xml').getroot().get('id')==jid
  if rp.exists():break
  time.sleep(3)
 if not rp.exists():rec['status']='NO_RECEIPT_AFTER_240S';save();print('STOP_NO_RECEIPT',jid,flush=True);break
 rt=E.parse(rp).getroot();assert rt.get('job')==jid;rec.update(status=rt.get('status'),checks=len(rt.findall('check')),failed=[dict(x.attrib)for x in rt.findall('check')if x.get('pass','').lower()!='true'],report_sha256=sha(rp));shutil.copytree(rp.parent,O/'evidence/native'/jid,dirs_exist_ok=True);save();print('RECEIVED',jid,rec,flush=True)
print('FINISHED',flush=True)
