from pathlib import Path
import sys,json,hashlib,re,subprocess,time,shutil,os,datetime
from html import escape
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
import prepare_p1_publication_20261030 as c
HOME=Path('/home/denis/projects/nsp-publish-p10-p11-20261031')
OLD=Path('/home/denis/projects/nsp-qa20-p9-20261030')
OLD_SHA='34bf03bcd3ed2e31d731dd8ac4c316cf9f94a8bb5dde1e4c9fc1aa3a7b7b23d9'
CF={
'p10':{'root':'/home/denis/projects/nsp-qa21-p10-20261031','sha':'90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594','qa':'qa/nsp-qa21-p10-20261031','review':'8335d9e7d241d9ccdcc75db7d134cbed703600a6','reviewprefix':'tools/nsp-qa21-p10-20261031/review-v1','archive':'P10_Pretenziya_k_podryadchiku_v1.zip','dir':'15-otvet-na-pretenziyu-baza','price':1790000,'oldname':'Система подготовки ответа на претензию заказчика','previous':'p9','qaindex':'qa21','composition':'10 файлов: 9 Word и 1 PDF','lead':'Проверьте основания и сумму претензии, подготовьте контррасчёт и мотивированный ответ. Алгоритм действий, редактируемые формы и три заполненных случая с перечнями доказательств.','titles':['Единая PDF-инструкция','Карта претензии и доказательств','Алгоритм проверки и ответа','Ответ стороне договора','Ответ на гарантийную претензию','Ответ на прямое требование','Уведомление контрагенту','Формулировки возражений','Ручной контррасчёт с примером','Три заполненных случая ответа'],'result':'Позицию по каждому требованию, контррасчёт, комплект подтверждающих документов и ответ с учётом выбранной ситуации.','steps':['Зарегистрируйте претензию и проверьте применимый срок.','Сопоставьте основания и документы, проверьте сумму по ручной расчётной форме.','Выберите форму ответа, изложите позицию по каждому требованию и сохраните подтверждение направления.'],'scope':'Для досудебной переписки по строительному подряду и субподряду между организациями и ИП. Примеры охватывают неустойку, гарантийный дефект и прямое требование к субподрядчику.','limits':'Расчёт заполняется вручную. Срок ответа, гарантийный режим и последствия частичного признания проверяются по конкретным обстоятельствам. Комплект не гарантирует отказа от претензии и не заменяет судебное сопровождение.'},
'p11':{'root':'/home/denis/projects/nsp-qa22-p11-20261031','sha':'ff6cf9a7056cab90ee1203a93ddb964e0308b8bd418394f4ebd672a9b8b860da','qa':'qa/nsp-qa22-p11-20261031','review':'dc98d1ac87b1f32383ba531b7e706eb8034c933a','reviewprefix':'tools/nsp-qa22-p11-20261031/review-v1','archive':'P11_Raschety_obektami_nedvizhimosti_v1.zip','dir':'13-raschet-metrami','price':2490000,'oldname':'Расчёты в неденежной форме: жилые и офисные помещения, машино-места','previous':'p10','qaindex':'qa22','composition':'10 файлов: 7 Word и 3 PDF','lead':'Проверьте права на объект, дополнительные обязательства и выгоду расчёта недвижимостью. Свяжите передачу имущества или права с погашением конкретного долга за работы.','titles':['Единая PDF-инструкция','Поля и показатели расчёта','Алгоритм проверки трёх вариантов сделки','Чек-лист и ручной расчёт','Запрос строительного статуса','Запрос оплаты ДДУ и условий уступки','Памятка об уступке и эскроу','Первый день до подписания','Карточка сделки и сравнение с деньгами','Три сквозных случая и заполненные запросы'],'result':'Карточку сторон и обязательств, расчёт дополнительных денег подрядчика и ожидаемого поступления, условия погашения долга и перечень нерешённых вопросов до подписания.','steps':['Выберите вариант: готовая недвижимость, новый ДДУ или уступка существующего права.','Проверьте документы, плательщика и дополнительные обязательства; направьте запросы по применимости.','Сравните ту же сумму долга с ожидаемым поступлением после расходов и зафиксируйте условия сделки в карточке.'],'scope':'Основные случаи относятся к квартирам, нежилым помещениям и машино-местам. Для земли, зданий, долей и специальных режимов нужны дополнительные проверки.','limits':'Формы расчёта заполняются вручную. Цена ДДУ, цена уступки и долг за работы проверяются раздельно. Регистрация ДДУ сама по себе не подтверждает погашение долга. Банкротство застройщика требует отдельного специального маршрута.'}
}
sku=sys.argv[1];phase=sys.argv[2];cfg=CF[sku];UP=sku.upper();D=Path(cfg['root'])/'publication';D.mkdir(exist_ok=True);P='tools/nsp-publication-20261026/'+sku+'-v1-20261031';SHA=cfg['sha'];H=lambda b:hashlib.sha256(b).hexdigest()
def jread(p):return json.loads(p.read_text())
def jwrite(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def adapt(s):
 return s.replace(str(OLD),cfg['root']).replace(OLD_SHA,SHA).replace('products/p9-bankrotstvo-genpodryadchika.html',jread(D/'SNAPSHOT_REQUEST.json')['page']).replace('11-bankrotstvo-genpodryadchika',cfg['dir']).replace('2490000',str(cfg['price'])).replace('P9',UP).replace('p9',sku).replace('!==12','!==10').replace('=>12','=>10').replace('==12','==10').replace(':12',':10')
def collect(request,kind):
 started=time.monotonic();run=None
 while time.monotonic()-started<240:
  xs=[x for x in c.api('GET','actions/workflows/nsp-cutover-final.yml/runs?per_page=12')['workflow_runs']if x['head_sha']==request['commit']]
  if xs:
   run=xs[0]
   if run['status']=='completed':break
  time.sleep(8)
 else:raise RuntimeError('Existing workflow still pending; inspect before resuming')
 out=D/('snapshot-artifact'if kind=='snapshot'else'live-evidence');out.mkdir(exist_ok=True)
 subprocess.run(['gh','run','download',str(run['id']),'-R','pmgpt12-arch/marzhavbetone.ru','-n','nsp-final-evidence-'+str(run['id']),'-D',str(out)],check=True,timeout=60)
 if run['conclusion']!='success':
  log=subprocess.run(['gh','run','view',str(run['id']),'-R','pmgpt12-arch/marzhavbetone.ru','--log-failed'],capture_output=True,timeout=40).stdout.decode();print(log[-12000:],flush=True);raise RuntimeError('Workflow failed; inspect existing evidence, no automatic retry')
 return run,out
if phase=='prepare':
 assert not(D/'SNAPSHOT_REQUEST.json').exists()
 archive=Path(cfg['root'])/'review-v1/output'/cfg['archive'];assert H(archive.read_bytes())==SHA;shutil.copyfile(archive,D/'current.zip')
 base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];w=c.fetch('.github/workflows/nsp-cutover-final.yml',base).decode();assert sku+'-snapshot'not in w
 prev=cfg['previous'];a='"'+prev+'-publish"]';assert w.count(a)==1;w=w.replace(a,'"'+prev+'-publish","'+sku+'-snapshot","'+sku+'-publish"]',1)
 a='|| "$action" == '+prev+'-publish ]]; fi';assert w.count(a)==1;w=w.replace(a,'|| "$action" == '+prev+'-publish || "$action" == '+sku+'-snapshot || "$action" == '+sku+'-publish ]]; fi',1)
 marker='      - name: Approved P4 targeted publication';assert w.count(marker)==1;w=w.replace(marker,"      - name: Approved "+UP+" targeted publication\n        if: startsWith(env.NSP_ACTION, '"+sku+"-') && github.ref_name == '"+c.BR+"'\n        run: python3 "+P+"/operate.py \"$NSP_ACTION\"\n"+marker,1)
 cat=c.fetch('katalog.html',base).decode();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if'data-sku="'+sku+'"'in x];assert len(cards)==1;page=re.search(r'href="(products/[^"]+)"',cards[0])[1]
 # Save route before adapting the established transaction code.
 jwrite(D/'ROUTE.json',{'page':page})
 ins=(OLD/'publication/tools/nsp-publication-20261026/p9-v1-20261030/inspect.php').read_text().replace('products/p9-bankrotstvo-genpodryadchika.html',page).replace('NSP_P9','NSP_'+UP).replace('11-bankrotstvo-genpodryadchika',cfg['dir']).replace('p9_files',sku+'_files')
 op=(OLD/'publication/operate.py').read_text().split("assert request['delivery_policy']")[0].replace(OLD_SHA,SHA).replace('P9',UP).replace('p9',sku)
 approval={'sku':sku,'edition':UP+'-review-v1','owner_quote':'Согласовано публикуй','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':SHA,'file_count':10,'review_evidence_commit':cfg['review'],'approved_at_local_date':'2026-10-31','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY'}
 review=c.fetch(cfg['reviewprefix']+'/internal/REVIEW_MANIFEST.json',cfg['review']);m=json.loads(review);assert m['archive']['sha256']==SHA and m['file_count']==10
 req={**approval,'action':sku+'-snapshot','approved_archive_sha256':SHA,'request_id':UP+'-OWNER-APPROVED-SNAPSHOT-20261031'}
 files={'.github/workflows/nsp-cutover-final.yml':w.encode(),P+'/inspect.php':ins.encode(),P+'/operate.py':op.encode(),P+'/OWNER_APPROVAL.json':json.dumps(approval,ensure_ascii=False,indent=2).encode(),P+'/REVIEW_MANIFEST.json':review,'tools/nsp-final/request.json':json.dumps(req,ensure_ascii=False,indent=2).encode()}
 for n,b in files.items():
  f=D/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
 sha=c.commit(files,UP+': accept exact edition and snapshot production before publication [skip deploy]',base);r={'commit':sha,'base':base,'branch':c.BR,'prefix':P,'page':page,'archive_sha256':SHA};jwrite(D/'SNAPSHOT_REQUEST.json',r);print('SNAPSHOT_REQUESTED '+json.dumps(r),flush=True)
 run,out=collect(r,'snapshot');shutil.copytree(out/(sku+'-before'),D/'snapshot',dirs_exist_ok=True);shutil.copyfile(out/(sku+'-production-snapshot.json'),D/'snapshot'/(sku+'-production-snapshot.json'));print('SNAPSHOT_READY '+str(run['id']),flush=True)
