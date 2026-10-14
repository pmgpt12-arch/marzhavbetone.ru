#!/usr/bin/env python3
"""P11 F02/F03: exact-anchor delta. No prices, canonical or service changes."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from copy import deepcopy
from lxml import etree as ET
import argparse, hashlib, json, re, subprocess, datetime, os, time
R=Path('/home/denis/projects/mb001-p11-normative-delta-20261013')
C=R/'tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami'
E=C.parent/'p11-f02-f03-20261014'
B=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
BASE='cfbc4e3edcf438250bac98a2df04133d96bb27b3'
JOB='p11-f02-f03-word-20261014-v1'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
RULE='Правило комплекта: каждый красный флаг — правовая оценка. Два и более — СТОП: до проверки не подписывайте сделку и не начинайте работы в счёт недвижимости. Возобновление — после документальной проверки рисков, согласования мер защиты, включая обеспечение, и письменного решения руководителя. Правовые препятствия должны быть устранены.'
BOUNDARY='Уступка права на получение объекта допускается с момента государственной регистрации ДДУ до подписания сторонами передаточного акта или иного документа о передаче объекта (ч. 2 ст. 11 Закона № 214-ФЗ). Передача уже оформлена либо стадия не подтверждена — СТОП до определения применимой формы сделки. Ввод дома сам по себе не означает передачу объекта.'
FILES={'51':'51-algoritm-raschet-metrami.docx','52':'52-chek-list-raschet-metrami.docx','55':'55-pamyatka-punkt-ustupki-escrow.docx'}
PATCH={
 '51':[
  ('При отметке «→ юрист» получите правовую оценку до подписания документов. Алгоритм не запрещает расчёт метрами: он делает видимым, что именно предлагают, и переводит решение из «по старой памяти» в решение по проверенным фактам.',RULE),
  ('До регистрации права требования у подрядчика нет ничего.',BOUNDARY),
  ('Развилка: срок ввода уже переносился, разрешение на исходе или истекло, дом не принят надзором (ЗОС не выдано) → каждый пункт — самостоятельный красный флаг. Два и больше → входить только с юристом и обеспечением (шаг 6).','Развилка: перенос ввода, истекающее или истёкшее разрешение, неснятые замечания надзора — поводы проверить риски. При двух и более флагах действует СТОП по правилу раздела «Граница применения». Проверка с юристом и наличие обеспечения сами по себе не разрешают подписать сделку.')],
 '52':[
  ('☐  Проект договора и уступки получен на руки до начала работ.','☐  Получены проекты договора и уступки. Проверены регистрация ДДУ и отсутствие подписанного сторонами передаточного акта или иного документа о передаче объекта (ч. 2 ст. 11 Закона № 214-ФЗ). Передача оформлена или стадия не подтверждена — СТОП до определения применимой формы сделки.'),
  ('☐  Проект сделки смотрел юрист (не юрист застройщика).','☐  Проект сделки проверен независимым от застройщика юристом. '+RULE),
  ('7. Красные флаги — каждый требует юриста, два и больше — стоп','7. Красные флаги — правило остановки в разделе 6')],
 '55':[
  ('— Конкретный проект договора проверьте с юристом.','— До подписания проверьте стадию передачи. '+BOUNDARY),
  ('Граница проходит по стадии. Пока сделка обсуждается и бумаги не подписаны — комплект работает. Уступка уже подписана и идёт спор — дальше работа юриста по конкретным документам. Застройщик в процедуре банкротства — это комплект «Реестр требований кредиторов» и юрист, а не эти файлы.','Порядок применяется до подписания документов. По уже заключённой сделке и при банкротстве правовую позицию определяют отдельно по её документам и фактической стадии передачи объекта.')]
}
sha=lambda b:hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(cmd,timeout=12):
 p=subprocess.run(cmd,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError(f'{cmd[0]} exit={p.returncode}: {p.stderr.decode(errors="replace")[:1000]}')
 return p.stdout
def read_doc(data):
 with ZipFile(BytesIO(data)) as z:
  assert z.testzip() is None
  return ET.fromstring(z.read('word/document.xml'))
def pars(tree):return tree.find(W+'body').findall(W+'p')
def txt(p):return ''.join(t.text or '' for t in p.iter(W+'t'))
def alltext(tree):return '\n'.join(tree.itertext()) if False else '\n'.join(txt(p) for p in tree.iter(W+'p'))
def settext(p,text):
 nodes=list(p.iter(W+'t'));assert nodes
 nodes[0].text=text
 for n in nodes[1:]:n.text=''
def validate(trees):
 texts={k:alltext(v) for k,v in trees.items()};checks={}
 for k,t in texts.items():
  matches=[txt(p) for p in pars(trees[k]) if 'ч. 2 ст. 11 Закона № 214-ФЗ' in txt(p)]
  checks[k+'_one_boundary']=len(matches)==1
  b=matches[0] if len(matches)==1 else ''
  checks[k+'_registration_and_transfer']=all(x in b for x in ('регистрац','передаточного акта','иного документа о передаче объекта','СТОП','стадия не подтверждена'))
  checks[k+'_part3_preserved']='ч. 3 ст. 11 Закона № 214-ФЗ' in t
 for k in ('51','52'):
  checks[k+'_unified_stop_resume']=texts[k].count(RULE)==1
 checks['51_no_old_permission']='Два и больше → входить только с юристом и обеспечением' not in texts['51']
 checks['52_heading_preserved']=sum(txt(p)=='7. Красные флаги — правило остановки в разделе 6' and p.find(W+'pPr/'+W+'pStyle') is not None and p.find(W+'pPr/'+W+'pStyle').get(W+'val')=='Heading2' for p in pars(trees['52']))==1
 return checks
def tests(trees):
 positive=validate(trees);negative={}
 for k in FILES:
  for phrase in ('ч. 2 ст. 11 Закона № 214-ФЗ','передаточного акта','СТОП'):
   t=deepcopy(trees);target=next(p for p in pars(t[k]) if 'ч. 2 ст. 11 Закона № 214-ФЗ' in txt(p));before=txt(target);assert phrase in before
   settext(target,before.replace(phrase,'УДАЛЕНО',1));negative[k+'_'+phrase]=not all(validate(t).values())
 for k in ('51','52'):
  for phrase in ('Два и более — СТОП','письменного решения руководителя','Правовые препятствия должны быть устранены.'):
   t=deepcopy(trees);target=next(p for p in pars(t[k]) if RULE in txt(p));settext(target,txt(target).replace(phrase,'УДАЛЕНО',1));negative[k+'_'+phrase]=not all(validate(t).values())
 return positive,negative
def prepare():
 assert run(['git','-C',str(R),'rev-parse','HEAD']).decode().strip()==BASE
 assert not run(['git','-C',str(R),'status','--porcelain']).strip(),'Worktree dirty: inspect first'
 assert not E.exists() and not (B/'word'/JOB).exists() and not (B/'results/word'/JOB).exists()
 prepared={};records=[];beforetrees={}
 for k,name in FILES.items():
  p=C/name;data=p.read_bytes();blob=run(['git','-C',str(R),'show',BASE+':'+str(p.relative_to(R))]);assert data==blob
  tree=read_doc(data);beforetrees[k]=deepcopy(tree);edits=[]
  for before,after in PATCH[k]:
   matches=[x for x in pars(tree) if txt(x)==before];assert len(matches)==1,(name,before[:55],len(matches))
   target=matches[0];style=ET.tostring(target.find(W+'pPr')) if target.find(W+'pPr') is not None else None
   settext(target,after)
   assert (ET.tostring(target.find(W+'pPr')) if target.find(W+'pPr') is not None else None)==style
   edits.append({'before':before,'after':after,'selector':'unique exact paragraph text','paragraph_position_for_audit_only':pars(tree).index(target)})
  with ZipFile(BytesIO(data)) as z:
   output=BytesIO()
   with ZipFile(output,'w') as w:
    for member in z.infolist():w.writestr(deepcopy(member),ET.tostring(tree,encoding='utf-8') if member.filename=='word/document.xml' else z.read(member.filename))
   result=output.getvalue()
   with ZipFile(BytesIO(result)) as zz:
    assert zz.testzip() is None and z.namelist()==zz.namelist()
    changed=[n for n in z.namelist() if z.read(n)!=zz.read(n)];assert changed==['word/document.xml']
  unchanged=[txt(x) for x in pars(beforetrees[k]) if txt(x) not in [v[0] for v in PATCH[k]]]
  current=[txt(x) for x in pars(tree) if txt(x) not in [v[1] for v in PATCH[k]]];assert unchanged==current
  prepared[k]=(p,result,tree,data)
  records.append({'key':k,'path':str(p.relative_to(R)),'before_sha256':sha(data),'after_sha256':sha(result),'edits':edits,'changed_zip_parts':changed})
 pos,neg=tests({k:x[2] for k,x in prepared.items()});assert all(pos.values()) and all(neg.values())
 assert not all(validate(beforetrees).values()),'Baseline must demonstrate defects'
 E.mkdir();(E/'before').mkdir()
 for k,(p,result,tree,data) in prepared.items():
  (E/'before'/p.name).write_bytes(data);tmp=p.with_suffix('.docx.f02.tmp');assert not tmp.exists();tmp.write_bytes(result);os.replace(tmp,p);assert sha(p.read_bytes())==sha(result)
 source={'law':'214-ФЗ, ч. 2 ст. 11','url':'https://www.consultant.ru/document/cons_doc_LAW_51038/26e3de2d783e453c4faf7fb26c33eecafddc2307/','access_date':'2026-10-14','edition_observed':'09.04.2026','rule':'Для уступки права на получение объекта проверяется период от государственной регистрации ДДУ до подписания сторонами передаточного акта либо иного документа о передаче. Ввод дома не приравнивается к передаче.','source_check':'Read using web tool; statutory text at article 11 part 2','risk_policy':'Unified stop/resume rule is a product risk-management rule, not a statutory two-flag threshold'}
 (E/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
 (E/'delta.json').write_text(json.dumps({'base_commit':BASE,'scope':'F02_TRANSFER_BOUNDARY_AND_F03_STOP_RULE_ONLY','records':records,'author_review_not_independent':True,'native_status':'NOT_RUN','release':'HOLD'},ensure_ascii=False,indent=2)+'\n')
 (E/'static.json').write_text(json.dumps({'positive':pos,'negative_detected':neg,'baseline_detected':True,'scope':'STATIC_REGRESSION_ONLY'},ensure_ascii=False,indent=2)+'\n')
 (E/'execution.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps({'status':'PREPARED_VERIFIED','docx':3,'positive':len(pos),'negative_detected':len(neg),'sha256':{x['key']:x['after_sha256'] for x in records}},ensure_ascii=False))
def native():
 assert E.exists();D=B/'word'/JOB;result=B/'results/word'/JOB/'report.xml'
 assert not D.exists() and not result.exists(),'Existing native job: inspect, never resubmit'
 current=B/'word/current.xml';old=current.read_bytes();previous=ET.fromstring(old).get('id')
 assert (B/'results/word'/previous/'report.xml').exists(),'Other native job pending'
 log=max(B.glob('transport*.log'),key=lambda p:p.stat().st_mtime);lines=log.read_text(errors='replace').splitlines()[-60:]
 polls=[x for x in lines if '192.168.1.140' in x and 'GET /word/current.xml HTTP/1.0" 204' in x];assert polls
 stamp=re.search(r'\[(.*?)\]',polls[-1]).group(1);at=datetime.datetime.strptime(stamp,'%d/%b/%Y %H:%M:%S').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7))).timestamp()
 assert 0<=time.time()-at<=75,'No fresh authenticated idle poll'
 j=ET.Element('job',id=JOB);inputs=[]
 for k,name in FILES.items():
  data=(C/name).read_bytes();expected=next(x['after_sha256'] for x in json.loads((E/'delta.json').read_text())['records'] if x['key']==k);assert sha(data)==expected
  ET.SubElement(j,'file',name=name,tag='f02'+k,sha256=expected);inputs.append((name,data))
 D.mkdir()
 for n,data in inputs:(D/n).write_bytes(data)
 xml=ET.tostring(j,encoding='utf-8',xml_declaration=True);(D/'job.xml').write_bytes(xml)
 stage={'job':JOB,'status':'STAGED_NOT_SUBMITTED','idle_poll':polls[-1],'previous_job':previous,'input_count':3,'utc':now()}
 (D/'stage-receipt.json').write_text(json.dumps(stage,ensure_ascii=False,indent=2)+'\n')
 assert current.read_bytes()==old;temp=current.with_name('current.xml.f02f03.tmp');assert not temp.exists();temp.write_bytes(xml);os.replace(temp,current)
 stage['status']='SUBMITTED_AWAITING_RESULT';(D/'stage-receipt.json').write_text(json.dumps(stage,ensure_ascii=False,indent=2)+'\n');print(json.dumps(stage,ensure_ascii=False),flush=True)
 start=time.monotonic()
 while not result.exists() and time.monotonic()-start<90:time.sleep(3)
 print('RESULT_AVAILABLE',result.exists(),flush=True)
 if not result.exists():raise TimeoutError('No native receipt within 90s; inspect late result, do not rerun')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','native']);args=ap.parse_args();globals()[args.mode]()
