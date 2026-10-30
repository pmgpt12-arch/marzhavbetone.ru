from pathlib import Path
import json,hashlib,re,shutil,subprocess
from html import escape
D=Path('/home/denis/projects/nsp-qa17-p5-20261030/publication');B=D/'snapshot';T=D/'current-only';assert not T.exists();T.mkdir();(T/'pages/products').mkdir(parents=True)
old=Path('/home/denis/projects/nsp-qa16-p4-20261030/publication');r=json.loads((D/'SNAPSHOT_REQUEST.json').read_text());P=r['prefix'];SHA=r['archive_sha256'];H=lambda b:hashlib.sha256(b).hexdigest();pagepath=r['page'];m=json.loads((D/P/'REVIEW_MANIFEST.json').read_text());members=m['files'];assert len(members)==30
snap=json.loads((B/'p5-production-snapshot.json').read_text());shutil.copyfile(D/'current.zip',T/'current.zip')
page=(B/pagepath).read_text();start=page.index('      <div class="document-list">');end=page.index('      <div class="kit-preview">',start)
titles=['Начните здесь: PDF-инструкция','Претензия на возврат удержания','Претензия на штраф','Возражение на зачёт','Расчёт убытков','Реестр удержаний','График возмещения','Алгоритм проверки удержаний','Типовые основания','Подготовка к консультации','Требование о возврате удержания','Словарь полей','Алгоритм проверки претензий','Соглашение о разграничении ответственности','Мотивированный ответ на претензию','Возражение на односторонний акт','Предупреждение по статье 716 ГК РФ','Ответ на гарантийную претензию','Акт передачи фронта работ','Акт входного контроля материалов','Возражение на зачёт и удержание','Регламент комиссионной фиксации','Реестр гарантийных удержаний','Реестр исполнительной документации','Кто кому отвечает','Ответ на прямое требование заказчика','Заявление об участии в осмотре','Разбор заключения экспертизы','Вопросы эксперту и проект ходатайства','Опись доказательств по дефекту']
listing='      <div class="document-list">\n'+''.join('<article class="doc-item"><h3>'+escape(title)+'</h3><p><code style="overflow-wrap:anywhere">'+escape(row['name'])+'</code></p></article>\n'for title,row in zip(titles,members))+'      </div>\n\n'
page=page[:start]+listing+page[end:];page=page.replace('11 готовых файлов.','30 файлов: 22 DOCX, 6 XLSX и 2 PDF. Одна начальная PDF-инструкция.').replace('30 файлов: претензии, расчёты, алгоритмы','30 файлов: 22 DOCX, 6 XLSX и 2 PDF').replace('Здесь 3 документа из 22;','Здесь 3 документа из 30;');assert '11 готовых файлов'not in page
(T/'pages'/pagepath).write_text(page)
cat=(B/'katalog.html').read_text();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if 'data-sku="p5"'in x];assert len(cards)==1
card=cards[0];new=card.replace('30 файлов','30 файлов: 22 DOCX, 6 XLSX и 2 PDF');assert new!=card;cat=cat.replace(card,new,1);assert cat.replace(new,card,1)==(B/'katalog.html').read_text();(T/'pages/katalog.html').write_text(cat)
config=(B/'products-config.php').read_text();a="if ($sku === 'p2' || $sku === 'p3' || $sku === 'p4') {";assert config.count(a)==1;config=config.replace(a,a.replace("'p4')","'p4' || $sku === 'p5')"),1)
anchor="            'p4' => ['a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea', '/P4-v1-current.zip'],";assert config.count(anchor)==1;config=config.replace(anchor,anchor+"\n            'p5' => ['"+SHA+"', '/P5-v1-current.zip'],",1);(T/'pages/products-config.php').write_text(config)
manifest={'sku':'p5','edition':'P5-layout-v1','archive_sha256':SHA,'members':members,'old_members':{x['name']:x['sha256']for x in snap['product_locations'][0]['p5_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in [pagepath,'katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':r['commit']};(T/'release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
def adapt(s):return s.replace('a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea',SHA).replace('p4-ispolnitelnaya-dokumentaciya-pto','p5-shtrafy-uderzhaniya').replace('08-pto-bez-zamechaniy','07-uderzhaniya-shtrafy-zachety').replace('P4','P5').replace('p4','p5').replace('2490000','2990000').replace('!==26','!==30').replace('=>26','=>30')
(T/'publish.php').write_text(adapt((old/'current-only/publish.php').read_text()))
op=adapt((old/'operate.py').read_text()).replace('869e1f56edc349fc62f69f6a52ac0cc72287a78e','e0a8f10fe5fa94c55a25c0a170b0ab3ed5a613c0').replace('tools/nsp-qa16-p5-20261030/P5_PTO_bez_zamechaniy_v1.zip','tools/nsp-qa17-p5-20261030/P5_Uderzhaniya_shtrafy_zachety_v1.zip').replace('==26','==30').replace(':26',':30');assert 'qa16'not in op;(D/'operate.py').write_text(op)
test=adapt((old.parent/'test_publication.py').read_text()).replace('nsp-qa16-p5','nsp-qa17-p5').replace("'files':26","'files':30")
needle=" shutil.copytree(T/'pages',stage/'pages');";assert needle in test
test=test.replace(needle," shutil.copyfile('/home/denis/projects/nsp-qa16-p4-20261030/publication/current-only/current.zip',root/'P4-v1-current.zip')\n"+needle)
needle="('p3','54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b')"
test=test.replace(needle,needle+",('p4','a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea')")
(D.parent/'test_publication.py').write_text(test)
for p in [T/'publish.php',T/'pages/products-config.php']:subprocess.run(['php','-l',str(p)],check=True,capture_output=True,timeout=8)
subprocess.run(['python3',str(D.parent/'test_publication.py')],check=True,timeout=90)
print('P5 release built and tested')
