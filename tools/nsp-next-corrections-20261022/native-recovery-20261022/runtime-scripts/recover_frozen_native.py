"""Frozen inputs preflight -> bounded native execution; no workbook authoring."""
from pathlib import Path
from copy import deepcopy
import subprocess,shutil,xml.etree.ElementTree as E,hashlib,json,time,datetime,fcntl
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
O=Q/'native-recovery-20261022';F=O/'frozen-inputs';F.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lock=(N/'diagnostics/office-access-20261021-222308/check.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
env={'__name__':'reviewed_submitter'};exec(compile(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/submit_office_review_job.py'],text=True),'reviewed_submitter','exec'),env)
assert env['previous_is_complete'](N,'native'),'PREVIOUS_PENDING'
source=Q/'prepared-office/native'
protected={f['accepted_sha256']for f in json.loads(subprocess.check_output(['git','-C',str(R),'show','637a22fe1b34ded1db64a929a363f0fad14d466e:tools/nsp-next-corrections-20261022/PROTECTED_ACCEPTED_MANIFEST.json'],text=True))['files']}
pending=[]
def freeze(rt,files):
 jid=rt.get('id');d=F/jid;d.mkdir(exist_ok=False)
 E.ElementTree(rt).write(d/'job.xml',encoding='utf-8',xml_declaration=True)
 assert (d/'job.xml').stat().st_size<=65536 and 1<=len(rt.findall('file'))<=4
 for f in rt.findall('file'):
  p=files[f.get('name')];assert sha(p)==f.get('sha256')and f.get('sha256')not in protected
  shutil.copyfile(p,d/f.get('name'));assert sha(d/f.get('name'))==f.get('sha256')
 pending.append(d)
# Preserved pending job11 exact XML from verified commit; use stable QA copy.
s=source/'nsp-next-excel-11-20261022'
expected=subprocess.check_output(['git','-C',str(R),'show','637a22fe1b34ded1db64a929a363f0fad14d466e:tools/nsp-next-corrections-20261022/prepared-office/native/'+s.name+'/job.xml'])
assert (s/'job.xml').read_bytes()==expected
rt=E.parse(s/'job.xml').getroot();freeze(rt,{f.get('name'):s/f.get('name')for f in rt.findall('file')})
# P2 revised test, immutable candidate.
s=Q/'native-resume-20261022/prepared-native/nsp-next-excel-5-coercion-v2-20261022'
rt=E.parse(s/'job.xml').getroot();freeze(rt,{f.get('name'):s/f.get('name')for f in rt.findall('file')})
# T2: numerical text COM coercion is distinct from nonnumeric text.
s=source/'nsp-next-excel-8-20261022';rt=E.parse(s/'job.xml').getroot();rt.set('id','nsp-next-excel-8-coercion-v2-20261022')
f=rt.find('file');c=next(x for x in f.findall('case')if x.get('name')=='text');c.set('name','numeric-string-coercion');x=c.find('expect');x.set('kind','number');x.set('value','3');E.SubElement(c,'expect',sheet='Опись',cell='F11',kind='number',value='3')
neg=deepcopy(c);neg.set('name','nonnumeric-text')
next(x for x in neg.findall('set')if x.get('cell')=='F11'and x.get('kind')=='text').set('value','три')
for x in list(neg.findall('expect')):neg.remove(x)
E.SubElement(neg,'expect',sheet='Опись',cell='E132',kind='text',value='ПРОВЕРЬТЕ СТРОКИ');f.append(neg)
freeze(rt,{f.get('name'):s/f.get('name')})
# New negative controls for exact held free candidates; no change of workbook bytes.
rt=E.Element('job',id='nsp-free-negative-controls-20261022',qa_only='true',hypothesis='Native blank, partial, negative, fractional and nonnumeric inputs with immutable held files')
files={}
def addcase(f,name,clear,inputs,expected):
 c=E.SubElement(f,'case',name=name)
 for addr in clear:E.SubElement(c,'set',cell=addr,kind='blank',value='')
 for addr,value in inputs.items():E.SubElement(c,'set',cell=addr,kind='text'if isinstance(value,str)else 'number',value=str(value))
 for addr,value in expected.items():E.SubElement(c,'expect',cell=addr,kind='blank'if value==''else'text'if isinstance(value,str)else'number',value=str(value))
for i in [10,11]:
 s=source/('nsp-next-excel-'+str(i)+'-20261022');old=E.parse(s/'job.xml').getroot().find('file');f=E.SubElement(rt,'file',dict(old.attrib));f.set('tag','free'+str(i));files[f.get('name')]=s/f.get('name')
 if i==10:
  clear=[str(c)+str(r)for r in range(2,5)for c in 'CDEF']
  good={'C2':'Работа','D2':150,'E2':'м2','F2':850}
  specs=[('empty',{}, {'G5':'','I5':''}),('single',good,{'G5':127500,'I5':'Расчёт заполнен'}),('additional',{**good,'C3':'Допработа','D3':20,'E3':'шт','F3':1000},{'G5':147500}),('missing-price',{k:v for k,v in good.items()if k!='F2'},{'G5':'','I5':'Проверьте строки'}),('negative-volume',{**good,'D2':-1},{'G5':'','I5':'Проверьте строки'}),('nonnumeric-price',{**good,'F2':'цена'},{'G5':'','I5':'Проверьте строки'}),('missing-unit',{k:v for k,v in good.items()if k!='E2'},{'G5':'','I5':'Проверьте строки'}),('rounding',{**good,'D2':1.5,'F2':1.25},{'G5':1.88})]
 else:
  clear=[str(c)+str(r)for r in range(2,7)for c in 'BCDE']
  good={a:v for r,vv in enumerate([3,2,5,1],2)for a,v in [('B'+str(r),'Документ '+str(r)),('E'+str(r),vv)]}
  specs=[('empty',{}, {'E7':'','G7':''}),('baseline',good,{'E7':11,'G7':'Листаж проверен'}),('additional',{**good,'B6':'Пятое приложение','E6':4},{'E7':15}),('negative',{**good,'E2':-1},{'E7':'','G7':'Проверьте строки'}),('fraction',{**good,'E2':1.5},{'E7':'','G7':'Проверьте строки'}),('nonnumeric',{**good,'E2':'три'},{'E7':'','G7':'Проверьте строки'}),('count-without-document',{'E2':3},{'E7':'','G7':'Проверьте строки'}),('missing-count',{'B2':'Документ'},{'E7':'','G7':'Проверьте строки'})]
 for name,inp,ex in specs:addcase(f,name,clear,inp,ex)
 pn=E.SubElement(f,'print')
 for addr,value in good.items():E.SubElement(pn,'set',cell=addr,kind='text'if isinstance(value,str)else'number',value=str(value))
freeze(rt,files)
# All dependencies verified and copied before the first submission.
manifest=[{'id':d.name,'job_sha256':sha(d/'job.xml'),'files':[dict(f.attrib)for f in E.parse(d/'job.xml').getroot().findall('file')]}for d in pending]
(O/'FROZEN_PREFLIGHT.json').write_text(json.dumps({'status':'PASS','source_head':'637a22fe1b34ded1db64a929a363f0fad14d466e','jobs':manifest,'rule':'No Git checkout/ref mutation while any job depends on its working tree; native jobs depend only on frozen input directory'},ensure_ascii=False,indent=2))
records=[]
def save():(O/'RECOVERY_V2_STATE.json').write_text(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':records,'masters_changed':False},ensure_ascii=False,indent=2))
for d in pending:
 jid=d.name;dest=N/'native'/jid;rp=N/'results/native'/jid/'report.xml';rec={'id':jid};records.append(rec)
 assert env['previous_is_complete'](N,'native'),'PREVIOUS_PENDING'
 if not rp.exists():
  assert not dest.exists(),'JOB_DIRECTORY_EXISTS_REQUIRE_REVIEW'
  shutil.copytree(d,dest);env['submit'](N,'native',dest);rec['status']='SUBMITTED';save();print('SUBMITTED',jid,flush=True)
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
