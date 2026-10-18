from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree
import re,subprocess,shutil,json
ROOT=Path('.')
BASE=ROOT/'tools/candidates/t3-buyer-review-20261017/R1'
OUT=ROOT/'tools/candidates/t3-unilateral-writeoff-20261018/R2'
TITLE='Система подготовки возражений на односторонний акт или списание в одностороннем порядке'
OLD='Система подготовки возражений на односторонний акт или зачёт'
FILE03='03-vozrazheniya-na-odnostoronnee-spisanie.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
maps={
 '01-poryadok-deystviy.docx':{
 'Порядок действий при получении акта или уведомления о зачёте':'Порядок действий при получении акта или уведомления о списании в одностороннем порядке',
 'Уведомление о зачёте либо удержании суммы из оплаты':'Уведомление о списании суммы из оплаты в одностороннем порядке',
 '03 Возражения на зачёт или удержание':'03 Возражения на списание в одностороннем порядке',
 'Проверьте содержание документа, а не только его название. Для зачёта встречных требований, договорного удержания и определения сальдо могут действовать разные условия; отберите доводы по фактической конструкции.':'Списание в одностороннем порядке — уменьшение заказчиком причитающейся Подрядчику оплаты. Проверьте основание: прекращение встречных требований по статье 410 ГК РФ, договорное удержание или определение сальдо. Отберите доводы по применённому механизму.'
 },
 '03-vozrazheniya-na-zachet.docx':{
 'Возражения на зачёт или удержание':'Возражения на списание в одностороннем порядке',
 'Подрядчик оспаривает основание и размер заявленного требования в следующей части: {{ПРЕДМЕТ_ВОЗРАЖЕНИЙ}}.':'Подрядчик оспаривает списание в одностороннем порядке и заявленное в его обоснование требование в следующей части: {{ПРЕДМЕТ_ВОЗРАЖЕНИЙ}}.',
 '3. Для зачёта встречных требований: {{ДОВОД_О_УСЛОВИЯХ_ЗАЧЕТА}}. ':'3. В отношении прекращения встречных требований по статье 410 ГК РФ: {{ДОВОД_ПО_СТАТЬЕ_410}}.',
 },
 '04-slovar-poley.docx':{
 'Возражение на сумму':'Возражение на списание в одностороннем порядке',
 'ДОВОД_О_УСЛОВИЯХ_ЗАЧЕТА':'ДОВОД_ПО_СТАТЬЕ_410',
 'Только при зачёте по статье 410 ГК РФ: конкретное несоблюдённое условие и доказательство.':'При ссылке заказчика на статью 410 ГК РФ проверьте встречность, однородность, срок исполнения требований и получение заявления. Укажите конкретное нарушение и доказательство.'
 }
}
for fname,repls in maps.items():
 with ZipFile(BASE/fname) as z:
  xml=etree.fromstring(z.read('word/document.xml'))
  seen=set()
  for node in xml.xpath('//w:t',namespaces=NS):
   if node.text in repls:seen.add(node.text);node.text=repls[node.text]
  assert seen==set(repls), 'unmatched replacements '+str(set(repls)-seen)
  dest=OUT/(FILE03 if fname.startswith('03-') else fname)
  with ZipFile(dest,'w') as o:
   for item in z.infolist():o.writestr(item,etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
shutil.copy2(BASE/'02-vozrazheniya-na-akt.docx',OUT/'02-vozrazheniya-na-akt.docx')
# Reuse established document style for the changed PDF instruction.
builder=(ROOT/'tools/candidates/t3-buyer-review-20261017/build_candidate.py').read_text()
prefix=builder[:builder.index("d=base();title(d,'Порядок действий")]
scope={};exec(prefix,scope);scope['O']=OUT
d=scope['base']();scope['title'](d,TITLE)
scope['p'](d,'Результат: письменные возражения с привязкой к полученному документу, договору, доказательствам и расчёту.')
scope['h'](d,'Состав комплекта')
for fname,desc in [('01-poryadok-deystviy.docx','Действия в день получения и контроль последующих документов.'),('02-vozrazheniya-na-akt.docx','Форма возражений на акт о недостатках.'),(FILE03,'Форма возражений на списание в одностороннем порядке.'),('04-slovar-poley.docx','Источники для заполнения полей и проверка перед направлением.')]:
 scope['p'](d,fname+' — '+desc)
scope['h'](d,'Порядок действий')
scope['p'](d,'1. Зарегистрируйте полученные документы и зафиксируйте сроки по договору. 2. Отберите нужную форму: 02, 03 либо обе по отдельности. 3. Заполните поля по словарю и удалите неприменимые доводы. 4. Сверьте расчёт, приложения и полномочия подписанта. 5. Направьте по договорному каналу и сохраните подтверждение доставки.')
scope['h'](d,'Контроль перед подписанием')
scope['p'](d,'Для возражений на акт проверьте уведомление об осмотре и спорные позиции. При списании в одностороннем порядке проверьте основание уменьшения оплаты и расчёт суммы. Сохраните возражение и подтверждения направления с материалами сделки.')
d.save(OUT/'00-START-HERE.docx')
subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/lo-t3-r2-20261018','--headless','--convert-to','pdf','--outdir',str(OUT),str(OUT/'00-START-HERE.docx')],check=True,timeout=60)
(OUT/'00-START-HERE.docx').unlink()
# Use only the new five buyer files in the active source.
src=ROOT/'products-storage/17-odnostoronniy-akt-i-zachet'
for f in src.iterdir():
 if f.is_file():f.unlink()
for f in OUT.iterdir():shutil.copy2(f,src/f.name)
# Product page and T3 catalog card only; preserve adjacent product copy.
p=ROOT/'products/t3-odnostoronniy-akt-i-zachet.html';s=p.read_text().replace(OLD,TITLE).replace('03-vozrazheniya-na-zachet.docx',FILE03)
repls={
 'возражение на зачёт':'возражение на списание в одностороннем порядке',
 'Возражения на акт или зачёт':'Возражения на акт или списание в одностороннем порядке',
 'уведомление о зачёте':'уведомление о списании в одностороннем порядке',
 'на зачёт или удержание':'на списание в одностороннем порядке',
 'заявлен зачёт, договорное удержание или расчёт сальдо':'заявлено прекращение встречных требований по статье 410 ГК РФ, договорное удержание или определение сальдо'
}
for a,b in repls.items():s=s.replace(a,b)
p.write_text(s)
p=ROOT/'products-config.php';s=p.read_text().replace(OLD,TITLE);p.write_text(s)
p=ROOT/'katalog.html';s=p.read_text().replace(OLD,TITLE)
a=s.index('<article class="product-card"><div class="product-number">T3</div>');b=s.index('</article>',a)+10
card=s[a:b].replace('зачёту или удержанию','списанию в одностороннем порядке').replace('уведомление о зачёте','уведомление о списании в одностороннем порядке').replace('Возражения на зачёт или удержание','Возражения на списание в одностороннем порядке')
s=s[:a]+card+s[b:]
# Update the T3 Product item in JSON-LD, including the stale target price.
a=s.index('"name": "Односторонний акт или зачёт: возражения в срок"');b=s.index('"priceCurrency"',a)
chunk=s[a:b].replace('Односторонний акт или зачёт: возражения в срок',TITLE).replace('"price": "990"','"price": "14900"')
s=s[:a]+chunk+s[b:];p.write_text(s)
# Correct the T3 link blocks on two articles and the lead material.
for path in ['articles/garantiynoe-uderzhanie-v-ks-2-i-ks-3.html','articles/raboty-ne-prinyaty.html','materialy/uderzhaniya.html']:
 p=ROOT/path;s=p.read_text();lines=s.splitlines(keepends=True)
 for i,line in enumerate(lines):
  if 't3-odnostoronniy-akt-i-zachet.html' not in line or ('<p ' not in line and '<article ' not in line):continue
  line=line.replace('Односторонний акт или зачёт: возражения в срок',TITLE).replace('990 ₽','14 900 ₽').replace('уведомление о зачёте','уведомление о списании в одностороннем порядке')
  line=line.replace('Удержание переименовали в зачёт и возражать нужно в срок:','Заказчик уменьшил оплату в одностороннем порядке — подготовьте возражение:')
  line=line.replace('и срок на возражение считается днями','и требуется ответить в договорный срок').replace(' — там счёт идёт на дни:',' — подготовьте письменные возражения:')
  lines[i]=line
 p.write_text(''.join(lines))
p=ROOT/'diagnostika.html';s=p.read_text();s=s.replace('"url":"/products/t3-odnostoronniy-akt-i-zachet.html","price":990','"url":"/products/t3-odnostoronniy-akt-i-zachet.html","price":14900');p.write_text(s)
# Package exactly five buyer files.
archive=OUT.parent/'T3-odnostoronnee-spisanie-5-files-R2.zip'
files=sorted(OUT.iterdir());assert len(files)==5
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for f in files:z.write(f,f.name)
with ZipFile(archive) as z:assert z.testzip() is None and len(z.namelist())==5
print('R2_CREATED',archive)
