from pathlib import Path
import json,base64,hashlib,re,shutil,subprocess,zipfile
D=Path('/home/denis/projects/nsp-qa15-p3-20261030/publication');B=D/'snapshot';T=D/'current-only';assert not T.exists()
H=lambda b:hashlib.sha256(b).hexdigest();SHA='54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b'
request=json.loads((D/'SNAPSHOT_REQUEST.json').read_text());PREFIX=request['prefix'];pagepath=request['page']
snap=json.loads((B/'p3-production-snapshot.json').read_text())
for n,row in snap['files'].items():
 b=base64.b64decode(row['base64']);assert H(b)==row['sha256'];out=B/n;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
review=json.loads((D/PREFIX/'REVIEW_MANIFEST.json').read_text());assert review['archive']['sha256']==SHA
members=review['files'];assert len(members)==11
assert H((D/'current.zip').read_bytes())==SHA
T.mkdir();(T/'pages/products').mkdir(parents=True);shutil.copyfile(D/'current.zip',T/'current.zip')
page=(B/pagepath).read_text()
page=page.replace('10 документов и инструкция','11 файлов: 7 DOCX, 2 XLSX и 2 PDF').replace('10 ДОКУМЕНТОВ + ИНСТРУКЦИЯ','11 ФАЙЛОВ / ОДНА PDF-ИНСТРУКЦИЯ').replace('10 шаблонов в Word и Excel','7 файлов Word, 2 таблицы Excel и 2 PDF')
page=page.replace('10 рабочих документов в Word, Excel и PDF плюс инструкция; полный перечень — в разделе «Что входит» выше.','11 файлов: 7 DOCX, 2 XLSX и 2 PDF. Начните с 00-INSTRUKCIYA.pdf; полный перечень — в разделе «Что входит» выше.')
page=page.replace('шаблоны, реестр сверки объёмов, алгоритм самопроверки и типовые ответы на замечания.','проверочный лист, реестр приложений, журнал передачи, алгоритм самопроверки и форма ответа на замечания.')
patt=r'<div class="document-list">.*?</div>'
old=re.findall(patt,page,re.S);assert len(old)==1
purposes={'00-INSTRUKCIYA.pdf':('PDF-инструкция','Начало работы, состав и применение документов.'),'01-proverochnyy-list-komplekta-ks.docx':('Проверочный лист комплекта КС','40 пунктов проверки КС-2, КС-3 и приложений.'),'02-reestr-prilozheniy.xlsx':('Реестр приложений','Полный перечень документов и контроль реквизитов.'),'03-akt-skrytyh-rabot.docx':('Редактируемый акт скрытых работ','Рабочая форма для применимых скрытых работ. Реквизиты и состав участников сверяйте с требованиями объекта.'),'04-protokol-vnutrenney-proverki.docx':('Протокол внутренней проверки','Замечания, ответственные, сроки и повторная проверка.'),'05-pismo-o-nedostatkah.docx':('Ответ на замечания','Позиция по замечаниям и состав повторной передачи.'),'06-zhurnal-peredachi.xlsx':('Журнал передачи','Отправка, получение, срок ответа, возврат и повторная передача.'),'07-sroki-hraneniya.docx':('Хранение документов','Классификация документов и применимые основания хранения.'),'08-algoritm-proverki.pdf':('Алгоритм проверки и передачи','Последовательность работы с файлами комплекта.'),'09-tipovye-oshibki.docx':('Типовые ошибки','15 ситуаций и адресные способы исправления.'),'10-sravnitelnaya-tablica.docx':('Состав и рабочие результаты','Инструменты комплекта и проверяемые результаты.')}
assert set(purposes)=={r['name']for r in members}
from html import escape
listing='<div class="document-list">\n'+''.join('<article class="doc-item"><h3>'+escape(title)+'</h3><p><code style="overflow-wrap:anywhere">'+name+'</code></p><p>'+escape(desc)+'</p></article>\n'for name,(title,desc)in purposes.items())+'</div>'
page=page.replace(old[0],listing,1)
page=page.replace('Первые строки самих файлов комплекта — заголовок документа и строка, которой он себя объясняет. Не описание для витрины: текст читается из файлов при сборке страницы. Здесь 3 документа из 7; тело шаблонов, формулировки требований и расчёты открываются после покупки.','Фрагменты трёх документов из комплекта. Полные редактируемые формы, таблицы и инструкция доступны после покупки.')
page=page.replace('03-akt-skrytyh-rabot.pdf','03-akt-skrytyh-rabot.docx')
page=page.replace('Полная опубликованная форма приложения № 3 к приказу Минстроя России № 344/пр. Текст, реквизиты, графы и подписи сохранены. Порядок применения указан в инструкции.','Редактируемая рабочая форма. Её состав отличается от рекомендуемого образца по приказу № 344/пр; порядок проверки реквизитов и применимости указан в PDF-инструкции.')
page=page.replace('ПАМЯТКА ПО ОПРЕДЕЛЕНИЮ СРОКОВ ХРАНЕНИЯ ДОКУМЕНТОВ КОМПЛЕКТА КС','Определение сроков хранения документов комплекта КС')
page=page.replace('Основные причины: неправильное заполнение граф, отсутствие подписей, несоответствие объёма договору. Этот комплект содержит подсказки по каждой графе и алгоритм проверки, чтобы КС-2 прошла с первого раза.','Проверочный лист содержит 40 пунктов по договору, КС-2, КС-3, приложениям и передаче. Реестры и протокол помогают зафиксировать состав документов, закрыть замечания и подтвердить получение комплекта заказчиком.')
page=page.replace('Плановый срок автоматической доставки — до 5 минут.','Ссылка действует один час: скачайте и сохраните архив.').replace('Плановый срок автоматической выдачи — до пяти минут, ждать ответа человека не нужно.','Ссылка действует один час: скачайте и сохраните архив.')
# Correct breadcrumbs to the actual catalog while preserving page design.
page=page.replace('href="../index.html#catalog"','href="../katalog.html"').replace('"item": "https://nastoronepodryadchika.ru/#catalog"','"item": "https://nastoronepodryadchika.ru/katalog.html"')
assert len(re.findall(r'<code[^>]*>([^<]+)</code>',page))==11
assert '03-akt-skrytyh-rabot.pdf'not in page and '3 документа из 7'not in page
(T/'pages'/pagepath).write_text(page)
catalog=(B/'katalog.html').read_text()
cards=[a for a in re.findall(r'<article\b[^>]*>.*?</article>',catalog,re.S)if 'data-sku="p3"'in a];assert len(cards)==1
newcard=cards[0].replace('10 документов и инструкция.','11 файлов: 7 DOCX, 2 XLSX и 2 PDF. Одна PDF-инструкция.').replace('<li>Акт скрытых работ</li>','<li>Редактируемый акт скрытых работ</li>')
assert newcard!=cards[0];catalog=catalog.replace(cards[0],newcard,1)
# Change only P3 JSON-LD product record, if it contains the old composition.
for tag in re.findall(r'<script type="application/ld\\+json">(.*?)</script>',catalog,re.S):json.loads(tag)
old_desc='Шаблоны, реестры, алгоритм проверки и типовые замечания для подготовки КС-2 без возврата. 10 документов и инструкция.'
if old_desc in catalog:catalog=catalog.replace(old_desc,old_desc.replace('10 документов и инструкция.','11 файлов: 7 DOCX, 2 XLSX и 2 PDF.'),1)
assert catalog.replace(newcard,cards[0],1).replace(old_desc.replace('10 документов и инструкция.','11 файлов: 7 DOCX, 2 XLSX и 2 PDF.'),old_desc,1)==(B/'katalog.html').read_text()
(T/'pages/katalog.html').write_text(catalog)
config=(B/'products-config.php').read_text()
a="""    if ($sku === 'p2') {
        $approved = '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da';
        $master = PRODUCTS_DIR . '/P2-v13-current.zip';"""
