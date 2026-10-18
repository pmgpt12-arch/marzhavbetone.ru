#!/usr/bin/env python3
"""P1 buyer candidate from existing forms and calculator with scoped editorial fixes."""
from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import load_workbook
from collections import Counter
from copy import deepcopy
import shutil,subprocess,hashlib,json

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'products-storage/01-zakrytie-rabot'
OUT=ROOT/'tools/candidates/remaining-batch-20261018/P1'
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir(parents=True,exist_ok=True)
for f in SRC.iterdir():
 if f.suffix.lower() in ('.docx','.xlsx','.pdf','.txt') and not f.name.startswith('00-PISMO'):
  shutil.copy2(f,OUT/f.name)

# Replace the old commercial/navigation text with a one-object route.
files=sorted(x.name for x in OUT.iterdir() if x.is_file())
intro="""С ЧЕГО НАЧАТЬ
Система получения оплаты за выполненные работы

Результат: подтверждён объём, оформлена сдача, рассчитан остаток к оплате и выбран документ для взыскания задолженности.

Если работы ещё сдаются, откройте 00-INSTRUKCIYA.pdf. Сверьте КС-2, КС-3, акты и объёмы в файлах 01–08; подготовьте подтверждение передачи 09 и сохраните документы по карте 10.

Если работы приняты и срок оплаты истёк, откройте 15-algoritm-pri-zaderzhke-oplaty.docx. Сверьте договор, акты и платежи; определите остаток к оплате, заполните 14-raschet-procentov-395-gk.xlsx. Направьте 13-uvedomlenie-o-prosrochke-oplaty.docx либо 12-pretenziya-na-neoplatu-po-ks-2.docx в применимом порядке. После проверки досудебного срока и приложений используйте 16-iskovoe-zayavlenie-o-vzyskanii.docx.

Поля из документов 11–16 расшифрованы в 11-slovar-poley.docx. Перед направлением удалите незаполненные поля и неприменимые варианты, сверьте сумму и даты, подпишите документ уполномоченным лицом. Сохраните экземпляр, список приложений, подтверждения отправки и получения.

СОСТАВ АРХИВА
"""
(OUT/'00-START-HERE.txt').write_text(intro+'\n'.join(files)+'\n',encoding='utf-8')
# The instruction is the only Word file carrying the former brand in header.
d=Document(OUT/'00-INSTRUKCIYA.docx')
for p in d.paragraphs:
 if 'Как внедрить пакет «Закрытие работ»' in p.text:
  p.text='Система получения оплаты за выполненные работы'
for sec in d.sections:
 for p in list(sec.header.paragraphs)+list(sec.footer.paragraphs):
  if 'МАРЖА В БЕТОНЕ' in p.text:p.text=p.text.replace('МАРЖА В БЕТОНЕ','НА СТОРОНЕ ПОДРЯДЧИКА')
d.save(OUT/'00-INSTRUKCIYA.docx')
res=subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/lo_p1_guide_batch','--headless','--convert-to','pdf','--outdir',str(OUT),str(OUT/'00-INSTRUKCIYA.docx')],capture_output=True,text=True)
if res.returncode:raise RuntimeError(res.stderr)

# Remove legacy forced page breaks that leave isolated table rows.
d=Document(OUT/'11-slovar-poley.docx')
for p in list(d.paragraphs):
 if p._p.xpath('.//w:br[@w:type="page"]'):
  p._element.getparent().remove(p._element)
d.save(OUT/'11-slovar-poley.docx')

# Put the sendable form at the very beginning, retain the source's separate instructions.
spans={'12-pretenziya-na-neoplatu-po-ks-2.docx':(24,56,2,20,57),
       '13-uvedomlenie-o-prosrochke-oplaty.docx':(20,38,2,16,38),
       '16-iskovoe-zayavlenie-o-vzyskanii.docx':(21,75,2,17,75)}
for name,(start,end,prestart,preend,poststart) in spans.items():
 d=Document(OUT/name)
 ps=list(d.paragraphs);body=d._element.body
 for p in ps:body.remove(p._p)
 for p in ps[start:end]:body.insert_element_before(p._p,'w:sectPr')
 guide=d.add_paragraph('Порядок заполнения и контроля')
 for run in guide.runs:run.bold=True;run.font.size=Pt(12)
 for p in ps[prestart:preend]+ps[poststart:]:
  body.insert_element_before(p._p,'w:sectPr')
 # remove duplicate guide paragraph that add_paragraph appended behind restored instructions
 body.remove(guide._p)
 body.insert(len(ps[start:end]),guide._p)
 d.save(OUT/name)

