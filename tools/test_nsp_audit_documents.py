#!/usr/bin/env python3
"""Offline regression for the exact P5/P8/P9/P11 authored-document corrections.

Reads delivered DOCX XML and formulas, not a second calculation implementation.
Does not certify native Office layout, XLSX results, legal completeness or release.
"""
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta
import argparse, ast, json, re, zipfile, xml.etree.ElementTree as E
R=Path(__file__).resolve().parents[1]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
REL='{http://schemas.openxmlformats.org/package/2006/relationships}'
RID='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
P5='products-storage/07-uderzhaniya-shtrafy-zachety/'
P8='products-storage/10-avans-usloviya-i-pribyl/'
P9='products-storage/11-bankrotstvo-genpodryadchika/'
P11='products-storage/13-raschet-metrami/'
FILES=[P9+x for x in ['02-algoritm-genpodryadchik-bankrotitsya.docx','05-perechen-paketa-dlya-zayavleniya-trebovaniya.docx','08-zayavlenie-o-vklyuchenii-v-reestr-zagotovka.docx','09-chto-delat-esli-srok-propushchen.docx']]+[P8+x for x in ['07-trebovanie-o-vyplate-avansa.docx','08-algoritm-s-vas-trebuyut-vernut-avans.docx','10-otvet-na-trebovanie-o-vozvrate-avansa.docx']]+[P11+x for x in ['52-chek-list-raschet-metrami.docx','56-pervyy-den-do-podpisi.docx']]+[P5+'03-vozrazhenie-na-zachet.docx']
def read(path):
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None, f'CRC: {path}'
  for n in z.namelist():
   if n.endswith(('.xml','.rels')):
    raw=z.read(n);E.fromstring(raw)
    assert b'marzhavbetone' not in raw, f'STALE_BRAND {path}:{n}'
  root=E.fromstring(z.read('word/document.xml'))
  rels={x.attrib['Id']:x.attrib for x in E.fromstring(z.read('word/_rels/document.xml.rels'))}
  for h in root.iter(W+'hyperlink'):
   if RID in h.attrib:
    target=rels[h.attrib[RID]]['Target'];assert target.startswith(('https://','mailto:')),target
  text=' '.join(x.text or '' for x in root.iter(W+'t'))
  tables=[]
  for t in root.findall('.//'+W+'body/'+W+'tbl'):
   tables.append([[''.join(x.text or '' for x in c.iter(W+'t')) for c in row.findall(W+'tc')]for row in t.findall(W+'tr')])
  return text,tables,[x['Target']for x in rels.values()if x.get('Type','').endswith('/hyperlink')]
def require(text,parts):
 for p in parts:assert p in text, f'MISSING {p}'
