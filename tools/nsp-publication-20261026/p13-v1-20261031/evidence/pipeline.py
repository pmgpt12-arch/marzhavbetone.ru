from pathlib import Path
import json,hashlib,subprocess,os,sys,re,zipfile,shutil
R=Path(__file__).resolve().parent.parent;D=R/'publication';REPO=R.parent/'qa23-p13-repo';P='tools/nsp-publication-20261026/p13-v1-20261031';BR='codex/nsp-publication-catalog-20261026';BASE='5bf5a84997eab07aeb606911f38a898ebc3188fe';PAGE='products/p13-chto-v-smete-ne-oplatyat.html';OLDPAGE='products/p11-raschet-metrami.html';OLD_DIR='13-raschet-metrami';DIR='16-chto-v-smete-ne-oplatyat';OLD_SHA='ff6cf9a7056cab90ee1203a93ddb964e0308b8bd418394f4ebd672a9b8b860da';SHA='0b1f777b9fb65952cd219d5e61e6b8500cdcd5f1c0039ceba80e3c8f6e67f955';H=lambda b:hashlib.sha256(b).hexdigest()
def jr(p):return json.loads(p.read_text())
def jw(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def git(args,data=None,env=None,timeout=30):
 p=subprocess.run(['git','-C',str(REPO),*args],input=data,capture_output=True,env=env,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.decode()[-1600:])
 return p.stdout
def commit(files,message,base,phase):
 request=D/(phase+'_REQUEST.json');assert not request.exists(),'Inspect existing request; do not retry'
 remote=git(['ls-remote','origin','refs/heads/'+BR],timeout=25).decode().split()[0];assert remote==base,('BRANCH_DRIFT',remote,base)
 idx=D/(phase+'.index');assert not idx.exists();env={**os.environ,'GIT_INDEX_FILE':str(idx),'GIT_AUTHOR_NAME':'Codex','GIT_AUTHOR_EMAIL':'codex@openai.com','GIT_COMMITTER_NAME':'Codex','GIT_COMMITTER_EMAIL':'codex@openai.com'}
 git(['read-tree',base],env=env)
 for path,data in files.items():
  sha=git(['hash-object','-w','--stdin'],data,env).decode().strip();git(['update-index','--add','--cacheinfo','100644,'+sha+','+path],env=env)
 tree=git(['write-tree'],env=env).decode().strip();sha=git(['commit-tree',tree,'-p',base],message.encode(),env).decode().strip()
 for path,data in files.items():assert git(['show',sha+':'+path])==data,path
 jw(request,{'commit':sha,'base':base,'phase':phase,'archive_sha256':SHA,'status':'COMMIT_CREATED_PUSH_PENDING','files':list(files)})
 print('COMMIT_READY '+json.dumps({'phase':phase,'commit':sha,'files':len(files)}),flush=True)
 transfer=[]
 for path,data in files.items():
  if path.endswith('.zip'):transfer.append({'path':path,'mode':'100644','type':'blob','sha':git(['hash-object','--stdin'],data).decode().strip()})
  else:transfer.append({'path':path,'mode':'100644','type':'blob','content':data.decode()})
 jw(D/(phase+'_TREE_TRANSFER.json'),transfer)
 print('READY_FOR_AUTHENTICATED_GITHUB_CONNECTOR '+phase,flush=True)
 return sha
def adapt(s):
 return s.replace(OLD_SHA,SHA).replace(OLDPAGE,PAGE).replace(OLD_DIR,DIR).replace('2490000','1790000').replace('P11','P13').replace('p11','p13').replace('!==10','!==12').replace('=>10','=>12').replace('==10','==12').replace(':10',':12')
phase=sys.argv[1]
if phase=='prepare':
 m=jr(R/'internal/REVIEW_MANIFEST.json');archive=R/'output'/m['archive']['name'];assert H(archive.read_bytes())==SHA and m['file_count']==12
 w=(D/'reference/workflow.yml').read_text();a='"p11-publish"]';assert w.count(a)==1;w=w.replace(a,'"p11-publish","p13-snapshot","p13-preflight","p13-publish"]')
 a='|| "$action" == p11-publish ]]; fi';assert w.count(a)==1;w=w.replace(a,'|| "$action" == p11-publish || "$action" == p13-snapshot || "$action" == p13-preflight || "$action" == p13-publish ]]; fi')
 marker='      - name: Approved P4 targeted publication';assert w.count(marker)==1;w=w.replace(marker,"      - name: Approved P13 targeted publication\n        if: startsWith(env.NSP_ACTION, 'p13-') && github.ref_name == '"+BR+"'\n        run: python3 "+P+"/operate.py \"$NSP_ACTION\"\n"+marker)
 ins=adapt((D/'reference/inspect.php').read_text());op=adapt((D/'reference/operate.py').read_text().split("assert request['delivery_policy']")[0])
 approval={'sku':'p13','edition':'P13-review-v1','owner_quote':'Ок публикуй','owner_product_acceptance':'APPROVED','release_permission':'ALLOW_EXACT_EDITION_ONLY','archive_sha256':SHA,'file_count':12,'approved_at_local_date':'2026-10-31','delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','title':m['title'],'github_publication_authorized_by_current_owner_instruction':True}
 req={**approval,'action':'p13-snapshot','approved_archive_sha256':SHA,'request_id':'P13-OWNER-APPROVED-SNAPSHOT-20261031'}
 files={'.github/workflows/nsp-cutover-final.yml':w.encode(),P+'/inspect.php':ins.encode(),P+'/operate.py':op.encode(),P+'/OWNER_APPROVAL.json':json.dumps(approval,ensure_ascii=False,indent=2).encode(),P+'/REVIEW_MANIFEST.json':(R/'internal/REVIEW_MANIFEST.json').read_bytes(),P+'/accepted/'+m['archive']['name']:archive.read_bytes(),'tools/nsp-final/request.json':json.dumps(req,ensure_ascii=False,indent=2).encode()}
 for n,b in files.items():p=D/'staged'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 compile(op,'operate.py','exec');commit(files,'P13 accepted: preserve exact archive and snapshot production [skip deploy]',BASE,'SNAPSHOT')
elif phase=='build':
 B=D/'snapshot';T=D/'current-only';assert not T.exists();(T/'pages/products').mkdir(parents=True);m=jr(R/'internal/REVIEW_MANIFEST.json');snap=jr(B/'p13-production-snapshot.json');name=m['title'];old='Система проверки сметной документации и выявления неоплачиваемых затрат';comp='12 файлов: 10 Word, 1 Excel и 1 PDF';lead='Найдите расходы, которые могут остаться за счёт подрядчика. Проверьте покрытие сметой, оцените влияние на плановую прибыль и подготовьте документы для согласования цены.'
 from html import escape
 page=(B/PAGE).read_text();assert old in page;page=page.replace(old,name)
 button='<div class="price-block"><span class="price">17 900 ₽</span><button class="button add-to-cart large" type="button" data-product="'+escape(name,quote=True)+'" data-sku="p13" data-price="1790000">Добавить в корзину</button></div>'
 main='<main class="product-landing product-landing--p13"><section class="section"><nav aria-label="Хлебные крошки" class="breadcrumbs"><a href="../index.html">Главная</a> · <a href="../katalog.html">Каталог</a></nav><p class="eyebrow">P13 / '+comp+'</p><h1>'+escape(name)+'</h1><p class="lead">'+lead+'</p>'+button+'</section>'
 main+='<section class="section"><h2>Что вы подготовите</h2><p>Перечень затрат с подтверждениями, расчёт непокрытого остатка и его доли в плановой прибыли, запрос с расчётом и проект согласования изменений сметы.</p><h2>Как работать с комплектом</h2><ol><li>Сопоставьте проект, смету, условия площадки и распределение обязанностей. Пройдите 62 вопроса проверочного листа.</li><li>Заполните 51 укрупнённую строку Excel: укажите покрытие, документы и непокрытую сумму. Принятый компанией риск остаётся в расчёте, неизвестная сумма не считается нулём.</li><li>Подготовьте запрос и согласуйте изменения цены. Обновите покрытие после надлежащего оформления решения.</li></ol></section>'
 titles=['Единая PDF-инструкция','Поля и порядок заполнения','Алгоритм проверки сметы','62 вопроса о затратах по объекту','Excel-реестр с проверкой покрытия','Запрос и приложение с расчётом','Протокол согласования изменений','Накладные расходы и сметная прибыль','Зимние затраты и временные объекты','Отходы, транспорт и резерв','Карта применимости норм и документов','Три случая и заполненный запрос']
 main+='<section class="section"><h2>Состав комплекта</h2><p>'+comp+'. Полный перечень:</p><div class="document-list">'+''.join('<article class="doc-item"><h3>'+escape(title)+'</h3><p><code style="overflow-wrap:anywhere">'+r['name']+'</code></p></article>\n'for title,r in zip(titles,m['files']))+'</div></section>'
 main+='<section class="section"><h2>Для каких ситуаций</h2><p>Основной маршрут — проверка и согласование коммерческой цены строительного подряда до подписания. Для уже заключённого договора отдельно проверяются вид цены, основание изменения и порядок уведомления.</p><p>Отсутствие отдельной строки не доказывает отсутствия покрытия: расход может быть учтён в ресурсе, расценке или начислении. Реестр показывает экономическую оценку и не устанавливает автоматически долг заказчика.</p><p>Комплект не выполняет автоматический подбор нормативов, профессиональную экспертизу всей сметы и расчёт налогов. Для регулируемых контрактов проверяется специальный порядок изменения цены. Расчёт охватывает фиксированные строки 2–52; произвольно добавленные строки автоматически не учитываются.</p></section>'
 main+='<section class="section faq"><h2>Получение и применение</h2><div class="faq-list"><details><summary>Как получить комплект?</summary><p>После подтверждения оплаты ссылка придёт на указанный email. Для каждого оплаченного заказа ссылка действует 1 час с момента её формирования. Скачайте и сохраните архив; повторное открытие письма срок не продлевает.</p></details><details><summary>С чего начать?</summary><p>Откройте <strong>00-INSTRUKCIYA.pdf</strong>, зафиксируйте редакции документов и выберите применимый порядок проверки. Word и Excel редактируются по данным вашего объекта.</p></details><details><summary>На скольких объектах можно применять?</summary><p>Лицензия действует для одной компании и не ограничивает количество её объектов. Передача комплекта другим компаниям не предусмотрена.</p></details></div><p>Если письмо не пришло или ссылка не открывается, напишите на <a href="mailto:nastoronepodryadchika@yandex.ru">nastoronepodryadchika@yandex.ru</a> — поможем получить файлы.</p></section></main>'
 assert page.count('<main ')==1;page=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:main,page,flags=re.S)
 for key in ['name="description"','property="og:description"']:page=re.sub(r'(<meta '+re.escape(key)+r' content=")[^"]*(">)',lambda q:q[1]+escape(lead+' '+comp+'.',quote=True)+q[2],page)
 def ld(q):
  obj=json.loads(q[1])
  if obj.get('@type')=='Product':obj.update(name=name,description=lead+' '+comp+'.',offers={'@type':'Offer','price':'17900','priceCurrency':'RUB','availability':'https://schema.org/InStock','url':'https://nastoronepodryadchika.ru/'+PAGE})
  return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False,indent=2)+'</script>'
 page=re.sub(r'<script type="application/ld\+json">(.*?)</script>',ld,page,flags=re.S);assert all(s not in page for s in ['00-START-HERE','В разработке','Оплата и скачивание пока недоступны'])
 (T/'pages'/PAGE).write_text(page)
 cat=(B/'katalog.html').read_text();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if'data-sku="p13"'in x];assert len(cards)==1;card=cards[0];new=card.replace(old,name);counter=[0]
 def cp(q):counter[0]+=1;return '<p>'+lead+' '+comp+'.</p>'if counter[0]==1 else''
 new=re.sub(r'<p\b[^>]*>.*?</p>',cp,new,flags=re.S);assert new!=card and counter[0]>=1;cat=cat.replace(card,new,1);assert cat.replace(new,card,1)==(B/'katalog.html').read_text();(T/'pages/katalog.html').write_text(cat)
 config=(B/'products-config.php').read_text();a=next(x for x in config.splitlines()if "if ($sku === 'p2'"in x);assert "'p13'"not in a;config=config.replace(a,a.replace(') {'," || $sku === 'p13') {"),1)
 anchor=re.search(r"^            'p11' => \['[a-f0-9]{64}', '/P11-v1-current.zip'\],$",config,re.M);assert anchor;config=config[:anchor.end()]+"\n            'p13' => ['"+SHA+"', '/P13-v1-current.zip'],"+config[anchor.end():];assert config.count(old)==1;config=config.replace(old,name,1);(T/'pages/products-config.php').write_text(config)
 manifest={'sku':'p13','edition':'P13-review-v1','archive_sha256':SHA,'members':m['files'],'old_members':{x['name']:x['sha256']for x in snap['product_locations'][0]['p13_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in [PAGE,'katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':jr(D/'SNAPSHOT_REQUEST.json')['commit']};jw(T/'release.json',manifest)
 shutil.copyfile(R/'output'/m['archive']['name'],T/'current.zip');(T/'publish.php').write_text(adapt((D/'reference/current-only/publish.php').read_text()))
 op=adapt((D/'reference/operate.py').read_text());op=op.replace("('p13-snapshot','p13-publish')","('p13-snapshot','p13-preflight','p13-publish')");op=op.replace("ref='dc98d1ac87b1f32383ba531b7e706eb8034c933a'","ref='"+jr(D/'SNAPSHOT_REQUEST.json')['commit']+"'").replace("source='tools/nsp-qa22-p13-20261031/review-v1/output/P13_Raschety_obektami_nedvizhimosti_v1.zip'","source='"+P+'/accepted/'+m['archive']['name']+"'")
 assert 'qa22-p13'not in op and 'Raschety_obektami'not in op
 marker="local=json.loads((C/'LOCAL_TEST_RECEIPT.json').read_text());";assert marker in op
 injected="\n# Isolated PHP delivery regression gate before production writes.\nimport shutil\n(C/'current.zip').write_bytes(archive)\nshutil.copytree(ROOT/'snapshot',ROOT/'test-snapshot',dirs_exist_ok=True)\ncall(['python3',str(ROOT/'test_publication.py')],timeout=100)\nshutil.copyfile(C/'LOCAL_TEST_RECEIPT.json',E/'P13_LOCAL_TEST_RECEIPT.json')\nif action=='p13-preflight':\n print((C/'LOCAL_TEST_RECEIPT.json').read_text());sys.exit(0)\n\n"
 op=op.replace(marker,injected+marker);compile(op,'operate.py','exec');(D/'operate.py').write_text(op)
 test=adapt((D/'reference/evidence/test_publication.py').read_text());test=test.replace("D=Path('/home/denis/projects/nsp-qa22-p13-20261031/publication')","D=Path(__file__).resolve().parent").replace("B=D/'snapshot'","B=D/'test-snapshot'")
 # Existing fixture copies are replaced with the exact previously published archives.
 test=re.sub(r" shutil.copyfile\('/home/denis/[^\n]+\n",'',test)
 needle=" shutil.copytree(T/'pages',stage/'pages');";assert test.count(needle)==1;test=test.replace(needle," for master in (D/'fixtures').glob('*.zip'):shutil.copyfile(master,root/master.name)\n"+needle)
 needle="('p10', '90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594')";assert needle in test;test=test.replace(needle,needle+",('p11', '"+OLD_SHA+"')")
 test=test.replace('from lxml import html','from html.parser import HTMLParser\nclass Parse(HTMLParser):\n def __init__(self):super().__init__();self.active=None;self.buf="";self.codes=[];self.scripts=[]\n def handle_starttag(self,tag,attrs):\n  if tag=="code"or(tag=="script"and dict(attrs).get("type")=="application/ld+json"):self.active=tag;self.buf=""\n def handle_data(self,data):\n  if self.active:self.buf+=data\n def handle_endtag(self,tag):\n  if tag==self.active:\n   (self.codes if tag=="code"else self.scripts).append(self.buf);self.active=None')
 oldblock=" doc=html.fromstring((T/'pages'/n).read_bytes())\n for scripttag in doc.xpath('//script[@type=\"application/ld+json\"]'):json.loads(scripttag.text)\n if n.startswith('products/'):assert set(doc.xpath('//code/text()'))=={r['name']for r in m['members']}"
 assert oldblock in test;test=test.replace(oldblock," doc=Parse();doc.feed((T/'pages'/n).read_text())\n for script in doc.scripts:json.loads(script)\n if n.startswith('products/'):assert set(doc.codes)=={r['name']for r in m['members']}")
 compile(test,'test_publication.py','exec');(D/'test_publication.py').write_text(test)
 fixtures={'P1-v1-current.zip':D/'fixtures/P1-v1-current.zip','P2-v13-current.zip':R.parent/'qa15-p3/p2.zip','P3-v1-current.zip':R.parent/'qa15-p3/output/P3_KS_bez_vozvrata_v1.zip','P4-v1-current.zip':R.parent/'qa16-p4/output/P4_PTO_bez_zamechaniy_v1.zip','P5-v1-current.zip':R.parent/'qa17-p5/output/P5_Uderzhaniya_shtrafy_zachety_v1.zip','P7-v2-current.zip':R.parent/'qa18-p7-v2/output/P7_Dogovor_v_interesah_ispolnitelya_v2.zip','P9-v1-current.zip':R.parent/'qa20-p9/output/P9_Genpodryadchik_bankrotitsya_v1.zip','P10-v1-current.zip':R.parent/'qa21-p10/output/P10_Pretenziya_k_podryadchiku_v1.zip','P11-v1-current.zip':R.parent/'qa22-p11/output/P11_Raschety_obektami_nedvizhimosti_v1.zip'}
 for n,p in fixtures.items():
  assert p.is_file()
  if p!=D/'fixtures'/n:shutil.copyfile(p,D/'fixtures'/n)
 from lxml import html
 doc=html.fromstring(page);assert len(doc.xpath('//code'))==12 and doc.xpath('//h1/text()')==[name]and doc.xpath('//button[@data-sku="p13"]/@data-price')==['1790000']
 print('P13_BUILD_SOURCE_HTML_PASS_12_FILES')
elif phase in ['preflight','publish']:
 snap=jr(D/'SNAPSHOT_REQUEST.json');base=snap['commit']if phase=='preflight'else jr(D/'PREFLIGHT_REQUEST.json')['commit'];T=D/'current-only';m=jr(R/'internal/REVIEW_MANIFEST.json')
 req=jr(D/'staged/tools/nsp-final/request.json');req.update(action='p13-'+phase,request_id='P13-OWNER-APPROVED-'+phase.upper()+'-20261031',method='EXACT_CURRENT_ARCHIVE_EXISTING_BUILDER',release_manifest_sha256=H((T/'release.json').read_bytes()))
 if phase=='publish':
  receipt=jr(D/'preflight-evidence/P13_LOCAL_TEST_RECEIPT.json');assert receipt['archive_sha256']==SHA and receipt['check_count']==23
 files={P+'/operate.py':(D/'operate.py').read_bytes(),P+'/test_publication.py':(D/'test_publication.py').read_bytes(),P+'/evidence/pipeline.py':Path(__file__).read_bytes(),'tools/nsp-final/request.json':json.dumps(req,ensure_ascii=False,indent=2).encode()}
 if phase=='preflight':
  for f in (D/'fixtures').glob('*.zip'):files[P+'/fixtures/'+f.name]=f.read_bytes()
  for f in (D/'snapshot').rglob('*'):
   if f.is_file():files[P+'/snapshot/'+str(f.relative_to(D/'snapshot'))]=f.read_bytes()
  for f in T.rglob('*'):
   if f.is_file()and f.name!='current.zip':files[P+'/current-only/'+str(f.relative_to(T))]=f.read_bytes()
 else:files[P+'/current-only/LOCAL_TEST_RECEIPT.json']=(D/'preflight-evidence/P13_LOCAL_TEST_RECEIPT.json').read_bytes()
 commit(files,'P13 '+phase+': exact accepted archive and one-hour delivery [skip deploy]',base,phase.upper())
else:raise ValueError(phase)
