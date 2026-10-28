from pathlib import Path
import json,hashlib,zipfile,re,copy
from lxml import etree as E
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';S=Q/'package-sources/products-storage/13-raschet-metrami';O=P/'p11-final-letter-tests';O.mkdir(exist_ok=True)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+ns['w']+'}';sha=lambda b:hashlib.sha256(b).hexdigest()
def unpack(p):
 with zipfile.ZipFile(p)as z:return z.infolist(),{i.filename:z.read(i)for i in z.infolist()}
def save(p,infos,parts,root):
 parts['word/document.xml']=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
 with zipfile.ZipFile(p,'w')as z:
  for i in infos:z.writestr(i,parts[i.filename])
text=lambda n:''.join(n.xpath('.//w:t/text()',namespaces=ns))
src=S/'54-zapros-sostoyanie-escrow.docx';infos,parts=unpack(src);root=E.fromstring(parts['word/document.xml']);body=root.find(W+'body');nodes=list(body);start=next(i for i,n in enumerate(nodes)if text(n).startswith('Кому:'));guide=next(i for i,n in enumerate(nodes)if text(n)=='Как пользоваться этим документом');sect=nodes[-1];assert sect.tag==W+'sectPr'
letter_text=''.join(text(n)for n in nodes[start:guide])
for n in nodes[:-1]:
 for b in n.xpath('.//w:br[@w:type="page"]|.//w:pageBreakBefore',namespaces=ns):b.getparent().remove(b)
for n in list(body):body.remove(n)
for n in nodes[start:guide]+nodes[:start]+nodes[guide:-1]+[sect]:body.append(n)
preface=nodes[0];pp=preface.find(W+'pPr')
if pp is None:pp=E.Element(W+'pPr');preface.insert(0,pp)
E.SubElement(pp,W+'pageBreakBefore')
changes={'Документальное подтверждение наполнения счёта эскроу по ДДУ, права по которому предлагаются в счёт выполненных работ. Отправляется — текст письма ниже; страница «Как пользоваться этим документом» в отправку не входит.':'Документальное подтверждение наполнения счёта эскроу по ДДУ, права по которому предлагаются в счёт выполненных работ. Заказчику направляется заполненная форма от «Кому:» до подписи перед разрывом страницы. Следующие пояснения покупателю не направляются.','Примечание покупателю. Эта страница в отправляемое письмо не входит: отправляется только текст до разрыва страницы.':'Примечание покупателю. Направляется заполненная форма перед разрывом страницы; все последующие пояснения покупателю в письмо не включаются.'}
for a,b in changes.items():
 ps=[p for p in root.findall('.//w:p',ns)if text(p)==a];assert len(ps)==1,(a,len(ps));ts=ps[0].findall('.//w:t',ns);ts[0].text=b
 for t in ts[1:]:t.text=''
assert ''.join(text(n)for n in list(body)[:guide-start])==letter_text
dst=O/src.name;save(dst,infos,parts,root)
with zipfile.ZipFile(src)as a,zipfile.ZipFile(dst)as b:assert all(a.read(n)==b.read(n)for n in a.namelist()if n!='word/document.xml')
rows=[{'path':dst.name,'new_sha256':sha(dst.read_bytes()),'base_sha256':sha(src.read_bytes()),'role':'BUYER_CANDIDATE','letter_text_exact':True,'guide_changes':changes}]
# Synthetic filled copies: demonstrate the sendable body and recipient fields, never send.
values={'НАИМЕНОВАНИЕ_АДРЕСАТА':'ООО «Условный застройщик»','НАИМЕНОВАНИЕ_ЦЕДЕНТА_ИЛИ_ЗАСТРОЙЩИКА':'ООО «Условный участник ДДУ»','АДРЕС_АДРЕСАТА':'г. Красноярск, ул. Примерная, д. 1','НАИМЕНОВАНИЕ_ПОДРЯДЧИКА':'ООО «Условный подрядчик»','АДРЕС_ПОДРЯДЧИКА':'г. Красноярск, ул. Примерная, д. 2','ИСХОДЯЩИЙ_НОМЕР':'НСП-ТЕСТ-23','ДАТА_ДОКУМЕНТА':'23.10.2026','НАИМЕНОВАНИЕ_ОБЪЕКТА_ПО_ПРОЕКТНОЙ_ДЕКЛАРАЦИИ':'Условный жилой дом, корпус 1, г. Красноярск','СРОК_ОТВЕТА_НА_ЗАПРОС':'30.10.2026','АДРЕС_ДЛЯ_ОТВЕТА':'г. Красноярск, ул. Примерная, д. 2','ЭЛЕКТРОННАЯ_ПОЧТА':'contractor@example.com','ДОЛЖНОСТЬ_ПОДПИСАНТА':'Директор','ФИО_ПОДПИСАНТА':'Иванов И. И. (учебный пример)','НОМЕР_ДДУ':'УЧ-42/26','ДАТА_ДДУ':'01.09.2026','ОПИСАНИЕ_ОБЪЕКТА_ДОЛЕВОГО_СТРОИТЕЛЬСТВА':'помещение № 101, 60 м², корпус 1 условного жилого дома','НАИМЕНОВАНИЕ_БАНКА_ЕСЛИ_ИЗВЕСТЕН':'Условный банк А'}
for num,s in [(53,P/'p11-layout-v3/53-zapros-status-obekta.docx'),(54,dst)]:
 ins,pts=unpack(s);r=E.fromstring(pts['word/document.xml']);count=0
 for p in r.findall('.//w:p',ns):
  old=text(p)
  def replace(m):
   global count
   key=m.group(1);count+=1
   if key.startswith('ОСНОВАНИЕ_ЗАПРОСА:'):return 'предложением о заключении договора подряда'
   if key.startswith('ЧТО_ЗАВИСИТ_ОТ_ВВОДА:'):return 'условия предлагаемого договора'
   assert key in values,key
   return values[key]
  new=re.sub(r'\{\{([^{}]+)\}\}',replace,old)
  if new!=old:
   ts=p.findall('.//w:t',ns);ts[0].text=new
   for t in ts[1:]:t.text=''
 assert not re.search(r'\{\{[^{}]+\}\}',''.join(r.xpath('.//w:t/text()',namespaces=ns)))
 p=O/('example-'+str(num)+'-filled.docx');save(p,ins,pts,r);rows.append({'path':p.name,'new_sha256':sha(p.read_bytes()),'role':'SYNTHETIC_TEST_ONLY_NOT_BUYER_FILE','substitutions':count})
(P/'P11_FINAL_LETTER_TESTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
s=(Q/'scripts/native_p11_remaining.py').read_text()
for a,b in {'nsp-p11-remaining-word-20261023':'nsp-p11-final-letter-tests-20261023','P11_REMAINING_DOCX.json':'P11_FINAL_LETTER_TESTS.json',"'p11-remaining-sources'":"'p11-final-letter-tests'","tag='pm'":"tag='pt'",'visual-p11-remaining':'visual-p11-final-letter-tests','P11_REMAINING_NATIVE.json':'P11_FINAL_LETTER_TESTS_NATIVE.json'}.items():assert s.count(a)==1;s=s.replace(a,b)
compile(s,'native_p11_final_letters.py','exec');(Q/'scripts/native_p11_final_letters.py').write_text(s)
print('PREPARED',json.dumps(rows,ensure_ascii=False),flush=True)
