"""Keep protection intact: cross-sheet cases use native fill/save/reopen, not worker edits."""
from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as E
from docx import Document
O=Path(__file__).resolve().parent;D=json.loads((O/'CASES.json').read_text());M=D['main_sheet'];FN='02-kalkulyator-sroka-oplaty.xlsx'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def flat(d):return {(s,c):v for s,cs in d.items()for c,v in cs.items()}
def put(p,t,s,c,v):
 k,x=('boolean',str(v).lower())if isinstance(v,bool)else('number',str(v))if isinstance(v,(int,float))else('text',str(v));E.SubElement(p,t,sheet=s,cell=c,kind=k,value=x)
def save(root,ch,files):
 p=O/'native-phase2'/ch/root.get('id');p.mkdir(parents=True,exist_ok=True);E.indent(root);E.ElementTree(root).write(p/'job.xml',encoding='utf-8',xml_declaration=True)
 for name,source in files.items():shutil.copyfile(source,p/name)
 return dict(channel=ch,id=root.get('id'))
main=[c for c in D['cases'][8:]if set(c['inputs'])<={M}]
root=E.Element('job',id='nsp-qa02-excel-main-v2-20261023',qa_only='true');f=E.SubElement(root,'file',name=FN,tag='q2m',sheet=M,sha256=sha(O/'candidate'/FN),export_source_first='true',print_preflight='true');prev={}
for c in main:
 cs=E.SubElement(f,'case',name=c['name']);now=flat(c['inputs'])
 for s,a in sorted(prev.keys()-now.keys()):E.SubElement(cs,'set',sheet=s,cell=a,kind='blank',value='')
 for(s,a),v in now.items():put(cs,'set',s,a,v)
 for(s,a),v in flat(c['expected']).items():put(cs,'expect',s,a,v)
 prev=now
mainjob=save(root,'native',{FN:O/'candidate'/FN})
# Filling the template in Excel uses the worker's existing cross-sheet print input path.
# Every such result is then reopened without writes and checked numerically.
cross=[c for c in D['cases']if set(c['inputs'])!={M}and c['inputs']]
assert len(main)==29 and len(cross)==19
groups=[]
for g in range(5):
 cases=cross[g*4:g*4+4];ident=f'nsp-qa02-excel-fill{g+1}-v2-20261023';root=E.Element('job',id=ident,qa_only='true');files={};entries=[]
 for i,c in enumerate(cases,1):
  name=f'case-{i}.xlsx';tag=f'q2c{i}';f=E.SubElement(root,'file',name=name,tag=tag,sheet=M,sha256=sha(O/'candidate'/FN),export_source_first='true',print_preflight='true');pr=E.SubElement(f,'print')
  for(s,a),v in flat(c['inputs']).items():put(pr,'set',s,a,v)
  files[name]=O/'candidate'/FN;entries.append(dict(tag=tag,case=c))
 groups.append(dict(fill=save(root,'native',files),verify_id=f'nsp-qa02-excel-check{g+1}-v2-20261023',entries=entries))
