#!/usr/bin/env python3
"""Addressed editorial, format and signature corrections over immutable R1 ZIPs."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from openpyxl import load_workbook
import shutil,subprocess,urllib.request,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'tools/candidates/remaining-batch-20261018'
OUT=BASE/'R2-work'
SKUS=('P1','P2','P4','P7','P8','P9','P10')
G=RGBColor(174,128,49);D=RGBColor(43,50,57)
P10_URL='https://raw.githubusercontent.com/pmgpt12-arch/marzhavbetone.ru/068ec3fd3538153f62005faeb0f00f3a24720cb8/tools/candidates/p10-buyer-review-20261018/P10-otvet-na-pretenziyu-8-files-business-R2.zip'
P10_SHA='42f51bb0c46fed63253a56dbddeceb3aa971c55a8b0389a5e0a59260acf92526'
def source(sku):
 if sku=='P10':
  data=urllib.request.urlopen(P10_URL,timeout=30).read()
  assert hashlib.sha256(data).hexdigest()==P10_SHA
  return BytesIO(data)
 return BASE/f'{sku}-buyer-review-20261018-R1.zip'
def all_paras(d):
 for p in d.paragraphs:yield p
 for t in d.tables:
  for row in t.rows:
   for c in row.cells:
    for p in c.paragraphs:yield p
 for s in d.sections:
  for zone in (s.header,s.footer):
   for p in zone.paragraphs:yield p
def normalise(d,sku):
 s=d.sections[0];land=s.page_width>s.page_height
 s.page_width=Cm(29.7 if land else 21);s.page_height=Cm(21 if land else 29.7)
 # The original small margins remain; all physical paper is A4.
 for style in d.styles:
  if style.type in (1,2,3):
   try:style.font.name='Arial'
   except Exception:pass
 for p in all_paras(d):
  for run in p.runs:
   if run.text:run.font.name='Arial'
 # Use the approved restrained gold accent on internal title rows, never on addressee lines.
 for p in d.paragraphs:
  if p.text.strip():
   if p.text.strip().lower().startswith(('кому:', 'в арбитражный суд','в {{')):
    break
   if sku in ('P1','P2') and (p.style.name.lower().startswith('title') or p.text.strip().lower().startswith(('акт ','дополнительное соглашение','письменное поручение','согласование объ','уведомление','обоснование'))):
    for run in p.runs:
     if run.text:run.font.color.rgb=G
   break
def remove_from_heading(d,heading):
 found=False
 for p in list(d.paragraphs):
  if p.text.strip()==heading:found=True
  if found:p._element.getparent().remove(p._element)
 assert found,heading
def remove_last_para(d):
 p=next(x for x in reversed(d.paragraphs) if x.text.strip())
 p._element.getparent().remove(p._element)
 return p.text
def sign_table(d,left,right=None):
 d.add_paragraph().paragraph_format.space_after=Pt(3)
 roles=[left]+([right] if right else [])
 t=d.add_table(rows=1,cols=len(roles));t.style='Table Grid'
 for i,(role,name) in enumerate(roles):
  c=t.rows[0].cells[i]
  c.text=role+'\nДолжность {{...}}    ФИО '+name+'\nПодпись ____________    Дата ____________'
  for p in c.paragraphs:
   p.paragraph_format.space_after=Pt(3)
   for r in p.runs:r.font.name='Arial';r.font.size=Pt(9.5)
def new(title='',send=False):
 d=Document();s=d.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7)
 s.top_margin=Cm(1.8);s.bottom_margin=Cm(1.7);s.left_margin=Cm(2);s.right_margin=Cm(2)
 st=d.styles['Normal'];st.font.name='Arial';st.font.size=Pt(10);st.font.color.rgb=D
 st.paragraph_format.space_after=Pt(6);st.paragraph_format.line_spacing=1.12
 f=s.footer.paragraphs[0];f.text='НА СТОРОНЕ ПОДРЯДЧИКА  /  P4'
 for r in f.runs:r.font.size=Pt(8);r.font.color.rgb=G
 if title and not send:line(d,title,'h')
 return d
def line(d,x,kind='p'):
 p=d.add_paragraph();r=p.add_run(x);r.font.name='Arial'
 if kind=='h':r.bold=True;r.font.size=Pt(13);r.font.color.rgb=G
 return p
def table(d,heads,rows):
 t=d.add_table(rows=1,cols=len(heads));t.style='Table Grid'
 for i,h in enumerate(heads):t.rows[0].cells[i].text=h
 for row in rows:
  cells=t.add_row().cells
  for i,v in enumerate(row):cells[i].text=v
 for row in t.rows:
  for c in row.cells:
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(2)
    for r in p.runs:r.font.name='Arial';r.font.size=Pt(8.5)
def write(d,dir,name):d.save(dir/name)

if OUT.exists():shutil.rmtree(OUT)
for sku in SKUS:
 d=OUT/sku;d.mkdir(parents=True)
 with ZipFile(source(sku)) as z:z.extractall(d)
 for path in sorted(d.glob('*.docx')):
  doc=Document(path)
  changed=sku in ('P1','P2','P4')
  if sku in ('P1','P2','P4'):normalise(doc,sku)
  if sku=='P1' and path.name=='02-ks-3.docx':
   doc.sections[0].top_margin=Cm(0.8);doc.sections[0].bottom_margin=Cm(0.8)
   doc.styles['Normal'].font.size=Pt(9)
   doc.styles['Normal'].paragraph_format.space_after=Pt(0)
   for para in all_paras(doc):
    para.paragraph_format.space_after=Pt(0)
    para.paragraph_format.line_spacing=1.0
  if sku=='P1' and path.name in ('12-pretenziya-na-neoplatu-po-ks-2.docx','13-uvedomlenie-o-prosrochke-oplaty.docx','16-iskovoe-zayavlenie-o-vzyskanii.docx'):
   remove_from_heading(doc,'Порядок заполнения и контроля')
  if sku=='P2' and path.name=='02-soglasovanie-obema.docx':
   p=next(p for p in doc.paragraphs if p.text.startswith('Копию подписанного документа'))
   p._element.getparent().remove(p._element)
  if sku=='P4' and path.name in ('32-kartochka-ispolnitelnoy-shemy.docx','33-akt-peredachi-komplekta-pto.docx','34-sluzhebnaya-zapiska.docx','41-akt-peredachi-ploshchadki-fronta.docx','42-akt-vhodnogo-kontrolya-materialov.docx'):
   n=path.name[:2]
   if n=='42':
    p=next(p for p in doc.paragraphs if p.text.startswith('Представитель передающей стороны'))
    p._element.getparent().remove(p._element)
   else:remove_last_para(doc)
   roles={
    '32':(('Подготовил','{{ФИО}}'),('Проверил','{{ФИО}}')),
    '33':(('Передал','{{ФИО}}'),('Принял','{{ФИО}}')),
    '34':(('Подготовил','{{ФИО}}'),('Решение принял','{{ФИО}}')),
    '41':(('Передал фронт','{{ФИО}}'),('Принял фронт','{{ФИО}}')),
    '42':(('Передающая сторона','{{ФИО}}'),('Принимающая сторона','{{ФИО}}'))}[n]
   sign_table(doc,*roles)
  if sku=='P7' and path.name.startswith(('01-','04-','06-','07-','10-')):
   changed=True
   remove_last_para(doc);sign_table(doc,('Генподрядчик','{{ФИО}}'),('Субподрядчик','{{ФИО}}'))
  if sku=='P8' and path.name.startswith(('05-','06-','07-','10-')):
   changed=True
   remove_last_para(doc)
   if path.name.startswith(('05-','06-')):sign_table(doc,('Генподрядчик','{{ФИО}}'),('Субподрядчик','{{ФИО}}'))
   else:sign_table(doc,('Подрядчик','{{ФИО}}'))
  if sku=='P9' and path.name.startswith(('06-','07-','08-')):
   changed=True
   remove_last_para(doc);sign_table(doc,('Кредитор','{{ФИО}}'))
  if sku=='P10' and path.name.startswith(('03-','04-','05-','06-')):
   changed=True
   last=next(p for p in reversed(doc.paragraphs) if p.text.strip())
   assert '{{ПОДПИСЬ}}' in last.text,(sku,path.name,last.text)
   last.text='{{ДОЛЖНОСТЬ}}    Подпись ______________ / {{ФИО}} /    Дата ____________'
   last.paragraph_format.space_before=Pt(16)
   for r in last.runs:r.font.name='Arial';r.font.size=Pt(10)
  if changed:doc.save(path)
 if sku=='P4':
  # Replace the legacy two-page sendable forms, which asserted automatic acceptance without a completed contractual basis.
  q=new(send=True)
  line(q,'Кому: {{ЗАКАЗЧИК, АДРЕС}}');line(q,'От: {{ПОДРЯДЧИК, ИНН, АДРЕС}}');line(q,'Исх. № {{...}} от {{...}}')
  line(q,'УВЕДОМЛЕНИЕ О ГОТОВНОСТИ ИД К ПЕРЕДАЧЕ','h')
  line(q,'Договор № {{...}} от {{...}}, объект {{...}}, этап/период {{...}}.')
  line(q,'Комплект исполнительной документации подготовлен по описи № {{...}} от {{...}}. Всего {{...}} позиций, {{...}} листов и {{...}} электронных файлов. Передача предложена {{ДАТА, ВРЕМЯ, МЕСТО / ДОГОВОРНЫЙ КАНАЛ}}.')
  table(q,['Раздел комплекта','Реквизиты / количество'],[
   ('Акты освидетельствования','{{НОМЕРА, ДАТЫ, ЛИСТЫ}}'),('Исполнительные схемы','{{НОМЕРА, ВЕРСИИ, ЛИСТЫ}}'),
   ('Журналы, паспорта, протоколы','{{РЕЕСТР, ЛИСТЫ / ФАЙЛЫ}}')])
  line(q,'Просим назначить уполномоченного представителя и подтвердить получение описи либо направить перечень замечаний с реквизитами в срок, предусмотренный договором. Отсутствие ответа зафиксировано подтверждениями направления и получения; дальнейшее оформление определяется договором и законом.')
  line(q,'Приложение: опись № {{...}} на {{...}} л.')
  sign_table(q,('Подрядчик','{{ФИО}}'));write(q,d,'01-uvedomlenie-o-gotovnosti-id.docx')
  q=new(send=True)
  line(q,'АКТ ПРИЁМА-ПЕРЕДАЧИ ИСПОЛНИТЕЛЬНОЙ ДОКУМЕНТАЦИИ № {{...}}','h')
  line(q,'{{МЕСТО}}   {{ДАТА}}   Договор № {{...}} от {{...}}   Объект {{...}}')
  line(q,'Передал: {{ПОДРЯДЧИК, ИНН, ПРЕДСТАВИТЕЛЬ, ПОЛНОМОЧИЯ}}.')
  line(q,'Принял: {{ЗАКАЗЧИК, ИНН, ПРЕДСТАВИТЕЛЬ, ПОЛНОМОЧИЯ}}.')
  line(q,'Комплект передан по описи № {{...}} от {{...}}, {{...}} позиций, {{...}} листов и {{...}} файлов.')
  table(q,['№','Документ / версия','Участок / период','Листы / файлы'],[
   ('1','{{...}}','{{...}}','{{...}}'),('2','{{...}}','{{...}}','{{...}}'),('3','{{...}}','{{...}}','{{...}}')])
  line(q,'Способ передачи {{ЛИЧНО / ЭДО / ИНОЙ КАНАЛ}}; идентификатор отправки и получения {{...}}.')
  line(q,'Замечания к составу при получении: {{ПЕРЕЧЕНЬ / ОТСУТСТВУЮТ}}. Рассмотрение содержания и сроки ответа определяются договором. Приложение: опись № {{...}} на {{...}} л.')
  sign_table(q,('Передал','{{ФИО}}'),('Принял','{{ФИО}}'));write(q,d,'02-akt-priemki-id.docx')
  q=new(send=True)
  line(q,'Кому: {{ЗАКАЗЧИК, АДРЕС}}');line(q,'От: {{ПОДРЯДЧИК, ИНН, АДРЕС}}');line(q,'Исх. № {{...}} от {{...}}  На замечания № {{...}} от {{...}}')
  line(q,'ОТВЕТ НА ЗАМЕЧАНИЯ К ИД','h')
  line(q,'Договор № {{...}} от {{...}}, объект {{...}}, опись передачи № {{...}} от {{...}}.')
  table(q,['Позиция замечаний','Основание и проверка','Ответ / документ'],[
   ('{{НОМЕР, ТЕКСТ}}','{{ПУНКТ ДОГОВОРА, ПРОЕКТ, ДОКУМЕНТ}}','{{ИСПРАВЛЕНО: ВЕРСИЯ / МОТИВИРОВАННОЕ ВОЗРАЖЕНИЕ}}'),
   ('{{НОМЕР, ТЕКСТ}}','{{ПУНКТ ДОГОВОРА, ПРОЕКТ, ДОКУМЕНТ}}','{{СРОК И ДЕЙСТВИЕ / ВОЗРАЖЕНИЕ}}')])
  line(q,'Исправленные документы передаём по описи № {{...}} от {{...}}. Просим подтвердить получение и направить ответ по каждой оставшейся позиции в договорном порядке. Отсутствие ответа зафиксировано отдельно; вопрос оплаты рассматривается по условиям договора и подтверждающим документам.')
  line(q,'Приложения: {{ИСПРАВЛЕННЫЕ ДОКУМЕНТЫ, ОПИСЬ, РАСЧЁТ}}.')
  sign_table(q,('Подрядчик','{{ФИО}}'));write(q,d,'04-pismo-na-zamechaniya.docx')
  q=new('СЛУЖЕБНАЯ ЗАПИСКА О ПРЕПЯТСТВИИ К ОПЛАТЕ')
  line(q,'Кому: {{РУКОВОДИТЕЛЬ}}  От: {{ОТВЕТСТВЕННЫЙ}}  Дата {{...}}')
  line(q,'Договор № {{...}}, объект {{...}}, этап {{...}}. Подтверждённый к оплате объём {{...}} руб.; договорная дата платежа {{...}}; поступило {{...}} руб.; остаток {{...}} руб.')
  line(q,'Передача ИД: опись № {{...}} от {{...}}, дата получения {{...}}. Замечания: № {{...}} от {{...}}, срок и ответ № {{...}}. Неурегулированные позиции {{...}}.')
  line(q,'Предлагаемые действия: {{ПЕРЕДАТЬ ДОКУМЕНТ / ОТВЕТИТЬ ПО ПУНКТАМ / НАПРАВИТЬ ТРЕБОВАНИЕ ОБ ОПЛАТЕ}} до {{...}}. Ответственный {{...}}.')
  sign_table(q,('Подготовил','{{ФИО}}'),('Решение принял','{{ФИО}}'));write(q,d,'05-sluzhebnaya-zapiska.docx')
 if sku=='P1':
  w=load_workbook(d/'14-raschet-procentov-395-gk.xlsx')
  w['Входные данные']['A9']='Внесите ключевую ставку Банка России, действовавшую на начало просрочки, и каждое изменение в периоде расчёта. Источник — cbr.ru, раздел «Ключевая ставка Банка России»; сверьте даты применения.'
  w.save(d/'14-raschet-procentov-395-gk.xlsx')
 if sku=='P8':
  w=load_workbook(d/'02-kalkulyator-usloviy-avansa.xlsx')
  edits={
  ('Условия','A34'):'Проверка исходных ставок и сроков',
  ('Условия','A35'):'Введите ставку обеспечения, сроки оплаты и гарантийное удержание из договора и банковского предложения на дату расчёта. Сверьте оба сценария.',
  ('Сравнение','A19'):'Дополнительный расчёт стоимости финансирования',
  ('Сравнение','A20'):'Для оценки стоимости собственных денег отдельно примените вашу ставку кредита или овердрафта к фактическому отрицательному остатку по месяцам.',
  ('Как читать','A17'):'Совместимость и контроль расчёта',
  ('Как читать','A18'):'После заполнения проверьте итоговые строки в Excel или LibreOffice; при переносе файла сохраните формулы и исходные данные.',
  ('Пример заполнения','A26'):'Сценарий А использует аванс в первом месяце; сценарий Б показывает финансирование собственными средствами. Сравните максимальный отрицательный остаток и стоимость обеспечения на ваших данных.'}
  for (sheet,cell),value in edits.items():w[sheet][cell]=value
  w.save(d/'02-kalkulyator-usloviy-avansa.xlsx')
 if sku in ('P4','P7'):
  notes={
   'P4':{
    '35-obshiy-zhurnal-rabot.xlsx':'Вносите фактические даты, участки, объёмы и исполнителей работ. Связывайте записи с актами и исполнительными схемами. Исправление отражайте новой записью с основанием; перед подписанием сверьте последовательность дат.',
    '36-vhodnoy-kontrol.xlsx':'По каждой партии материалов укажите поставщика, количество, документы о качестве и результат осмотра. Зафиксируйте решение по замечанию, ответственного и связь с актом входного контроля.',
    '37-reestr-pasportov.xlsx':'Свяжите паспорт или сертификат с конкретной партией, поставкой и записью входного контроля. Сверьте срок действия и реквизиты документа перед включением в комплект ИД.',
    '38-reestr-id.xlsx':'По каждому документу укажите объект, участок, версию, статус, номер описи и дату передачи. Сохраните подтверждение получения и ответ по замечаниям рядом с соответствующей записью.'},
   'P7':{
    '02-perechen-rabot.xlsx':'Для каждой позиции укажите конкретный вид работ, единицу, количество, расценку, редакцию проекта и исключения. Сверьте стоимость с ценой договора и подпишите приложение.',
    '03-kalendarnyy-plan.xlsx':'Внесите даты этапов, передачу фронта и исходных данных, зависимые работы и ответственного. Сверьте события и сроки с договором до подписания приложения.',
    '05-grafik-platezhey.xlsx':'Привяжите каждый платёж к проверяемому событию, сумме и сроку. Отдельно отразите аванс, порядок его погашения и гарантийное удержание; сверьте итог с договорной ценой.'}}
  from openpyxl.styles import Alignment
  for filename,note in notes[sku].items():
   book=load_workbook(d/filename);sheet=book['Инструкция']
   sheet['A3']='Порядок заполнения:\n'+note
   sheet['A3'].alignment=Alignment(horizontal='left',vertical='top',wrap_text=True)
   sheet.column_dimensions['A'].width=78
   sheet.row_dimensions[3].height=100
   sheet.page_setup.orientation='portrait';sheet.page_setup.paperSize=sheet.PAPERSIZE_A4
   sheet.sheet_properties.pageSetUpPr.fitToPage=True
   sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=1
   sheet.print_area='A1:A3'
   book.save(d/filename)
 if sku in ('P1','P2'):
  original=d/'00-INSTRUKCIYA.docx'
  pdf=d/'00-INSTRUKCIYA.pdf'
  pdf.unlink()
  res=subprocess.run(['libreoffice',f'-env:UserInstallation=file:///tmp/lo_batch_r2_{sku}','--headless','--convert-to','pdf','--outdir',str(d),str(original)],capture_output=True,text=True,timeout=45)
  assert res.returncode==0 and pdf.exists(),res.stderr
 print('REFINED',sku,len(list(d.iterdir())))
