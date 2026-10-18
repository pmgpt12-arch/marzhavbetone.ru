#!/usr/bin/env python3
"""Address findings from the complete page review; plans are applied via Artifact Tool."""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re,math
R=Path(__file__).resolve().parents[1]
B=R/'tools/candidates/remaining-batch-r3-20261018'
IN=Path('/tmp/mb-r3/input')
X={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
edits=json.loads((B/'text-edits.json').read_text());lookup={(e['sku'],e['file'],e['loc']):e for e in edits}
layouts={}
def file(sku,prefix):return next((IN/sku).glob(prefix+'*.xlsx'))
def value(p,part,cell):
 with ZipFile(p) as z:
  r=E.fromstring(z.read(part));c=r.find(f'.//x:c[@r="{cell}"]',X)
  if c is None:return None
  assert c.find('x:f',X) is None,(p,cell,'formula requires separate literal plan')
  if c.get('t')=='inlineStr':return ''.join(c.xpath('.//x:t/text()',namespaces=X))
  if c.get('t')=='s':
   ss=E.fromstring(z.read('xl/sharedStrings.xml'));return ''.join(list(ss)[int(c.find('x:v',X).text)].itertext())
  v=c.find('x:v',X);return v.text if v is not None else None
def text(sku,prefix,index,changes):
 p=file(sku,prefix);part=f'xl/worksheets/sheet{index}.xml'
 for cell,new in changes.items():
  old=value(p,part,cell);k=(sku,p.name,part+':'+cell)
  lookup[k]={'sku':sku,'file':p.name,'loc':part+':'+cell,'old':old,'new':new}
def layout(sku,prefix,index,**options):
 p=file(sku,prefix);key=sku+'/'+p.name
 layouts.setdefault(key,{'sku':sku,'file':p.name,'sheets':{}})['sheets'][f'xl/worksheets/sheet{index}.xml']=options
# The three contractual appendices contain their own identification and signature fields.
for prefix,number,end,mid in [('02-',1,'I','E'),('03-',2,'I','E'),('05-',3,'J','F')]:
 text('P7',prefix,1,{
 'A2':f'Приложение № {number} к договору № {{{{НОМЕР_ДОГОВОРА}}}} от {{{{ДАТА_ДОГОВОРА}}}}.\nОбъект: {{{{ОБЪЕКТ}}}}. Генподрядчик: {{{{НАИМЕНОВАНИЕ_ГЕНПОДРЯДЧИКА}}}}. Субподрядчик: {{{{НАИМЕНОВАНИЕ_СУБПОДРЯДЧИКА}}}}.',
 'A105':'Генподрядчик',mid+'105':'Субподрядчик',
 'A106':'{{ДОЛЖНОСТЬ_ФИО_ПОЛНОМОЧИЯ}}\nПодпись __________________\nДата __________________',
 mid+'106':'{{ДОЛЖНОСТЬ_ФИО_ПОЛНОМОЧИЯ}}\nПодпись __________________\nДата __________________'})
 left='D' if end=='I' else 'E'
 layout('P7',prefix,1,merges=[f'A105:{left}105',f'{mid}105:{end}105',f'A106:{left}106',f'{mid}106:{end}106'],copy_style={a:'A4' for a in ['A105',mid+'105','A106',mid+'106']},wrap=['A2','A106',mid+'106'],row_heights={'2':54,'105':18,'106':60},print_area=f'A1:{end}106',repeat_rows='1:3')
text('P2','07-',1,{'A2':'Расчёт № {{НОМЕР}} от {{ДАТА}} к договору № {{НОМЕР_ДОГОВОРА}} от {{ДАТА_ДОГОВОРА}}.\nОбъект: {{ОБЪЕКТ}}. Подрядчик: {{ПОДРЯДЧИК}}. Заказчик: {{ЗАКАЗЧИК}}.','A106':'Подрядчик','F106':'Заказчик','A107':'{{ДОЛЖНОСТЬ_ФИО_ПОЛНОМОЧИЯ}}\nПодпись __________________\nДата __________________','F107':'{{ДОЛЖНОСТЬ_ФИО_ПОЛНОМОЧИЯ}}\nПодпись __________________\nДата __________________'})
layout('P2','07-',1,merges=['A106:E106','F106:J106','A107:E107','F107:J107'],copy_style={a:'A4' for a in ['A106','F106','A107','F107']},wrap=['A2','A107','F107'],row_heights={'2':54,'106':18,'107':60},print_area='A1:J107',repeat_rows='1:3')
text('P2','07-',2,{'A3':'По каждой позиции укажите работу или ресурс, единицу измерения, количество, цену и источник цены с номером и датой документа. Коэффициент 1,15 увеличивает стоимость на 15%; пустая ячейка коэффициента учитывается как 1. Проверьте суммы, договорные реквизиты и подписи. Приложите согласованный расчёт к соглашению 11.'})
text('P2','08-',2,{'A3':'Регистрируйте каждую дополнительную работу с датой, инициатором, местом, основанием, единицей измерения и объёмом. Укажите стоимость по расчёту 07. Раздельно отмечайте согласование, выполнение, включение в КС-2 и фактическую оплату. Свяжите запись с формами 02 и 04, фотографиями и платёжными документами. Исправления вносите с сохранением истории и основания изменения.'})
for prefix in ['07-','08-']:
 layout('P2',prefix,2,wrap=['A3'],row_heights={'3':135},print_area='A1:A3')
# The calculation summary is an identifiable, signable attachment.
text('P1','14-',1,{'C4':'Задолженность на первый день просрочки с учётом полученных ранее авансов и оплат. Последующие оплаты внесите в таблицу «Частичные оплаты».','C5':'День, следующий за последним днём срока оплаты, определённого по договору с учётом статей 191 и 193 ГК РФ.','C6':'Дата претензии или иска; для требования «по день фактической уплаты» — дата составления расчёта.'})
text('P1','14-',3,{
 'A1':'Расчёт взыскиваемой суммы',
 'A2':'Подрядчик: {{НАИМЕНОВАНИЕ_ПОДРЯДЧИКА}}. Заказчик: {{НАИМЕНОВАНИЕ_ЗАКАЗЧИКА}}.\nДоговор № {{НОМЕР_ДОГОВОРА}} от {{ДАТА_ДОГОВОРА}}. Объект: {{ОБЪЕКТ}}.',
 'A12':'Порядок начисления процентов','A15':'Подписание расчёта',
 'A16':'Подтверждающие документы: {{НОМЕРА_ДАТЫ_АКТОВ_ПЛАТЕЖЕЙ_ВЫПИСОК}}.',
 'A17':'Приложение: расчёт по периодам на {{КОЛИЧЕСТВО_ЛИСТОВ}} листах.',
 'A18':'{{ДОЛЖНОСТЬ_ПОДПИСАНТА}}  Подпись __________ / {{ФИО_ПОДПИСАНТА}} /',
 'A19':'Дата {{ДАТА_ДОКУМЕНТА}}. Полномочия {{ОСНОВАНИЕ_ПОЛНОМОЧИЙ}}.'})
layout('P1','14-',1,columns={'A':28,'B':18,'C':32},merges=['A1:C1','A2:C2'],wrap=['A1','A2','C4','C5','C6','A47'],row_heights={'1':24,'2':48,'4':84,'5':72,'6':60,'47':150},print_area='A1:C47',repeat_rows='1:1',break_before=[33])
layout('P1','14-',2,columns=dict(zip('ABCDEFGH',[16,16,11,18,11,12,18,28])),merges=['A1:H1','A2:H2'],wrap=['A1','A2'],row_heights={'1':24,'2':36,'3':36,**{str(i):16 for i in range(4,44)}},print_area='A1:H47',repeat_rows='1:3',break_before=[24])
layout('P1','14-',3,wrap=['A2','A16','A17','A18','A19'],row_heights={'2':60,'16':32,'17':28,'18':40,'19':32},print_area='A1:B19')
# Remove unnecessary page tails while retaining every model input, formula and status.
layout('P8','02-',1,row_heights={'35':36,'38':36},print_area='A1:D38',repeat_rows='1:4')
layout('P8','02-',2,wrap=['D42'],row_heights={'42':42},repeat_rows='1:4')
for index in [3,4]:layout('P8','02-',index,repeat_rows='1:4')
layout('P8','02-',5,row_heights={'17':54})
layout('P8','02-',6,row_heights={**{str(i):34 for i in range(3,9)},'18':32,'21':36},print_area='A1:B21',fit_height=1)
text('P8','09-',4,{'A1':'Реестр документально подтверждённых встречных сумм'})
text('P8','09-',6,{'A8':'Субподрядчик: {{НАИМЕНОВАНИЕ_СУБПОДРЯДЧИКА}}. Генподрядчик: {{НАИМЕНОВАНИЕ_ГЕНПОДРЯДЧИКА}}.','A21':'От Субподрядчика\n{{ДОЛЖНОСТЬ_ФИО_ПОЛНОМОЧИЯ}}','C21':'От Генподрядчика\n{{ДОЛЖНОСТЬ_ФИО_ПОЛНОМОЧИЯ}}','D10':'Подтверждающие документы','D11':'{{ОСНОВАНИЕ_НАЧАЛЬНОГО_САЛЬДО}}','D12':'{{НОМЕРА_ДАТЫ_АКТОВ}}','D13':'{{ПЛАТЕЖИ_АВАНСА}}','D14':'{{ПЛАТЕЖИ_ЗА_РАБОТЫ}}','A25':'Направьте акт по согласованному договорному каналу. Сохраните подписанный экземпляр, подтверждение направления, получения и ответ второй стороны.'})
# All introductory paragraphs are visible; heading blocks stay with their text.
p=file('P8','09-')
with ZipFile(p) as z:r=E.fromstring(z.read('xl/worksheets/sheet1.xml'))
heights={}
for row in r.findall('x:sheetData/x:row',X):
 i=row.get('r');a=r.find(f'.//x:c[@r="A{i}"]',X)
 t=lookup.get(('P8',p.name,f'xl/worksheets/sheet1.xml:A{i}'),{}).get('new',value(p,'xl/worksheets/sheet1.xml','A'+i))
 heights[i]=max(18,math.ceil(len(t or '')/115)*14+5) if t else 8
layout('P8','09-',1,row_heights=heights,print_area='A1:A26',break_before=[16])
layout('P8','09-',2,row_heights={'9':90,'12':60,'16':48,'17':72,'18':48,'29':40},print_area='A1:C29',break_before=[15])
layout('P8','09-',3,print_area='A1:L57',repeat_rows='1:5',break_before=[26])
layout('P8','09-',4,row_heights={'5':48,'40':30,'41':30},print_area='A1:G41',repeat_rows='1:5',break_before=[22])
layout('P8','09-',5,row_heights={'17':60,'21':60,'23':48,'24':48,'31':48,'32':72,'37':90,'41':60,'42':60},print_area='A1:C44',repeat_rows='1:3',break_before=[19,29,36])
layout('P8','09-',6,merges=['A8:D8','A21:B21','C21:D21'],copy_style={'A8':'A9'},wrap=['A8','A21','C21'],row_heights={'8':36,'21':42},print_area='A6:D23',fit_height=1,repeat_rows=None)
layout('P8','09-',7,merges=[f'B{i}:C{i}' for i in [6,7,8,9,12,13,14,16,17,19,20,21,22,23,24]],row_heights={'8':40,'12':36,'13':36,'14':36,'16':36,'22':36},print_area='A1:C25',break_before=[15])
# Replace remaining advance-offset labels by the corresponding financial term.
for p in (IN/'P8').glob('*.xlsx'):
 with ZipFile(p) as z:
  for part in z.namelist():
   if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',part):continue
   for c in E.fromstring(z.read(part)).findall('.//x:c',X):
    if c.find('x:f',X) is not None:continue
    old=value(p,part,c.get('r'))
    if not old or not re.search('зач[её]т|зачтено',old,re.I):continue
    new=re.sub('Зачтено в сч[её]т аванса','Погашение аванса',old)
    new=re.sub('зачтено в сч[её]т аванса','погашение аванса',new)
    new=re.sub('Зач[её]т аванса','Погашение аванса',new)
    new=re.sub('зач[её]т аванса','погашение аванса',new)
    if new!=old:
     key=('P8',p.name,part+':'+c.get('r'))
     if key not in lookup:lookup[key]={'sku':'P8','file':p.name,'loc':key[2],'old':old,'new':new}
(B/'text-edits.json').write_text(json.dumps(list(lookup.values()),ensure_ascii=False,indent=2)+'\n')
(B/'layout-edits.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2)+'\n')
# Only quoted display literals change. Operators, functions, ranges and criteria remain exact.
mapping={
 'дата по вашей записи прошла — файл «Что делать, если срок пропущен» и юрист сегодня':'Указанная контрольная дата истекла: проверьте срок и процессуальный порядок по файлу 09.',
 'дней до вашей даты: ':'Дней до контрольной даты: ',
 'сумма есть, подписи обеих сторон нет — отдельно обсудите с юристом':'Акт не подписан обеими сторонами: проверьте подтверждения выполнения и сдачи.',
 'отметьте, идёт ли копия в пакет':'Отметьте включение копии в перечень приложений.',
 'после принятия заявления — возможно текущий платёж (ст. 5), к юристу':'Проверьте признаки текущего платежа по статье 5 Закона № 127-ФЗ.',
 'ОШИБКА: зачтено и оплачено больше стоимости акта':'ОШИБКА: погашение аванса и оплата превышают стоимость акта.',
 'ОШИБКА: зачёт аванса по неподписанному акту':'ОШИБКА: погашение аванса отнесено к акту, не подписанному обеими сторонами.',
 'акт подписан, но по нему ничего не зачтено и не оплачено — проверьте':'По подписанному акту не отражены погашение аванса и оплата: проверьте платежи.',
 'акт не подписан: без даты передачи он в расчёте не работает':'Акт не подписан: укажите дату передачи.',
 'акт не подписан: нечем подтвердить передачу':'Акт не подписан: укажите документ, подтверждающий передачу.',
 'заявлять можно, но обосновывать придётся отдельно':'Проверьте самостоятельное основание требования и подтверждающие документы.',
 'в вашу пользу':'К оплате Субподрядчику',
 'сходится':'Расхождений не выявлено',
 'ПРОВЕРЬТЕ: деньги приходили под акты, которые не подписаны обеими сторонами — расхождение ':'ПРОВЕРЬТЕ: платежи отнесены к актам, не подписанным обеими сторонами; расхождение ',
 'ПРОВЕРЬТЕ: требуют больше, чем было получено авансом':'ПРОВЕРЬТЕ: сумма требования превышает полученный аванс.',
 'Условия заполнены. Обеспечение платное — его стоимость уже вычтена из кассы':'Условия заполнены. Стоимость обеспечения учтена в денежных расходах.',
 'Оба графика закрывают 100% объёма':'Сумма долей выполнения в каждом сценарии составляет 100%.',
 'Сумма долей не равна 100: расчёт закроет не весь договор':'Сумма долей выполнения отличается от 100%: проверьте полноту графика.',
 'Из КС этого месяца удерживают больше, чем она стоит: погашение аванса и гарантийное удержание вместе больше объёма':'Погашение аванса и гарантийное удержание превышают стоимость работ данного месяца.',
 'Месяц за пределами срока объекта, а объём в графике есть':'Объём работ указан за пределами срока выполнения: сверьте график и условия.',
 'минуса нет':'Отсутствует',
 'Сценарий Б замораживает меньше ваших денег в худшей точке':'Сценарий Б снижает максимальную потребность в финансировании.',
 'Сценарий Б замораживает больше ваших денег в худшей точке':'Сценарий Б увеличивает максимальную потребность в финансировании.',
 'Оба сценария дают одинаковую худшую точку':'Максимальная потребность в финансировании одинакова.'
}
formula=[];literal=re.compile(r'"(?:[^"]|"")*"')
for p in sorted(IN.rglob('*.xlsx')):
 with ZipFile(p) as z:
  for part in z.namelist():
   if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',part):continue
   for c in E.fromstring(z.read(part)).findall('.//x:c',X):
    f=c.find('x:f',X)
    if f is None or not f.text:continue
    old=f.text
    new=literal.sub(lambda m:'"'+mapping.get(m[0][1:-1],m[0][1:-1])+'"',old)
    if new!=old:
     assert literal.sub('""',old)==literal.sub('""',new)
     formula.append({'sku':p.parent.name,'file':p.name,'part':part,'cell':c.get('r'),'old':'='+old,'new':'='+new})
(B/'formula-text-edits.json').write_text(json.dumps(formula,ensure_ascii=False,indent=2)+'\n')
print('LAYOUT_PLANS',len(layouts),'TEXT_EDITS',len(lookup),'FORMULA_DISPLAY_EDITS',len(formula))
