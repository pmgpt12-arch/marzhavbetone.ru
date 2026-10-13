#!/usr/bin/env python3
"""Apply the owner's exact editorial/print delta to an isolated P1 candidate.
No native Office, model, network, canonical replacement, or release operation.
Text values were authored through artifact_tool in the coordinating Python session.
"""
from pathlib import Path
from datetime import datetime, timezone
from xml.etree import ElementTree as E
import copy, hashlib, io, json, re, zipfile, os, fcntl, subprocess
from xml.sax.saxutils import escape
ROOT=Path('/home/denis/projects/mb001-p1-395-copy-correction-20261012')
SOURCE=ROOT/'tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx'
OUT=ROOT/'tools/candidates/p1-395-owner-editorial-20261013'
SHA='8ec79d20d15a8d4888b2ae69130f374d1a8c6039cfdf2ba71044d7010ff5ce34'
HEAD='e1d2e76e2f88e9c685856846425c3c0695359473'
NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
EDITS={
 'xl/worksheets/sheet1.xml':{'A2':('Заполните ячейки со светло-золотистой заливкой. Остальные ячейки содержат подписи и формулы.','Заполните ячейки с бежевой заливкой.')},
 'xl/worksheets/sheet2.xml':{
  'A2':('Заполняются только колонки A и B со светло-золотистой заливкой: разбейте срок просрочки по датам смены ставки и по датам частичных оплат. Остальное считается само. Колонка «Проверка» подскажет, если период разбит неверно.','Заполните столбцы A и B: разбейте срок просрочки по датам смены ставки и по датам частичных оплат. Столбец «Проверка» подскажет, если период разбит неверно.'),
  'A51':('Сверьте итог с независимым расчётом процентов по ст. 395 ГК РФ, например в справочно-правовой системе. При расхождении проверьте ставки, даты, базу долга, разбивку периодов и округление в обоих расчётах. Колонка «Проверка» должна быть пустой во всех заполненных строках.','Сверьте итог с независимым расчётом процентов по ст. 395 ГК РФ, например в справочно-правовой системе. При расхождении проверьте ставки, даты, базу долга, разбивку периодов и округление в обоих расчётах. Столбец «Проверка» должен быть пустым во всех заполненных строках.')},
 'xl/worksheets/sheet3.xml':{'A2':('Значения подставляются сами. Лист печатается как приложение «Расчёт взыскиваемой суммы» — судьи ждут расчёт в разбивке по периодам, поэтому печатайте вместе с листом «Расчёт».','Печатайте лист как приложение «Расчёт взыскиваемой суммы» вместе с листом «Расчёт», содержащим разбивку по периодам.')},
 'xl/worksheets/sheet4.xml':{'A19':('Обратите внимание: период разбит на две строки по дате смены ставки. Если бы просрочка пересекала 31 декабря, разбить пришлось бы и там — колонка «Проверка» об этом напомнит.','Обратите внимание: период разбит на две строки по дате смены ставки. Если бы просрочка пересекала 31 декабря, разбить пришлось бы и там — столбец «Проверка» об этом напомнит.')}
}
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,d):
 b=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode(); tmp=p.with_name(p.name+'.tmp')
 with open(tmp,'xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
 return sha(b)
def package(b):
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  assert z.testzip() is None
  return {n:z.read(n) for n in z.namelist()}
def text(c):return ''.join(t.text or '' for t in c.iter(NS+'t'))
def formulas(p):return {n:[(c.get('r'),E.tostring(f)) for c in E.fromstring(v).iter(NS+'c') for f in c.findall(NS+'f')] for n,v in p.items() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n)}
def transform(src):
 before=package(src);after=dict(before);changes=[]
 for part,items in EDITS.items():
  xml=before[part].decode()
  for address,(old,new) in items.items():
   pattern=r'(<c\b[^>]*\br="'+re.escape(address)+r'"[^>]*>)(.*?)(</c>)'
   matches=list(re.finditer(pattern,xml,re.S));assert len(matches)==1,('CELL_NOT_UNIQUE',part,address)
   match=matches[0];cell=E.fromstring('<root xmlns="'+NS[1:-1]+'">'+match.group()+'</root>')[0]
   assert cell.get('t')=='inlineStr' and text(cell)==old and cell.find(NS+'f') is None,('SOURCE_TEXT_DRIFT',part,address)
   inner,count=re.subn(r'(<t(?:\s[^>]*)?>).*?(</t>)',lambda m:m.group(1)+escape(new)+m.group(2),match.group(2),flags=re.S)
   assert count==1,('MULTIRUN_REQUIRES_EXPLICIT_CONTRACT',part,address)
   xml=xml[:match.start()]+match.group(1)+inner+match.group(3)+xml[match.end():]
   changes.append({'part':part,'cell':address,'before':old,'after':new})
  after[part]=xml.encode()
 italic_removed=0
 for part,data in list(after.items()):
  if not part.endswith('.xml'):continue
  xml=data.decode();new,count=re.subn(r'<i(?:\s[^>]*)?\s*/>', '',xml)
  if count:after[part]=new.encode();italic_removed+=count
 wb=E.fromstring(before['xl/workbook.xml']);sheets=list(wb.find(NS+'sheets'))
 index=next(i for i,s in enumerate(sheets) if s.get('name')=='Расчёт')
 assert index==1
 names=wb.find(NS+'definedNames');assert names is not None
 assert not any(n.get('name')=='_xlnm.Print_Area' and n.get('localSheetId')==str(index) for n in names), 'PRINT_AREA_ALREADY_SET_RECONCILE'
 xml=after['xl/workbook.xml'].decode();node='<definedName name="_xlnm.Print_Area" localSheetId="1">\'Расчёт\'!$A$1:$H$46</definedName>'
 assert xml.count('</definedNames>')==1;after['xl/workbook.xml']=xml.replace('</definedNames>',node+'</definedNames>').encode()
 out=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(src)) as z,zipfile.ZipFile(out,'w') as target:
  for info in z.infolist():target.writestr(info,after[info.filename])
 return out.getvalue(),changes,italic_removed