elif phase=='build':
 r=jread(D/'SNAPSHOT_REQUEST.json');B=D/'snapshot';T=D/'current-only';assert not T.exists();(T/'pages/products').mkdir(parents=True);m=jread(D/P/'REVIEW_MANIFEST.json');members=m['files'];assert len(members)==10;pagepath=r['page'];name=m['title'];comp=cfg['composition'];lead=cfg['lead'];oldname=cfg['oldname']
 snap=jread(B/(sku+'-production-snapshot.json'));shutil.copyfile(D/'current.zip',T/'current.zip')
 page=(B/pagepath).read_text();assert oldname in page;page=page.replace(oldname,name)
 # Preserve public header/footer/assets; replace only outdated product body.
 price=f"{cfg['price']//100:,}".replace(',',' ')+' ₽';button='<div class="price-block"><span class="price">'+price+'</span><button class="button add-to-cart large" type="button" data-product="'+escape(name,quote=True)+'" data-sku="'+sku+'" data-price="'+str(cfg['price'])+'">Добавить в корзину</button></div>'
 hero=button
 if sku=='p11':hero='<div class="product-hero"><img src="../assets/raschet-metrami.jpg" alt="Расчёты объектами недвижимости" width="1376" height="768" loading="lazy" decoding="async"><div class="product-meta">'+button+'<ul class="product-features"><li>'+comp+'</li><li>Карточка сделки и ручной расчёт</li><li>Три сквозных случая и два заполненных запроса</li></ul></div></div>'
 main='<main class="product-landing product-landing--'+sku+'"><section class="section"><nav aria-label="Хлебные крошки" class="breadcrumbs"><a href="../index.html">Главная</a> · <a href="../katalog.html">Каталог</a></nav><p class="eyebrow">'+UP+' / '+comp+'</p><h1>'+escape(name)+'</h1><p class="lead">'+escape(lead)+'</p>'+hero+'</section>'
 main+='<section class="section"><h2>Что вы подготовите</h2><p>'+escape(cfg['result'])+'</p><h2>Как работать с комплектом</h2><ol>'+''.join('<li>'+escape(s)+'</li>'for s in cfg['steps'])+'</ol></section>'
 main+='<section class="section"><h2>Состав комплекта</h2><p>'+comp+'. Полный перечень:</p><div class="document-list">'+''.join('<article class="doc-item"><h3>'+escape(title)+'</h3><p><code style="overflow-wrap:anywhere">'+escape(row['name'])+'</code></p></article>\n'for title,row in zip(cfg['titles'],members))+'</div></section>'
 main+='<section class="section"><h2>Для каких ситуаций</h2><p>'+escape(cfg['scope'])+'</p><p>'+escape(cfg['limits'])+'</p><p>Начальная инструкция одна — PDF. Редактируемые документы заполняются по данным вашей ситуации.</p></section>'
 main+='<section class="section faq"><h2>Получение и применение</h2><div class="faq-list"><details><summary>Как получить комплект?</summary><p>После подтверждения оплаты ссылка придёт на указанный email. Для каждого оплаченного заказа ссылка действует 1 час с момента её формирования. Скачайте и сохраните архив; повторное открытие письма срок не продлевает.</p></details><details><summary>С чего начать?</summary><p>Откройте <strong>00-INSTRUKCIYA.pdf</strong> и выберите порядок действий по вашей ситуации. Формы Word редактируются, расчёты заполняются вручную.</p></details><details><summary>На скольких объектах можно применять?</summary><p>Лицензия действует для одной компании и не ограничивает количество её объектов. Передача комплекта другим компаниям не предусмотрена.</p></details></div><p>Если письмо не пришло или ссылка не открывается, напишите на <a href="mailto:nastoronepodryadchika@yandex.ru">nastoronepodryadchika@yandex.ru</a> — поможем получить файлы.</p></section></main>'
 assert page.count('<main ')==1 and page.count('</main>')==1;page=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:main,page,flags=re.S)
 # Replace actual metadata, not descriptions embedded in escaped Word XML.
 for key in ['name="description"','property="og:description"']:
  page=re.sub(r'(<meta '+re.escape(key)+r' content=")[^"]*(">)',lambda q:q[1]+escape(lead+' '+comp+'.',quote=True)+q[2],page)
 def ld(q):
  obj=json.loads(q[1])
  if obj.get('@type')=='Product':
   obj['name']=name;obj['description']=lead+' '+comp+'.'
   if 'offers'in obj:obj['offers']['availability']='https://schema.org/InStock'
  return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,indent=2)+'</script>'
 page=re.sub(r'<script type="application/ld\+json">(.*?)</script>',ld,page,flags=re.S)
 assert all(x not in page for x in ['00-START-HERE','В разработке','Оплата и скачивание пока недоступны','&lt;w:','&lt;/w:'])
 (T/'pages'/pagepath).write_text(page)
 cat=(B/'katalog.html').read_text();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if'data-sku="'+sku+'"'in x];assert len(cards)==1;card=cards[0];new=card.replace(oldname,name);counter=[0]
 def cp(q):
  counter[0]+=1;return '<p>'+escape(lead+' '+comp+'.')+'</p>'if counter[0]==1 else''
 new=re.sub(r'<p\b[^>]*>.*?</p>',cp,new,flags=re.S);assert new!=card and counter[0]>=1;cat=cat.replace(card,new,1);assert cat.replace(new,card,1)==(B/'katalog.html').read_text();(T/'pages/katalog.html').write_text(cat)
 config=(B/'products-config.php').read_text();a=next(x for x in config.splitlines()if "if ($sku === 'p2'"in x);assert sku not in a;config=config.replace(a,a.replace(') {'," || $sku === '"+sku+"') {"),1)
 prev=cfg['previous'];anchor=re.search(r"^            '"+prev+r"' => \['[a-f0-9]{64}', '/"+prev.upper()+r"-v1-current.zip'\],$",config,re.M);assert anchor;config=config[:anchor.end()]+"\n            '"+sku+"' => ['"+SHA+"', '/"+UP+"-v1-current.zip'],"+config[anchor.end():];assert config.count(oldname)==1;config=config.replace(oldname,name,1);(T/'pages/products-config.php').write_text(config)
 manifest={'sku':sku,'edition':UP+'-review-v1','archive_sha256':SHA,'members':members,'old_members':{x['name']:x['sha256']for x in snap['product_locations'][0][sku+'_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in [pagepath,'katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':r['commit']};jwrite(T/'release.json',manifest)
 (T/'publish.php').write_text(adapt((OLD/'publication/current-only/publish.php').read_text()))
 op=(OLD/'publication/operate.py').read_text().replace('2f8727dcb11d3760e5b92a09b70b474419c85f40',cfg['review']).replace('tools/nsp-qa20-p9-20261030/review-v1/output/P9_Genpodryadchik_bankrotitsya_v1.zip',cfg['reviewprefix']+'/output/'+cfg['archive']);(D/'operate.py').write_text(adapt(op))
 test=adapt((OLD/'test_publication.py').read_text());needle=" shutil.copytree(T/'pages',stage/'pages');";assert test.count(needle)==1
 extra=" shutil.copyfile('/home/denis/projects/nsp-qa20-p9-20261030/publication/current-only/current.zip',root/'P9-v1-current.zip')\n"
 prior=[('p9',OLD_SHA)]
 if sku=='p11':
  extra+=" shutil.copyfile('/home/denis/projects/nsp-qa21-p10-20261031/publication/current-only/current.zip',root/'P10-v1-current.zip')\n";prior.append(('p10',CF['p10']['sha']))
 test=test.replace(needle,extra+needle)
 needle="('p7','99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24')";assert test.count(needle)==1;test=test.replace(needle,needle+''.join(','+repr(x)for x in prior))
 (D/'test_publication.py').write_text(test)
 for f in [T/'publish.php',T/'pages/products-config.php']:subprocess.run(['php','-l',str(f)],check=True,capture_output=True,timeout=8)
 subprocess.run(['python3',str(D/'test_publication.py')],check=True,timeout=90)
 local=jread(T/'LOCAL_TEST_RECEIPT.json');assert local['check_count']==(20 if sku=='p10'else 21)
 # Stronger publication composition and metadata checks without touching product content.
 from lxml import html
 doc=html.fromstring(page)
 assert len(doc.xpath('//button[@data-sku="'+sku+'"]'))==1
 assert doc.xpath('//h1/text()')==[name]
 assert len(doc.xpath('//code'))==10
 assert doc.xpath('//button[@data-sku="'+sku+'"]/@data-price')==[str(cfg['price'])]
 assert all(json.loads(x.text)['offers']['availability']=='https://schema.org/InStock'for x in doc.xpath('//script[@type="application/ld+json"]')if json.loads(x.text).get('@type')=='Product')
 print(UP+'_BUILD_AND_CHECKS_PASS '+str(local['check_count']),flush=True)
elif phase=='publish':
 T=D/'current-only';r=jread(D/'SNAPSHOT_REQUEST.json');local=jread(T/'LOCAL_TEST_RECEIPT.json');assert local['check_count']==(20 if sku=='p10'else 21);assert not(D/'PUBLISH_REQUEST.json').exists()
 base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];assert base==r['commit'],'Branch drift after snapshot'
 req=json.loads(c.fetch('tools/nsp-final/request.json',base));assert req['action']==sku+'-snapshot'
 req.update(action=sku+'-publish',request_id=UP+'-OWNER-APPROVED-PUBLISH-20261031',method='EXACT_CURRENT_ARCHIVE_EXISTING_BUILDER',release_manifest_sha256=H((T/'release.json').read_bytes()))
 files={P+'/operate.py':(D/'operate.py').read_bytes(),'tools/nsp-final/request.json':json.dumps(req,ensure_ascii=False,indent=2).encode(),P+'/evidence/publication.py':Path(__file__).read_bytes(),P+'/evidence/test_publication.py':(D/'test_publication.py').read_bytes()}
 for n in ['publish.php','release.json','pages/'+r['page'],'pages/katalog.html','pages/products-config.php','LOCAL_TEST_RECEIPT.json']:files[P+'/current-only/'+n]=(T/n).read_bytes()
 sha=c.commit(files,'Publish accepted '+UP+': exact ten-file edition and one-hour current-only delivery [skip deploy]',base);request={'commit':sha,'base':base,'archive_sha256':SHA};jwrite(D/'PUBLISH_REQUEST.json',request);print('PUBLICATION_REQUESTED '+json.dumps(request),flush=True)
 run,E=collect(request,'publish');receipt=jread(E/(UP+'_PUBLICATION_RECEIPT.json'));assert receipt['archive_sha256']==SHA and receipt['file_count']==10;print('VERIFIED_LIVE '+json.dumps(receipt,ensure_ascii=False),flush=True)
elif phase=='save':
 E=D/'live-evidence';T=D/'current-only';r=jread(E/(UP+'_PUBLICATION_RECEIPT.json'));f=jread(E/(sku+'-finalize.json'));assert not(D/'FINAL_SAVE_RECEIPT.json').exists()
 assert r['status']==UP+'_REVIEW_V1_DEPLOYED_CURRENT_ARCHIVE_AND_HTTPS_VERIFIED'and r['archive_sha256']==SHA==H((E/(sku+'-current-delivered.zip')).read_bytes())
 assert r['file_count']==10 and r['ttl_seconds']==3600 and f['temporary_rollback_removed']and not r['old_product_files_retained']and not r['old_cache_retained']
 m=jread(D/P/'REVIEW_MANIFEST.json');approval=(D/P/'OWNER_APPROVAL.json').read_bytes();count=jread(T/'LOCAL_TEST_RECEIPT.json')['check_count']
 status={'sku':sku,'edition':UP+'-review-v1','status':'OWNER_ACCEPTED_AND_PUBLICATION_VERIFIED','product_title':m['title'],'archive_sha256':SHA,'file_count':10,'owner_quote':'Согласовано публикуй','workflow_url':'https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/'+r['run_id'],'source_publication_commit':r['commit'],'local_delivery_checks':str(count)+'/'+str(count)+' PASS','live_current_archive_exact_match':True,'public_pages_https':'2/2 PASS','ttl_seconds':3600,'old_source_and_cache_removed':True,'new_real_payment':False,'new_full_qa_pass_claimed':False,'published_local_date':'2026-10-31'}
 raw=json.dumps(status,ensure_ascii=False,indent=2).encode();files={P+'/CURRENT_STATUS.json':raw}
 for n in [UP+'_PUBLICATION_RECEIPT.json',sku+'-finalize.json',sku+'-https.json',sku+'-source-gate.json',sku+'-preflight.json',sku+'-apply.json']:files[P+'/live-evidence/'+n]=(E/n).read_bytes()
 pagepath=jread(D/'SNAPSHOT_REQUEST.json')['page']
 for n in [pagepath,'katalog.html','products-config.php']:files[n]=(T/'pages'/n).read_bytes()
 base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];assert base==r['commit'],'Branch moved after deploy'
 sha=c.commit(files,UP+': preserve verified publication receipt and released source [skip deploy]',base);assert c.fetch(P+'/live-evidence/'+UP+'_PUBLICATION_RECEIPT.json',sha)==(E/(UP+'_PUBLICATION_RECEIPT.json')).read_bytes()
 c.BR=cfg['qa'];qb=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];assert qb==cfg['review']
 qprefix=cfg['reviewprefix'].rsplit('/',1)[0];qsha=c.commit({qprefix+'/CURRENT_STATUS.json':raw,qprefix+'/OWNER_APPROVAL.json':approval,qprefix+'/'+UP+'_PUBLICATION_RECEIPT.json':(E/(UP+'_PUBLICATION_RECEIPT.json')).read_bytes()},UP+': exact edition accepted and published [skip deploy]',qb)
 S=Path('/home/denis/.local/share/ai-business-os/office-vm/STATE.json');before=S.read_bytes();state=json.loads(before);idx=cfg['qaindex'];assert state[idx+'_current_owner_review']['archive_sha256']==SHA
 (D/'STATE_BEFORE_LIVE_VERIFIED.json').write_bytes(before)
 live={**r,'status':'VERIFIED_LIVE','receipt_evidence_commit':sha,'receipt_evidence_path':P+'/live-evidence/'+UP+'_PUBLICATION_RECEIPT.json','qa_evidence_commit':qsha,'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 state[idx+'_live_publication']=live
 for k in ['_current_owner_review','_current_checkpoint']:state[idx+k].update(status='OWNER_ACCEPTED_AND_PUBLISHED',owner_approval='APPROVED',release_allowed=True,production_changed=True,owner_edition_approval_pending=False,superseded_by=idx+'_live_publication',next_action=UP+' publication complete')
 state[idx+'_current_accepted_edition']={'sku':sku,'edition':UP+'-review-v1','owner_acceptance':'APPROVED','archive_sha256':SHA,'file_count':10,'publication_status':'VERIFIED_LIVE','publication_receipt_commit':sha,'review_evidence_commit':cfg['review']}
 if 'title_owner_approval_pending'in state[idx+'_current_owner_review']:state[idx+'_current_owner_review']['title_owner_approval_pending']=False;state[idx+'_current_checkpoint']['title_owner_approval_pending']=False
 tmp=S.with_name('STATE.'+idx+'-publication.tmp');assert not tmp.exists();tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');assert S.read_bytes()==before;os.replace(tmp,S);check=jread(S);assert check[idx+'_live_publication']==live
 for k,v in json.loads(before).items():
  if not k.startswith(idx+'_'):assert check[k]==v
 receipt={'status':UP+'_LIVE_EVIDENCE_AND_EXISTING_STATE_READBACK_PASS','publication_evidence_commit':sha,'qa_evidence_commit':qsha,'archive_sha256':SHA,'run_id':r['run_id'],'page':pagepath,'state_sha256':H(S.read_bytes())};jwrite(D/'FINAL_SAVE_RECEIPT.json',receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)
else:raise ValueError('Unknown phase')