def calc(expr,env):
 root=ast.parse(expr.replace('×','*').replace('−','-'),mode='eval')
 def visit(n):
  if isinstance(n,ast.Expression):return visit(n.body)
  if isinstance(n,ast.Name):return Decimal(str(env[n.id]))
  if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):return Decimal(str(n.value))
  if isinstance(n,ast.BinOp):
   a,b=visit(n.left),visit(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  raise AssertionError('Unsupported formula: '+expr)
 return visit(root)
def evaluate(table,inputs):
 f={r[0].split('.')[0]:r[1]for r in table[1:]}
 env=dict(inputs)
 for symbol in ['В','З','К','М']:env[symbol]=calc(f[symbol],env)
 return env['М']
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=R);p.add_argument('--json',type=Path);args=p.parse_args()
 docs={};checks=[]
 def check(name,fn):
  fn();checks.append(name)
 for rel in FILES:
  docs[rel]=read(args.root/rel);checks.append('DOCX_XML_CRC_LINKS_BRAND:'+rel)
 text=docs[P11+'52-chek-list-raschet-metrami.docx'][0];tables=docs[P11+'52-chek-list-raschet-metrami.docx'][1]
 table=next(t for t in tables if any('М. Разница' in r[0]for r in t))
 base={'А':10000000,'Б':5,'Г':600000,'Д':200000,'Е':400000,'Ж':0,'И':0,'Л':9000000}
 cases=[('P11_baseline',base,-700000),('P11_DDU_extra_3m',{**base,'Ж':3000000},-3700000),('P11_audit_sign_change',{**base,'Ж':3000000,'Л':6000000},-700000),('P11_mixed_cash',{**base,'А':7700000,'Б':0,'Ж':0,'И':3000000},500000)]
 for name,inputs,expected in cases:
  result=evaluate(table,inputs);assert result==Decimal(expected),(name,result,expected);checks.append(name)
 # Both previous omission classes must be detected by the same scenario checks.
 import copy
 m=copy.deepcopy(table)
 next(r for r in m if r[0].startswith('З.'))[1]='В − Г − Д − Е'
 assert evaluate(m,cases[1][1])!=Decimal(cases[1][2]);checks.append('MUTANT_missing_DDU_payment_detected')
 m=copy.deepcopy(table);next(r for r in m if r[0].startswith('К.'))[1]='З'
 assert evaluate(m,cases[3][1])!=Decimal(cases[3][2]);checks.append('MUTANT_missing_cash_part_detected')
 require(text,['неизвестное ≠ 0','Погашаемый долг','Себестоимость работ и прибыль объекта анализируются отдельно','после регистрации ДДУ'])
 checks.append('P11_unknown_inputs_perimeter_and_sequence')
 require(docs[P11+'56-pervyy-den-do-podpisi.docx'][0],['существующего ДДУ','По новому ДДУ','после регистрации']);checks.append('P11_first_day_separates_new_DDU')
 a=docs[P9+'02-algoritm-genpodryadchik-bankrotitsya.docx'][0]
 require(a,['30 календарных дней','два месяца','В любой момент','В суд электронно','бумажное обращение','не является подачей','27 500','льготу','не увеличивает долг','мораторные проценты'])
 assert Decimal('0.5')*(10000+Decimal('.05')*(1000000-100000))==27500
 checks.append('P9_fee_27500_and_adjudicated_exemption_branch')
 checks.append('P9_procedure_deadlines_and_electronic_filing')
 for name in ['05-perechen-paketa-dlya-zayavleniya-trebovaniya.docx','08-zayavlenie-o-vklyuchenii-v-reestr-zagotovka.docx']:
  s=docs[P9+name][0].lower();require(s,['пошлин','льгот','ходатайств','подтвержд','текущие платежи']);checks.append('P9_filing_packet_consistency:'+name)
 s=docs[P9+'09-chto-delat-esli-srok-propushchen.docx'][0];require(s,['п. 4 ст. 142','восстановлен','20.08.2026','20.10.2026','19.10.2026'])
 assert date(2026,8,20)+timedelta(days=60)==date(2026,10,19);checks.append('P9_two_calendar_months_not_60_days')
 for name in ['08-algoritm-s-vas-trebuyut-vernut-avans.docx','10-otvet-na-trebovanie-o-vozvrate-avansa.docx']:
  s=docs[P8+name][0].lower();require(s,['действует','прекращ','оспарива']);checks.append('P8_contract_state_branches:'+name)
 s=docs[P8+'07-trebovanie-o-vyplate-avansa.docx'][0];require(s,['Договорный срок выплаты аванса истёк','добровольно до','не изменяет наступивший договорный срок','п. 2 ст. 711 ГК РФ']);checks.append('P8_old_deadline_not_replaced_by_voluntary_date')
 s=docs[P5+'03-vozrazhenie-na-zachet.docx'][0];require(s,['Отсутствие нашего согласия само по себе не доказывает','Само наличие спора','не является самостоятельным запретом','конкретным фактическим'])
 assert '1. Зачет произведен без письменного согласования с Подрядчиком.' not in s;checks.append('P5_consent_and_dispute_not_standalone_grounds')
 for name in ['08-zayavlenie-o-vklyuchenii-v-reestr-zagotovka.docx','07-trebovanie-o-vyplate-avansa.docx','10-otvet-na-trebovanie-o-vozvrate-avansa.docx','03-vozrazhenie-na-zachet.docx']:
  row=next(v for k,v in docs.items() if k.endswith('/'+name));assert 'Помощь по комплекту' not in row[0];checks.append('NO_MARKETING_IN_OUTGOING:'+name)
 for rel in ['products-storage/02-dopraboty-bez-poter/00-START-HERE.txt','products-storage/05-ks-bez-vozvrata/00-START-HERE.txt']:
  guide=(args.root/rel).read_text();assert 'cons_doc_LAW_448832' in guide and '406969808' not in guide;checks.append('GUIDE_344_SOURCE_IDENTITY:'+rel)
 result={'status':'PASS','checks':checks,'check_count':len(checks),'docx_count':len(FILES),'p11_cases':[{'name':n,'expected_rub':v,'actual_rub':str(evaluate(table,i))}for n,i,v in cases],'scope':'DOCX semantic/structure and Word-table arithmetic; not native Office or ZIP release'}
 if args.json:args.json.parent.mkdir(parents=True,exist_ok=True);args.json.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