# Targeted formula-preserving editorial replacement on the printable calculation summary.
source=load_workbook(SRC/'14-raschet-procentov-395-gk.xlsx')
w=load_workbook(OUT/'14-raschet-procentov-395-gk.xlsx')
s=w['Итог для документа']
for cell,value in {
'A15':'Контроль перед направлением',
'A16':'Сверьте договор: проценты по ст. 395 ГК РФ или договорная неустойка. Для выбранного требования оформите отдельный расчёт.',
'A17':'Проверьте оплаты, изменение ставки, границы периодов и основания изменения суммы долга.',
'A18':'Сопоставьте итог с претензией или иском, датой расчёта и первичными документами.',
'A19':'Подпишите расчёт; сохраните источники ставок и подтверждения платежей.'
}.items():s[cell]=value
w.save(OUT/'14-raschet-procentov-395-gk.xlsx')
def formulas(book):
 return {(sh.title,c.coordinate):c.value for sh in book for row in sh for c in row if c.data_type=='f'}
assert formulas(source)==formulas(load_workbook(OUT/'14-raschet-procentov-395-gk.xlsx'))
assert len(formulas(source))==251
assert source['Итог для документа'].print_area==load_workbook(OUT/'14-raschet-procentov-395-gk.xlsx')['Итог для документа'].print_area

# Two short check cards: same actions and output format, current brand.
def check_pdf(name,title,items):
 d=Document()
 sec=d.sections[0];sec.page_height=Cm(29.7);sec.page_width=Cm(21)
 sec.top_margin=Cm(2);sec.bottom_margin=Cm(1.8);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
 normal=d.styles['Normal'];normal.font.name='Arial';normal.font.size=Pt(10);normal.font.color.rgb=RGBColor(43,50,57)
 normal.paragraph_format.space_after=Pt(9)
 p=d.add_paragraph('НА СТОРОНЕ ПОДРЯДЧИКА  /  P1')
 p.runs[0].font.size=Pt(8);p.runs[0].font.color.rgb=RGBColor(174,128,49)
 h=d.add_paragraph(title,style='Title')
 h.runs[0].font.name='Arial';h.runs[0].font.size=Pt(18);h.runs[0].font.color.rgb=RGBColor(43,50,57)
 for x in h._p.xpath('.//w:pBdr'):x.getparent().remove(x)
 for i,entry in enumerate(items,1):
  p=d.add_paragraph()
  r=p.add_run(f'{i:02d}  ');r.bold=True;r.font.color.rgb=RGBColor(174,128,49)
  p.add_run(entry)
 tmp=OUT/(name+'.docx');d.save(tmp)
 res=subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/lo_p1_cards_batch','--headless','--convert-to','pdf','--outdir',str(OUT),str(tmp)],capture_output=True,text=True)
 if res.returncode:raise RuntimeError(res.stderr)
 tmp.unlink()
check_pdf('09-checklist-peredachi','Контроль перед передачей работ',[
'Журнал объёмов заполнен по предъявляемому периоду.',
'КС-2 сверена с журналом и согласованной сметой.',
'КС-3 соответствует принятой стоимости по КС-2.',
'Исполнительная документация собрана по согласованному перечню.',
'Дополнительные работы имеют письменное основание и отдельный расчёт.',
'Комплект прошёл внутреннюю проверку реквизитов и сумм.',
'Подготовлен реестр передачи с составом и числом листов.',
'Выбран договорный канал направления; сохраняются доказательства доставки.',
'Установлены контрольные даты проверки, замечаний и оплаты.'
])
check_pdf('10-sroki-hraneniya','Хранение доказательств по объекту',[
'Утвердите номенклатуру дел и ответственного за хранение.',
'Храните подписанные оригиналы отдельно от рабочих редакций.',
'Сохраняйте подтверждения ЭДО, электронной почты и вручения.',
'Привязывайте фотографии и схемы к конкретному объёму и дате.',
'Сохраняйте предыдущие версии документов и историю согласования.',
'Определите срок хранения каждого вида документа по применимым требованиям и учётной политике.'
])
print('P1_PREPARED',len([f for f in OUT.iterdir() if f.is_file()]),len(formulas(source)))
