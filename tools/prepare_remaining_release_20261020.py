#!/usr/bin/env python3
"""Promote only the exact owner-approved R3 members and their sale surfaces."""
from pathlib import Path
from hashlib import sha256
from html import escape
from zipfile import ZipFile
import json, re, shutil, subprocess
from bs4 import BeautifulSoup

R=Path(__file__).resolve().parents[1]
B=R/'tools/candidates/remaining-batch-r3-20261018'
O=B/'release-20261020'
APPROVED='37c1b22c092ef979b4dd2151f018b6812dad017532d842159be8cf0fb70f0789'
DATA={
'p1':('Система получения оплаты за выполненные работы',29900,'p1-oplata-po-ks2.html',
'Работы выполнены, но сдача документов или просроченная оплата задерживают поступление денег. Система связывает подтверждение объёмов, передачу документов и подготовку требования об оплате.',
'Проверенный комплект для сдачи работ; подтверждения передачи и приёмки; расчёт задолженности и процентов с документами для претензионной и судебной работы.',
['Сопоставьте договор, объёмы, акты и приложения.','Оформите сдачу работ и сохраните подтверждения передачи.','При просрочке сверьте расчёты и подготовьте уведомление, претензию и последующие документы.']),
'p2':('Система оформления и получения оплаты за дополнительные работы',24900,'p2-dopolnitelnye-raboty.html',
'Дополнительный объём выходит за согласованную стоимость и сроки. Зафиксируйте поручение, согласуйте условия и соберите документы, подтверждающие выполнение и стоимость работ.',
'Документально подтверждённый дополнительный объём, расчёт стоимости, согласованные изменения договора и комплект для предъявления работ к оплате.',
['Проверьте основания дополнительного объёма и полномочия представителей.','Направьте уведомление, согласуйте стоимость и сроки письменными документами.','Ведите учёт выполнения, оформите освидетельствование и предъявите документы для оплаты.']),
'p4':('Система ведения, проверки и передачи исполнительной документации',24900,'p4-ispolnitelnaya-dokumentaciya-pto.html',
'Неполная исполнительная документация и незакрытые замечания задерживают сдачу работ. Организуйте учёт документов, проверку комплектности, устранение замечаний и подтверждение передачи.',
'Проверенный состав исполнительной документации, реестры состояния и замечаний, документы о готовности, приёмке и передаче комплекта.',
['Определите состав документации по договору, проекту и применимым требованиям.','Ведите реестры, оформляйте предусмотренные акты и контролируйте устранение замечаний.','Проверьте комплект, направьте уведомление и подтвердите передачу документов.']),
'p7':('Система проверки и согласования договора субподряда',24900,'p7-dogovor-podryada.html',
'Условия договора определяют, какие работы, расходы и сроки окажутся на стороне подрядчика. До подписания сопоставьте предмет, цену, приёмку, графики и порядок изменения обязательств.',
'Согласованные условия договора и приложений, перечень требуемых изменений и формы их письменного оформления.',
['Проверьте предмет, объёмы, сроки, цену, порядок приёмки и оплаты.','Согласуйте перечень работ, календарный план и график платежей.','До подписания внесите изменения в договор; последующие изменения оформляйте дополнительными соглашениями.']),
'p8':('Система управления авансами и расчётами по договору подряда',24900,'p8-avans-po-dogovoru-subpodryada.html',
'Условия аванса влияют на потребность в финансировании и размер обязательств при прекращении работ. Сравните сценарии, согласуйте порядок погашения и подтвердите расчёт отработанной части.',
'Сравнение условий финансирования, оформленные авансовые положения и проверенный расчёт для ответа на требование о возврате остатка.',
['Внесите условия договора и сравните денежные потоки по двум сценариям.','Согласуйте выплату и погашение аванса письменными документами.','При требовании возврата сопоставьте оплату, выполненные работы и встречные обязательства; подготовьте расчёт и ответ.']),
'p9':('Система защиты требований подрядчика при банкротстве генподрядчика',24900,'p9-bankrotstvo-genpodryadchika.html',
'Банкротство контрагента требует контроля публикаций, сроков и подтверждающих документов. Определите процессуальный порядок предъявления требования и соберите доказательства задолженности.',
'Реестр документов и контрольных дат, подготовленные обращения управляющему и комплект для заявления требования в деле о банкротстве.',
['Проверьте сведения о деле, стадию процедуры, публикации и применимый срок.','Сопоставьте задолженность с договорами, актами, платежами и перепиской.','Подготовьте обращение и приложения; контролируйте рассмотрение и последующие процессуальные действия.']),
'p10':('Система подготовки ответа на претензию заказчика',17900,'p10-otvet-na-pretenziyu.html',
'Полученная претензия требует проверки оснований, суммы и срока ответа. Систематизируйте требования и доказательства, выберите подходящую форму и подготовьте мотивированную позицию.',
'Зарегистрированная претензия, проверенные основания и расчёт, мотивированный ответ с подтверждающими документами и доказательствами направления.',
['Зарегистрируйте претензию и проверьте договорный срок ответа.','Сопоставьте каждый довод с договором, документами выполнения и расчётом.','Подготовьте ответ по подходящему сценарию, приложите доказательства и сохраните подтверждение отправки.']),
'p13':('Система проверки сметной документации и выявления неоплачиваемых затрат',17900,'p13-chto-v-smete-ne-oplatyat.html',
'Расходы, отсутствующие в смете или условиях договора, уменьшают заработанный результат по объекту. Сопоставьте состав работ, сопутствующие затраты и основания их оплаты до согласования стоимости.',
'Перечень затрат с основаниями, оценка покрытия договорной ценой и документы для согласования необходимых изменений.',
['Сопоставьте проект, смету, условия выполнения и распределение обязанностей.','Зарегистрируйте затраты и проверьте их покрытие стоимостью работ.','Подготовьте запрос и протокол разногласий; согласуйте изменения до подписания документов.'])}
LABELS={
'p1':'Инструкция Word|Инструкция PDF|Порядок начала работы|Форма КС-2|Форма КС-3|Акт выполненных работ|Акт приёмки|Акт передачи документов|Форма КС-6а|Рабочий реестр объёмов|Реестр замечаний|Реестр передачи|Контроль перед передачей|Порядок хранения|Словарь полей|Претензия об оплате|Уведомление о просрочке оплаты|Расчёт процентов|Порядок действий при задержке оплаты|Исковое заявление',
'p2':'Инструкция Word|Инструкция PDF|Порядок начала работы|Поручение на дополнительный объём|Согласование объёма|Уведомление о дополнительных работах|Акт освидетельствования скрытых работ|Изменение сроков|Письмо о приостановке|Расчёт стоимости|Журнал дополнительных работ|Контроль фотофиксации|Порядок оформления дополнительных работ|Соглашение об объёме и цене|Соглашение о сроках',
'p4':'Порядок начала работы|Уведомление о готовности ИД|Акт приёмки ИД|Перечень замечаний|Письмо по замечаниям|Служебная записка|Реестр замечаний|График устранения|Порядок работы с ИД|Контроль рисков|Акт освидетельствования скрытых работ|Карточка исполнительной схемы|Акт передачи комплекта ПТО|Служебная записка по комплекту|Общий журнал работ|Рабочий журнал производства работ|Журнал входной верификации|Рабочий реестр входного контроля|Реестр паспортов|Реестр ИД|Порядок работы с замечаниями|Ежемесячная проверка|Акт передачи площадки и фронта работ|Акт входного контроля материалов|Предупреждение по статье 716 ГК РФ',
'p7':'Инструкция Word|Инструкция PDF|Порядок начала работы|Договор субподряда|Перечень работ|Календарный план|Порядок приёмки|График платежей|Соглашение об объёме|Соглашение о сроках|Контроль договорных рисков|Проверка договора|Протокол разногласий',
'p8':'Порядок начала работы|Словарь полей|Расчёт условий аванса|Проверка четырёх условий аванса|Порядок согласования аванса|Протокол разногласий|Соглашение о погашении аванса|Требование о выплате аванса|Порядок действий при требовании возврата|Расчёт отработанной части аванса|Ответ на требование о возврате',
'p9':'Порядок начала работы|Словарь полей|Порядок действий при банкротстве|Признаки финансовых затруднений|Реестр документов и дат|Перечень приложений к требованию|Уведомление управляющему|Запрос о состоянии расчётов|Заявление о включении требования в реестр|Действия при пропуске срока',
'p10':'Инструкция|Карта претензии|Порядок подготовки ответа|Ответ на претензию|Ответ на гарантийную претензию|Ответ на прямое требование|Уведомление контрагенту|Блоки для подготовки ответа',
'p13':'Инструкция|Словарь полей|Порядок проверки сметы|Проверка неучтённых затрат|Реестр затрат по объекту|Запрос о включении затрат|Протокол разногласий по смете|Накладные расходы и сметная прибыль|Зимнее удорожание и временные здания|Вывоз отходов, транспорт и непредвиденные затраты'}