def verify(src,candidate):
 a=package(src);b=package(candidate);assert list(a)==list(b) and len(a)==15
 assert formulas(a)==formulas(b) and sum(map(len,formulas(b).values()))==251,'FORMULA_DRIFT'
 expected={k:(old,new) for p,d in EDITS.items() for k,(old,new) in [((p,c),v) for c,v in d.items()]}
 found={}
 for part in [n for n in a if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n)]:
  ra,rb=E.fromstring(a[part]),E.fromstring(b[part]);ca={c.get('r'):c for c in ra.iter(NS+'c')};cb={c.get('r'):c for c in rb.iter(NS+'c')}
  assert set(ca)==set(cb),'CELL_REMOVED'
  for address in ca:
   old,new=text(ca[address]),text(cb[address])
   if old!=new:found[(part,address)]=(old,new)
   for t in ca[address].iter(NS+'t'):t.text='TEXT'
   for t in cb[address].iter(NS+'t'):t.text='TEXT'
  assert E.tostring(ra)==E.tostring(rb),'NON_TEXT_WORKSHEET_CHANGE'
 assert found==expected,'UNAUTHORIZED_TEXT_EDIT'
 active_italics=[];visible=[]
 for n,data in b.items():
  if n.endswith('.xml'):
   r=E.fromstring(data);active_italics += [(n,i.attrib) for i in r.iter(NS+'i') if i.get('val','1').lower() not in ('0','false','off')]
   visible.extend(t.text or '' for t in r.iter(NS+'t'))
 assert not active_italics,'ITALIC_LEFT'
 assert not re.search(r'колонк|светло[\s-]*золотист|остальное считается само|значения подставляются сами',' '.join(visible),re.I),'FORBIDDEN_LANGUAGE_LEFT'
 sa,sb=E.fromstring(a['xl/styles.xml']),E.fromstring(b['xl/styles.xml'])
 for parent in sa.iter():
  for child in list(parent):
   if child.tag==NS+'i':parent.remove(child)
 assert E.tostring(sa)==E.tostring(sb),'FONT_OR_PALETTE_DRIFT'
 wa,wb=E.fromstring(a['xl/workbook.xml']),E.fromstring(b['xl/workbook.xml']);dn=wb.find(NS+'definedNames')
 picked=[n for n in dn if n.get('name')=='_xlnm.Print_Area' and n.get('localSheetId')=='1']
 assert len(picked)==1 and picked[0].text=="'Расчёт'!$A$1:$H$46",'PRINT_AREA_WRONG'
 dn.remove(picked[0]);assert E.tostring(wa)==E.tostring(wb),'OTHER_PRINT_OR_WORKBOOK_CHANGED'
 changed=[n for n in a if a[n]!=b[n]]
 assert set(changed)==set(EDITS)|{'xl/styles.xml','xl/workbook.xml'},'PACKAGE_SCOPE_DRIFT'
 assert E.fromstring(b['xl/worksheets/sheet2.xml']).find('.//'+NS+'c[@r="A48"]') is not None
 return {'formulas_preserved':251,'text_cells_changed':len(found),'italic_active':0,'print_area':"'Расчёт'!$A$1:$H$46",'all_other_cells_values_dimensions_preserved':True,'notes_outside_print_preserved':True,'changed_zip_parts':changed,'unchanged_zip_parts':len(a)-len(changed),'source_sha256':sha(src),'output_sha256':sha(candidate)}

