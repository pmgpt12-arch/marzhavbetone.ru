from pathlib import Path
import json,hashlib,re,shutil,subprocess,sys,time
from html import escape
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024');import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa20-p9-20261030/publication');B=D/'snapshot';T=D/'current-only';assert not T.exists();(T/'pages/products').mkdir(parents=True)
O=Path('/home/denis/projects/nsp-qa18-p7-20261030')
r=json.loads((D/'SNAPSHOT_REQUEST.json').read_text());P=r['prefix'];SHA=r['archive_sha256'];H=lambda b:hashlib.sha256(b).hexdigest();pagepath=r['page'];m=json.loads((D/P/'REVIEW_MANIFEST.json').read_text());members=m['files'];assert len(members)==12
snap=json.loads((B/'p9-production-snapshot.json').read_text());shutil.copyfile(D/'current.zip',T/'current.zip')
name=m['title'];oldname='Система защиты требований подрядчика при банкротстве генподрядчика'
lead='Проверьте сроки предъявления требований, рассчитайте задолженность и подготовьте заявление в реестр кредиторов. Алгоритм действий, примеры расчёта, реестр документов и редактируемые документы для суда.'
page=(B/pagepath).read_text();assert oldname in page
page=page.replace(oldname,name)
# Existing hero lead has the same structural position across product pages.
from lxml import html
doc=html.fromstring(page)
print('PAGE',pagepath,'NAME',name,flush=True)
print('LEADS',[(x.tag,x.attrib,x.text_content()[:220])for x in doc.xpath('//main//p')[:6]],flush=True)
# Target the existing lead class, preserving all layout and CTA.
match=re.search(r'<p class="lead">.*?</p>',page,re.S);assert match,'Missing lead'
oldlead=match.group(0);page=page[:match.start()]+'<p class="lead">'+lead+'</p>'+page[match.end():]
start=page.index('<div class="document-list">');end=page.index('</div></section>',start)
titles=['Единая инструкция по работе с комплектом','Словарь полей','Алгоритм при банкротстве генподрядчика','Маркеры риска до банкротства','Реестр документов и контроль дат','Проверка комплекта доказательств','Уведомление арбитражному управляющему','Запрос управляющему о расчётах','Заявление о включении в реестр','Действия при пропуске срока','Ручной расчёт долга с примером','Ходатайство о восстановлении срока']
listing='<div class="document-list">'+''.join('<article class="doc-item"><h3>'+escape(title)+'</h3><p><code style="overflow-wrap:anywhere">'+escape(row['name'])+'</code></p></article>\n'for title,row in zip(titles,members))
page=page[:start]+listing+page[end:]
page=page.replace('10 файлов, включая инструкции','12 файлов: 10 Word, 1 Excel и 1 PDF').replace('10 файлов','12 файлов').replace('00-START-HERE.txt','00-INSTRUKCIYA.pdf')
start=page.index('<section class="section"><h2>Результат</h2>');end=page.index('</section>',start)+len('</section>')
body='<section class="section"><h2>Что вы подготовите</h2><p>Расчёт состава требования без повторного учёта одних и тех же работ, комплект подтверждающих документов и заявление в реестр кредиторов.</p><h2>Как работать с комплектом</h2><ol><li>Установите процедуру банкротства, публикацию и применимый срок. Внесите проверенные даты в реестр.</li><li>Разделите основной долг, текущие платежи, спорные суммы и санкции. Выполните ручной расчёт по карточкам и примеру, сверив оплаты и зачёт аванса.</li><li>Соберите доказательства и подготовьте заявление. При пропуске срока проверьте доступный порядок действий и основания для ходатайства.</li></ol><h2>Границы применения</h2><p>Комплект предназначен для денежных требований к обычному юридическому лицу в банкротстве. Особые категории требований требуют отдельной проверки.</p><p>Расчёт задолженности заполняется вручную. Excel помогает вести документы и контролировать введённые даты; юридический срок определяется по применимым нормам. Ходатайство о восстановлении срока предназначено для конкурсного производства по статье 142; решение принимает суд.</p><p>Начальная инструкция одна — PDF. Комплект помогает подготовить документы и не гарантирует включение требования или получение денег.</p></section>'
page=page[:start]+body+page[end:];assert '00-START-HERE.txt'not in page
(T/'pages'/pagepath).write_text(page)
cat=(B/'katalog.html').read_text();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if 'data-sku="p9"'in x];assert len(cards)==1;card=cards[0];new=card.replace(oldname,name);new=new.replace('10 файлов, включая инструкции','12 файлов: 10 Word, 1 Excel и 1 PDF').replace('10 файлов','12 файлов')
# Replace the card description only; retain price and links.
new=re.sub(r'(<p class="product-desc">).*?(</p>)',lambda q:q[1]+lead+q[2],new,flags=re.S)
assert new!=card;cat=cat.replace(card,new,1);assert cat.replace(new,card,1)==(B/'katalog.html').read_text();(T/'pages/katalog.html').write_text(cat)
config=(B/'products-config.php').read_text();a="if ($sku === 'p2' || $sku === 'p3' || $sku === 'p4' || $sku === 'p5' || $sku === 'p7') {";assert config.count(a)==1;config=config.replace(a,a.replace("'p7')","'p7' || $sku === 'p9')"),1)
anchor="            'p7' => ['99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24', '/P7-v2-current.zip'],";assert config.count(anchor)==1;config=config.replace(anchor,anchor+"\n            'p9' => ['"+SHA+"', '/P9-v1-current.zip'],",1);assert config.count(oldname)==1;config=config.replace(oldname,name,1);(T/'pages/products-config.php').write_text(config)
manifest={'sku':'p9','edition':'P9-review-v1','archive_sha256':SHA,'members':members,'old_members':{x['name']:x['sha256']for x in snap['product_locations'][0]['p9_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in [pagepath,'katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':r['commit']};(T/'release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
def adapt(s):
 return s.replace('99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24',SHA).replace('p7-dogovor-podryada',Path(pagepath).stem).replace('03-dogovor-podryada','11-bankrotstvo-genpodryadchika').replace('P7','P9').replace('p7','p9').replace('v2-current','v1-current').replace('review-v2','review-v1').replace('REVIEW_V2','REVIEW_V1').replace('!==13','!==12').replace('=>13','=>12').replace('==13','==12').replace(':13',':12').replace("'files':13","'files':12").replace('nsp-qa18-p9','nsp-qa20-p9')
(T/'publish.php').write_text(adapt((O/'publication/current-only/publish.php').read_text()))
op=adapt((O/'publication/operate.py').read_text()).replace('8dfde54d57b9a5416e367cd4c189c73cb787acb9','2f8727dcb11d3760e5b92a09b70b474419c85f40').replace('tools/nsp-qa20-p9-20261030/review-v1/P9_Dogovor_v_interesah_ispolnitelya_v2.zip','tools/nsp-qa20-p9-20261030/review-v1/output/P9_Genpodryadchik_bankrotitsya_v1.zip')
(D/'operate.py').write_text(op)
test=adapt((O/'test_publication.py').read_text())
needle=" shutil.copytree(T/'pages',stage/'pages');";assert needle in test
test=test.replace(needle," shutil.copyfile('/home/denis/projects/nsp-qa18-p7-20261030/publication/current-only/current.zip',root/'P7-v2-current.zip')\n"+needle)
needle="('p5','1a0ab501a008c9cae1b1baaaa6570d1123291630ac8ecff1db74fad411431286')";test=test.replace(needle,needle+",('p7','99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24')")
(D.parent/'test_publication.py').write_text(test)
subprocess.run(['python3',str(D.parent/'test_publication.py')],check=True,timeout=90)
print('P9_BUILD_AND_LOCAL_CHECKS_PASS',flush=True)