b="""    if ($sku === 'p2' || $sku === 'p3') {
        $approved = $sku === 'p2'
            ? '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'
            : 'SHA';
        $master = PRODUCTS_DIR . ($sku === 'p2' ? '/P2-v13-current.zip' : '/P3-v1-current.zip');""".replace('SHA',SHA)
assert config.count(a)==1;config=config.replace(a,b,1)
(T/'pages/products-config.php').write_text(config)
m={'sku':'p3','edition':'P3-layout-v1','archive_sha256':SHA,'members':members,'old_members':{r['name']:r['sha256']for r in snap['product_locations'][0]['p3_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in [pagepath,'katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':request['commit']}
(T/'release.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
php=Path('/home/denis/projects/nsp-qa13-20261024/p1-publication-20261030/current-only/publish.php').read_text()
php=php.replace('99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada',SHA).replace('p1-oplata-po-ks2','p3-shablony-ks2-ks3').replace('P1','P3').replace('p1','p3').replace('01-zakrytie-rabot','05-ks-bez-vozvrata').replace('01-ks-podpisany-deneg-net.zip','05-ks-bez-vozvrata.zip').replace('2990000','1790000').replace('!==18','!==11').replace('=>18','=>11')
php=php.replace("$cache=$delivery.'/p3-'.$sha.'.zip';","$cache=$delivery.'/'.$p['zip'];")
start=php.index("    $edition=mvb_capture_p3_edition();")
end=php.index("    $built=mvb_build_product_zip('p3');",start)
php=php[:start]+php[end:]
anchor="if($mode==='preflight'){"
php=php.replace(anchor,anchor+"\n    if(file_exists($master))throw new RuntimeException('MASTER_ALREADY_PRESENT');",1)
(T/'publish.php').write_text(php)
for p in [T/'publish.php',T/'pages/products-config.php']:subprocess.run(['php','-l',str(p)],check=True,capture_output=True,timeout=8)
for tag in re.findall(r'<script type="application/ld\+json">(.*?)</script>',page,re.S):json.loads(tag)
assert len(m['members'])==11
print(json.dumps({'status':'P3_RELEASE_PREPARED','page':pagepath,'members':11,'old_members':len(m['old_members']),'manifest_sha256':H((T/'release.json').read_bytes())},indent=2))