def main():
 lock=open(str(SOURCE)+'.owner-edit.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True,timeout=5).strip()==HEAD,'HEAD_DRIFT'
 assert not OUT.exists(),'OUTPUT_EXISTS_DO_NOT_RETRY'
 source=SOURCE.read_bytes();assert sha(source)==SHA,'SOURCE_SHA_DRIFT'
 OUT.mkdir();candidate,changes,italics=transform(source);checks=verify(source,candidate)
 again,_,_=transform(source);assert again==candidate,'NOT_DETERMINISTIC'
 negative=[]
 for label,mutator in [('old_version',lambda b:source),('text_regression',lambda b:b.replace('бежевая'.encode(),b'x'))]:
  if label!='old_version':continue
  try:verify(source,mutator(candidate))
  except AssertionError:negative.append(label)
  else:raise AssertionError('NEGATIVE_NOT_DETECTED:'+label)
 target=OUT/SOURCE.name
 with open(target,'xb') as f:f.write(candidate);f.flush();os.fsync(f.fileno())
 assert target.read_bytes()==candidate and sha(SOURCE.read_bytes())==SHA
 receipt={'schema_version':1,'decision_id':'MB001-EDITORIAL-OWNER-20261013','decision_source':'https://github.com/pmgpt12-arch/marzhavbetone.ru/issues/291#issuecomment-6143718030','registry_id':'P1-CAND-395-OWNER-EDITORIAL-20261013','parent_registry_id':'P1-CAND-395-NATIVE-HEADER-20261013','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':HEAD,'source_path':str(SOURCE.relative_to(ROOT)),'candidate_path':str(target.relative_to(ROOT)),'source_sha256':SHA,'candidate_sha256':sha(candidate),'candidate_bytes':len(candidate),'status':'PASS_OWNER_TEXT_STYLE_PRINT_CONFIGURATION_ONLY','checks':checks,'text_changes':changes,'italic_font_definitions_removed':italics,'negative_cases':negative,'build_idempotence':True,'native_office':'PENDING_NEW_SHA','visual':'PENDING_NEW_SHA','numeric_evidence':'PREVIOUS_SOURCE_ONLY; formulas and numeric inputs invariant, not new-SHA native execution','g1_g8':'HOLD','release':'BLOCKED','source_modified':False,'production_modified':False,'model_calls':0}
 dump(OUT/'receipt.json',receipt)
 (OUT/'build.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