wordroot=E.Element('job',id='nsp-qa02-word-v2-20261023',qa_only='true');files={}
for i,p in enumerate(sorted((O/'candidate').glob('*.docx')),1):E.SubElement(wordroot,'file',name=p.name,tag='q2d'+str(i),sha256=sha(p));files[p.name]=p
word=save(wordroot,'word',files)
# Synthetic filled letter: no customer, personal or banking data.
p=O/'proof/fixtures/04-filled-example.docx';p.parent.mkdir(exist_ok=True);d=Document(O/'candidate/04-shablon-pisma.docx')
texts={0:'УЧЕБНЫЙ ПРИМЕР — синтетические данные',1:'Исх. № 1 от 21.10.2026',2:'Кому: Заказчику (учебный пример), по договорному адресу',3:'От: Подрядчика (учебный пример), ответ по договорному каналу',5:'По договору № 1 от 01.10.2026 выполнен этап работ № 1. Сдача подтверждается актом № 1 от 11.10.2026. Комплект получен заказчиком 11.10.2026; подтверждение получения приложено.',6:'Основание срока оплаты: пункт 5 договора — пять календарных дней после получения комплекта. Событие начала срока — получение 11.10.2026; крайний день оплаты — 16.10.2026.',7:'По состоянию на 21.10.2026 сумма обязательства до оплат составляет 100 000 руб., погашено в счёт основного долга 40 000 руб. Остаток основного долга — 60 000 руб. Расшифровка оплат прилагается.',8:'Договорная пеня по пункту 7 договора — 0,1% в день на неоплаченный основной долг. За период 17–21.10.2026 включительно пеня составляет 420 руб. Основание, база и периоды приведены в расчёте.',9:'Просим перечислить основной долг 60 000 руб. и договорную пеню 420 руб. Общая сумма обращения — 60 420 руб. Просим исполнить требование до 28.10.2026. Этот срок не изменяет ранее наступивший срок исполнения обязательства.',10:'Реквизиты для перечисления и адрес для ответа — по договору. При разногласиях просим указать конкретное основание и приложить подтверждения.',11:'Приложения: 1. Акт № 1 и подтверждение получения — 2 листа. 2. Расшифровка обязательства и оплаты от 19.10.2026 — 1 лист. 3. Расчёт договорной пени — 1 лист.',12:'Уполномоченный представитель Подрядчика  /  подпись в оригинале'}
for n,t in texts.items():d.paragraphs[n].text=t
d.save(p);root=E.Element('job',id='nsp-qa02-word-filled-v2-20261023',qa_only='true');E.SubElement(root,'file',name=p.name,tag='q2df',sha256=sha(p));filledword=save(root,'word',{p.name:p})
plan=dict(word=word,main=mainjob,cross=groups,filled_word=filledword,reason='Existing native agent checks main-sheet protection before routing case set to target sheet. Source stays protected; print inputs perform real native fill/save; fresh reopen cases verify every cross-sheet result without writes.',main_case_count=29,cross_case_count=19,reused_b1_cases=8)
(O/'native-phase2/PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
# Retain immutable phase1 script; reuse only its guarded queue functions with new roots.
s=(O/'run_native_remote.py').read_text();s=s[:s.index('lock=(B/')];s=s.replace("O/'native-jobs/PLAN.json'","O/'native-phase2/PLAN.json'").replace("O/'native-jobs'/ch/ident","O/'native-phase2'/ch/ident")
s+='''
lock=(B/'diagnostics/office-access-20261021-222308/check.lock').open('a+')
try:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for ch in ['word','native']:
  if not complete(ch):raise RuntimeError('Foreign incomplete queue: '+ch)
 run(**dict(ch=PLAN['word']['channel'],ident=PLAN['word']['id']))
 run('native',PLAN['main']['id'])
 for g in PLAN['cross']:
  out=run('native',g['fill']['id']);ident=g['verify_id'];p=O/'native-phase2/native'/ident;p.mkdir(parents=True)
  root=E.Element('job',id=ident,qa_only='true')
  for i,e in enumerate(g['entries'],1):
   original=out/(e['tag']+'-filled.xlsx');name='native-saved-'+str(i)+'.xlsx';shutil.copyfile(original,p/name)
   f=E.SubElement(root,'file',name=name,tag='q2v'+str(i),sheet='Калькулятор срока оплаты',sha256=sha(original),export_source_first='true',print_preflight='true');c=E.SubElement(f,'case',name=e['case']['name'])
   for sheet,cs in e['case']['expected'].items():
    for cell,v in cs.items():E.SubElement(c,'expect',sheet=sheet,cell=cell,kind='number'if isinstance(v,(int,float))else'text',value=str(v))
  E.indent(root);E.ElementTree(root).write(p/'job.xml',encoding='utf-8',xml_declaration=True);run('native',ident)
 run('word',PLAN['filled_word']['id'])
 emit(dict(stage='PHASE2_NATIVE_PASS',cases=56,cross_sheet_native_save_reopen_cases=19))
except Exception as exc:
 emit(dict(stage='STOPPED',error=str(exc)));raise
finally:lock.close()
'''
(O/'run_native_phase2_remote.py').write_text(s)
print('Prepared phase2: 29 main + 19 fill/save/reopen + 8 reused; Word 3 + filled example')