def sha(data):return sha256(data).hexdigest()
def read_catalog():return json.loads(subprocess.check_output(['php','-r','define("ORDERS_DIR",sys_get_temp_dir());require "products-config.php";echo json_encode(mvb_products(),JSON_UNESCAPED_UNICODE);'],cwd=R))
def main():
 O.mkdir(exist_ok=True)
 assert not (O/'release-plan.json').exists(),'Preparation already frozen; inspect before rerun'
 m=json.loads((B/'final-buyer-review-20261020/BATCH-MANIFEST-R3.json').read_text())
 assert sha((B/'final-buyer-review-20261020'/m['archive']).read_bytes())==APPROVED
 before_catalog=read_catalog();original={};changed=set()
 def put(p,s):
  data=s.encode() if isinstance(s,str) else s
  old=p.read_bytes() if p.exists() else None
  if old!=data:
   rel=str(p.relative_to(R));original.setdefault(rel,sha(old) if old is not None else None)
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);changed.add(rel)
 approval={'status':'OWNER_ACCEPTED_AND_RELEASE_AUTHORIZED','message':'Файлы согласованы, сохраняй и размещай','at':'2026-10-20T13:09:31+07:00','approved_outer_zip_sha256':APPROVED,'scope':'Eight remaining products plus isolated P3 AOSR correction; scoped site, approved prices and delivery; no general deploy.','packages':[{k:v for k,v in p.items() if k in ['sku','archive','sha256','file_count']} for p in m['packages']]}
 (O/'owner-acceptance.json').write_text(json.dumps(approval,ensure_ascii=False,indent=2)+'\n')
 packages=[]
 for p in m['packages']:
  sku=p['sku'].lower();d=R/'products-storage'/before_catalog[sku]['dir']
  old={str(f.relative_to(d)):sha(f.read_bytes()) for f in d.rglob('*') if f.is_file()}
  new={v['file']:v['sha256'] for v in p['members']}
  if sku=='p3':
   delta={n for n in set(old)|set(new) if old.get(n)!=new.get(n)}
   assert delta <= {'00-START-HERE.txt','03-akt-skrytyh-rabot.docx','03-akt-skrytyh-rabot.pdf','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md','.htaccess'},delta
  for f in d.iterdir():
   if f.is_file() and f.name not in {'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'} and f.name not in new:f.unlink()
  with ZipFile(B/'final-buyer-review-20261020'/p['archive']) as z:
   for n in new:
    data=z.read(n);assert sha(data)==new[n];(d/n).write_bytes(data)
  entry={'sku':sku,**before_catalog[sku],'approved_zip_sha256':p['sha256'],'count':len(new),'members':new}
  if sku in DATA:
   title,price,page,lead,result,steps=DATA[sku];entry.update(name=title,price=price*100,page='products/'+page)
   start='00-START-HERE.pdf' if sku in {'p10','p13'} else '00-INSTRUKCIYA.pdf' if sku in {'p1','p2','p7'} else '00-START-HERE.txt'
   letter=f'Тема: {title}\n\nЗдравствуйте!\n\nВаш комплект готов к скачиванию. Ссылка действует 1 час. Сохраните архив и распакуйте его.\n\n1. Откройте {start}.\n2. Выберите порядок действий по вашей ситуации.\n3. Заполните документы по договору и подтверждающим материалам объекта.\n4. Проверьте реквизиты, расчёты, полномочия и подписи до направления документов.\n\nВопросы: marzhavbetone@yandex.ru\n\nНа стороне подрядчика\n'
   (d/'00-PISMO-POSLE-POKUPKI.txt').write_text(letter)
   labels=LABELS[sku].split('|');assert len(labels)==len(new),(sku,len(labels),len(new))
   inventory='\n'.join(f'<article class="doc-item"><h3>{escape(label)}</h3><p><code style="overflow-wrap:anywhere">{escape(n)}</code></p></article>' for n,label in zip(sorted(new),labels))
   rub=f'{price:,}'.replace(',',' ')
   main_html=f'''<main class="product-landing product-landing--{sku}">
    <section class="section"><nav aria-label="Хлебные крошки" class="breadcrumbs"><a href="../index.html">Главная</a> · <a href="../katalog.html">Каталог</a></nav>
    <p class="eyebrow">{sku.upper()} / {len(new)} файлов, включая инструкции</p><h1>{escape(title)}</h1><p class="lead">{escape(lead)}</p>
    <div class="price-block"><span class="price">{rub} ₽</span><button class="button add-to-cart large" type="button" data-product="{escape(title,quote=True)}" data-sku="{sku}" data-price="{price*100}">Добавить в корзину</button></div></section>
    <section class="section"><h2>Результат</h2><p>{escape(result)}</p><h2>Порядок действий</h2><ol>{''.join('<li>'+escape(s)+'</li>' for s in steps)}</ol></section>
    <section class="section"><h2>Состав комплекта</h2><p>{len(new)} файлов в одном архиве. Полный перечень:</p><div class="document-list">{inventory}</div></section>
    <section class="section"><h2>Контроль перед подписанием и отправкой</h2><p>Сопоставьте документы с договором, проектом и фактическими обстоятельствами объекта. Проверьте реквизиты, объёмы, суммы, даты, полномочия подписантов и перечень приложений. Сохраните подтверждения направления и получения.</p>
    {'<p>Унифицированные формы включены в опубликованном исходном виде. Их текст, графы, реквизиты и подписные строки сохранены; пояснения и рабочие реестры находятся в отдельных файлах.</p>' if sku in {'p1','p2','p4'} else ''}</section>
    <section class="section faq"><h2>Получение и применение</h2><div class="faq-list"><details><summary>Как получить комплект?</summary><p>После подтверждения оплаты ссылка придёт на указанный email. Ссылка действует 1 час: скачайте и сохраните архив. Если письмо не поступило, обратитесь на <a href="mailto:marzhavbetone@yandex.ru">marzhavbetone@yandex.ru</a>.</p></details><details><summary>С чего начать?</summary><p>Откройте <strong>{start}</strong> и выберите порядок действий по вашей ситуации. Формы Word и рабочие таблицы Excel заполняются по документам объекта; исходные бланки и материалы PDF применяются в соответствии с инструкцией.</p></details><details><summary>На скольких объектах можно применять?</summary><p>Лицензия действует для одной компании и не ограничивает количество её объектов. Передача комплекта другим компаниям не предусмотрена.</p></details></div></section>
    </main>'''
   pagepath=R/'products'/page;s=pagepath.read_text();s=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:main_html,s,flags=re.S)
   description=f'{lead} {len(new)} файлов. Цена {rub} ₽.'
   s=re.sub(r'<title>.*?</title>',lambda _:f'<title>{escape(title)} — {rub} ₽</title>',s,flags=re.S)
   for key,val in [('name="description"',description),('property="og:title"',title),('property="og:description"',description)]:
    s=re.sub(r'(<meta\s+'+key+r'\s+content=")[^"]*(")',lambda m:m[1]+escape(val,quote=True)+m[2],s)
   schema={'@context':'https://schema.org','@type':'Product','name':title,'description':description,'offers':{'@type':'Offer','url':'https://marzhavbetone.ru/products/'+page,'price':str(price),'priceCurrency':'RUB','availability':'https://schema.org/InStock'}}
   s=re.sub(r'<script type="application/ld\+json">.*?</script>',lambda _: '<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script>',s,flags=re.S);put(pagepath,s)
  packages.append(entry)
 # Update only commerce elements for affected SKUs. Retired steps point to their accepted parent.
 retired={'t1':'p1','t4':'p9','t5':'p8'}
 for path in list(R.glob('*.html'))+list((R/'articles').glob('*.html'))+list((R/'materialy').glob('*.html'))+list((R/'products').glob('*.html')):
  s=path.read_text();original_text=s
  def button(m):
   tag=m[0];v=re.search(r'data-sku="([^"]+)"',tag)
   if not v:return tag
   sku=retired.get(v[1],v[1])
   if sku not in DATA:return tag
   title,price,*_=DATA[sku]
   tag=re.sub(r'data-sku="[^"]+"','data-sku="'+sku+'"',tag)
   tag=re.sub(r'data-product="[^"]*"',lambda _: 'data-product="'+escape(title,quote=True)+'"',tag)
   tag=re.sub(r'data-price="[^"]*"','data-price="'+str(price*100)+'"',tag)
   return tag
  # Associated visible price belongs to the same price container; do not replace other SKUs.
  pattern=r'<(?:div|article)\b[^>]*class="[^"]*(?:price-block|product-footer|cta-price|product-buy)[^"]*"[^>]*>.*?</(?:div|article)>'
  def pricebox(m):
   t=m[0];skus=re.findall(r'data-sku="([^"]+)"',t)
   if len(set(skus))!=1:return t
   sku=retired.get(skus[0],skus[0])
   if sku not in DATA:return t
   rub=f'{DATA[sku][1]:,}'.replace(',',' ')
   return re.sub(r'\d[\d \u00a0\u202f]*\s*₽',lambda _:rub+' ₽',t)
  s=re.sub(pattern,pricebox,s,flags=re.S)
  s=re.sub(r'<button\b[^>]*>',button,s)
  if path.name=='katalog.html':
   def card(m):
    t=m[0];v=re.search(r'data-sku="([^"]+)"',t)
    if not v:return t
    sku=v[1]
    if sku not in DATA:return t
    title,price,page,lead,result,steps=DATA[sku];count=next(p['count'] for p in packages if p['sku']==sku)
    # One canonical card per retained product; the old entry steps are removed below.
    return f'<article class="product-card"><div class="product-number">{sku.upper()}</div><h3><a href="products/{page}">{escape(title)}</a></h3><p>{escape(lead)}</p><p>{count} файлов, включая инструкции.</p><div class="product-footer"><strong>{price:,} ₽</strong><button class="button add-to-cart" type="button" data-product="{escape(title,quote=True)}" data-sku="{sku}" data-price="{price*100}">Добавить в корзину</button></div></article>'.replace(f'{price:,}',f'{price:,}'.replace(',',' '))
   # Identify original step cards before replacing their converted buttons.
   origcards=re.findall(r'<article class="product-card">.*?</article>',original_text,flags=re.S)
   for cardold in origcards:
    v=re.search(r'data-sku="([^"]+)"',cardold)
    if v and v[1] in retired:
     converted=re.sub(pattern,pricebox,cardold,flags=re.S);converted=re.sub(r'<button\b[^>]*>',button,converted);s=s.replace(converted,'')
   s=re.sub(r'<article class="product-card">.*?</article>',card,s,flags=re.S)
  if s!=original_text:put(path,s)
 # P3: only replace the stale AOSR preview; unrelated accepted content stays intact.
 p3=R/'products/p3-shablony-ks2-ks3.html';s=p3.read_text()
 s=re.sub(r'<article class="preview-item">\s*<p class="preview-file">03-akt-skrytyh-rabot\.docx</p>.*?</article>', '<article class="preview-item"><p class="preview-file">03-akt-skrytyh-rabot.pdf</p><h3>Акт освидетельствования скрытых работ</h3><p>Полная опубликованная форма приложения № 3 к приказу Минстроя России № 344/пр. Текст, реквизиты, графы и подписи сохранены. Порядок применения указан в инструкции.</p></article>',s,flags=re.S);put(p3,s)
 config=R/'products-config.php';s=config.read_text()
 for sku,(title,price,*_) in DATA.items():
  pattern=r"('"+sku+r"'\s*=>\s*\[\s*'name'\s*=>\s*)'[^']*'(,\s*'price'\s*=>\s*)\d+"
  s,n=re.subn(pattern,lambda m:m[1]+repr(title)+m[2]+str(price*100),s);assert n==1,(sku,n)
 for sku in retired:
  anchor="    if ($sku === 't6') return null;"
  s=s.replace(anchor,"    if ($sku === '"+sku+"') return null;\n"+anchor)
  anchor="        if ($key === 't6') continue;"
  s=s.replace(anchor,"        if ($key === '"+sku+"') continue;\n"+anchor)
 anchor='    $body .= "Что делать дальше:\\n";'
 starts={p['sku']:('00-START-HERE.pdf' if p['sku'] in {'p10','p13'} else '00-INSTRUKCIYA.pdf' if p['sku'] in {'p1','p2','p7'} else '00-START-HERE.txt') for p in packages if p['sku']!='p3'}
 block='    // Exact accepted entry file for each remaining product.\n    $acceptedStarts = '+str(starts).replace('{','[').replace('}',']').replace(':',' =>')+';\n'
 block+='    if (count($links) === 1 && isset($acceptedStarts[$links[0]["sku"] ?? ""])) {\n        $body .= "Порядок действий:\\n1. Распакуйте архив и откройте " . $acceptedStarts[$links[0]["sku"]] . ".\\n2. Выберите порядок действий по вашей ситуации.\\n3. Заполните документы по договору и материалам объекта.\\n4. Проверьте реквизиты, расчёты, полномочия и подписи перед направлением.\\n\\nВопросы: " . ADMIN_EMAIL . "\\n\\nНа стороне подрядчика\\n";\n        return $body;\n    }\n'
 assert s.count(anchor)==1;s=s.replace(anchor,block+anchor);put(config,s)
 plan={'status':'OWNER_ACCEPTED_RELEASE_PREPARED','owner_approval':'owner-acceptance.json','approved_outer_zip_sha256':APPROVED,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'packages':packages,'retired_sales':retired,'protected_catalog':{k:v for k,v in before_catalog.items() if k not in DATA and k not in retired},'site_files':[{'file':n,'before_sha256':original[n],'sha256':sha((R/n).read_bytes())} for n in sorted(changed)],'production':'NOT_YET_PUBLISHED'}
 (O/'release-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'site_files':len(changed),'products':len(packages),'files':sum(p['count'] for p in packages),'retired':retired},ensure_ascii=False))
if __name__=='__main__':main()
