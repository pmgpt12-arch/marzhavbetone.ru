from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from PIL import Image,ImageChops
import json,hashlib,subprocess,shutil,ast,xml.etree.ElementTree as X,tarfile,re
P=Path(__file__).resolve().parent;D=P/'checkpoint';assert not D.exists();D.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(D/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
for n in ['candidates','proof','rendered-docx','rendered-xlsx','scripts','deferred-office-jobs']:(D/n).mkdir()
sources=[{'file':f.name,'sha256':sha(f),'bytes':f.stat().st_size}for f in sorted((P/'source').iterdir())if f.is_file()]
assert len(sources)==5;write('SOURCE_MEMBERS.json',sources)
for f in (P/'output').iterdir():
 if f.suffix in ['.docx','.xlsx']:shutil.copy2(f,D/'candidates'/f.name)
shutil.copy2(P/'source/99-chto-dalshe.pdf',D/'candidates/99-chto-dalshe.pdf')
assert len(list((D/'candidates').iterdir()))==5
for name in ['build_docs.py','build_workbook.mjs','finalize_workbook.py','render_xlsx.py','prepare_lo_cases.mjs','verify_lo_cases.py','prepare_checkpoint.py']:shutil.copy2(P/name,D/'scripts'/name)
for f in (P/'proof').glob('*.json'):shutil.copy2(f,D/'proof'/f.name)
shutil.copytree(P/'rejected-layout-v1',D/'rejected-layout-v1')
for name in ['lo-inputs','lo-recalculated']:shutil.copytree(P/'proof'/name,D/'proof'/name)
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
cases=json.loads((P/'proof/XLSX_CASES.json').read_text())['cases'];lo=[]
for i,c in enumerate(cases,1):
 f=P/'proof/lo-recalculated'/(str(i).zfill(2)+'-'+c['name']+'.xlsx')
 if not f.exists():lo.append({'case':c['name'],'status':'NO_OUTPUT_BEFORE_120S_EXPORT_TIMEOUT','expected':c['expected']});continue
 with ZipFile(f)as z:
  ss=E.fromstring(z.read('xl/sharedStrings.xml'));strings=[''.join(si.itertext())for si in ss];root=E.fromstring(z.read('xl/worksheets/sheet1.xml'));actual=[]
  for row in range(12,17):
   e=root.find('.//m:c[@r="D'+str(row)+'"]',NS);v=e.find('m:v',NS);actual.append(strings[int(v.text)]if e.get('t')=='s'else(v.text if e.get('t')=='str'else float(v.text)))
 lo.append({'case':c['name'],'status':'PASS_LIBREOFFICE_RECALC'if actual==c['expected']else'UNRESOLVED_ENGINE_TYPE_DIFFERENCE','actual':actual,'expected':c['expected']})
assert sum(r['status']=='PASS_LIBREOFFICE_RECALC'for r in lo)==10
write('proof/XLSX_SECOND_ENGINE.json',{'status':'PARTIAL_NOT_ACCEPTED','cases':lo,'confirmed_scenarios':10,'confirmed_checks':50,'boolean_observation':'Input XML D4 has t=b and v=1. LibreOffice XLSX output writes TRUE() with numeric cached value and D14=1. Do not change the workbook expectation to numeric 1. Native Excel check required.','date_observation':'No output for D2=-1 with date number format before 120-second export timeout. Stage/cause not established.','source_sha256':sha(P/'output/02-reestr-izyatiy-po-obektu.xlsx')})
pixel=[]
def imageproof(src,dest):
 im=Image.open(src);dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest,format='WEBP',lossless=True,method=6)
 restored=Image.open(dest).convert('RGBA');assert ImageChops.difference(im.convert('RGBA'),restored).getbbox()is None
 pixel.append({'source':str(src.relative_to(P)),'source_png_sha256':sha(src),'stored':str(dest.relative_to(D)),'stored_sha256':sha(dest),'pixels_identical':True,'size':list(im.size)})
docrows=[];allpages=0
for f in sorted((D/'candidates').glob('*.docx')):
 rd=P/'rendered-v2'/f.stem;target=D/'rendered-docx'/f.stem;target.mkdir()
 pdf=next(rd.glob('*.pdf'));shutil.copy2(pdf,target/pdf.name)
 pages=sorted(rd.glob('page-*.png'));expected={'01':5,'03':4,'04':3}[f.name[:2]];assert len(pages)==expected;allpages+=len(pages)
 for png in pages:imageproof(png,target/(png.stem+'.webp'))
 with ZipFile(f)as z:
  assert z.testzip()is None;styles=E.fromstring(z.read('word/styles.xml'));title=styles.find('.//w:style[@w:styleId="Title"]',NS);assert title is not None and not title.findall('.//w:pBdr',NS)
  root=E.fromstring(z.read('word/document.xml'));assert not root.xpath('//w:t[contains(text(),"🔗")]',namespaces=NS)
 links=subprocess.check_output(['pdfinfo','-url',str(pdf)],text=True)
 assert 'nastoronepodryadchika.ru/products/p8-avans-po-dogovoru-subpodryada.html'in links
 assert 'consultant.ru/document/'in links
 if f.name.startswith('04'):
  first=subprocess.check_output(['pdftotext','-f','1','-l','1',str(pdf),'-'],text=True);assert '[подпись]'in first and 'Как подготовить и отправить запрос'not in first
 docrows.append({'file':f.name,'sha256':sha(f),'canonical_renderer':'render_docx.py','pages_viewed':expected,'pdf_sha256':sha(pdf),'visual':'PASS_ALL_PAGES_V2','native_word':'PENDING','pdf_links':links})
assert allpages==12;write('DOCX_REVIEW.json',docrows)
pdf=P/'rendered-xlsx/02-reestr-izyatiy-po-obektu.pdf';shutil.copy2(pdf,D/'rendered-xlsx'/pdf.name)
for png in (P/'rendered-xlsx').glob('page-*.png'):imageproof(png,D/'rendered-xlsx'/(png.stem+'.webp'))
assert len(list((D/'rendered-xlsx').glob('page-*.webp')))==2
for name in ['before-Изъятия.png','before-Как считать.png','after-register.png','after-guide.png','source99-1.png']:imageproof(P/'proof'/name,D/'proof'/(Path(name).stem+'.webp'))
write('PIXEL_PRESERVATION.json',pixel)
# Freeze native inputs without sending them to a channel that failed its last runtime control.
jid='nsp-avans-xlsx-v1-20261023';j=X.Element('job',id=jid,qa_only='true',scope='Separate cash categories; 12 scenario and 60 expected-value checks; native Excel required')
f=X.SubElement(j,'file',name='02-reestr-izyatiy-po-obektu.xlsx',tag='av1',sheet='Изъятия',sha256=sha(D/'candidates/02-reestr-izyatiy-po-obektu.xlsx'),export_source_first='true',print_preflight='true')
for c in cases:
 ce=X.SubElement(f,'case',name=c['name'])
 for addr in ['D2']+['D'+str(i)for i in range(4,12)]:X.SubElement(ce,'set',cell=addr,kind='blank',value='')
 for addr,v in c['inputs'].items():
  kind='blank'if v is None else('boolean'if isinstance(v,bool)else('number'if isinstance(v,(int,float))else'text'))
  value=''if v is None else(str(v).lower()if isinstance(v,bool)else str(v));X.SubElement(ce,'set',cell=addr,kind=kind,value=value)
 for row,v in enumerate(c['expected'],12):X.SubElement(ce,'expect',cell='D'+str(row),kind='number'if isinstance(v,(int,float))else'text',value=str(v))
dest=D/'deferred-office-jobs'/jid;dest.mkdir();shutil.copy2(D/'candidates'/f.get('name'),dest/f.get('name'));X.ElementTree(j).write(dest/'job.xml',encoding='utf-8',xml_declaration=True)
jid='nsp-avans-docx-v2-20261023';j=X.Element('job',id=jid,qa_only='true')
dest=D/'deferred-office-jobs'/jid;dest.mkdir()
for i,f in enumerate(sorted((D/'candidates').glob('*.docx')),1):shutil.copy2(f,dest/f.name);X.SubElement(j,'file',name=f.name,tag='avd'+str(i),sha256=sha(f))
X.ElementTree(j).write(dest/'job.xml',encoding='utf-8',xml_declaration=True)
# Complete five-member QA package; source 99 PDF is exact.
with ZipFile(D/'avans-QA-candidate.zip','w',ZIP_DEFLATED)as z:
 for f in sorted((D/'candidates').iterdir()):z.write(f,f.name)
members=[]
with ZipFile(D/'avans-QA-candidate.zip')as z:
 assert z.testzip()is None and len(z.namelist())==5
 for n in z.namelist():
  b=z.read(n);assert hashlib.sha256(b).hexdigest()==sha(D/'candidates'/n);members.append({'file':n,'sha256':hashlib.sha256(b).hexdigest()})
assert sha(D/'candidates/99-chto-dalshe.pdf')==sha(P/'source/99-chto-dalshe.pdf')
write('PACKAGE_GATE.json',{'status':'QA_CANDIDATE_NOT_NATIVE_ACCEPTED','zip_sha256':sha(D/'avans-QA-candidate.zip'),'members':members,'changed_members':sorted(f.name for f in (D/'candidates').iterdir()if f.name!='99-chto-dalshe.pdf'),'source_99_pdf':'EXACT_UNCHANGED_VISUAL_PASS_1_PAGE','artifact_engine':{'scenarios':12,'checks':60,'status':'PASS'},'libreoffice_numeric':{'scenarios_pass':10,'checks_pass':50,'boolean':'UNRESOLVED_DIFFERENCE','invalid_date':'EXPORT_TIMEOUT_NOT_ACCEPTED'},'libreoffice_print':'PASS_2_PAGES_A3_REGISTER_A4_GUIDE','word_canonical_render':'PASS_12_PAGES','native_excel':'PENDING_RUNTIME_RECOVERY_AND_EXACT_SHA_CHECK','native_word':'PENDING_RUNTIME_RECOVERY_AND_EXACT_SHA_CHECK','native_jobs_submitted':False,'production_or_public_changes':False})
laws={}
for st in ast.parse((P/'build_docs.py').read_text()).body:
 if isinstance(st,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='LAWS'for t in st.targets):laws=ast.literal_eval(st.value)
write('LEGAL_SOURCES.json',{'checked_on':'2026-10-23 Asia/Krasnoyarsk','articles':[{'article':'ГК РФ '+k,'scope':v[0],'url':v[1],'read':'Full current article via browser retrieval'}for k,v in laws.items()],'limits':'Rules are conditional on contract and facts; no conclusion about an actual contract or guarantee.'})
(D/'EXECUTION_ERROR_LEDGER.md').write_text('# Ошибки и правила проверки\n\n1. Исходная модель складывала остаток аванса, денежные остатки, расходы и непринятые работы. Первопричина — не определён измеряемый показатель. Правило: складывать только совместимые и непересекающиеся суммы; разные показатели показывать отдельно. Gate: аванс без удержаний даёт 0 удержанных денег; непринятые работы с удержанием не превращаются в удвоенную сумму. Двенадцать сценариев и 60 проверок Artifact Tool пройдены.\n\n2. Наследованный Title содержал синюю границу в paragraph style, а не в самом абзаце. Удалена граница стиля, проверен XML Title и все 12 страниц повторного render_docx.py. Первая редакция сохранена как отклонённая по оформлению.\n\n3. GitHub Fetch отклонил бинарный ZIP как не-UTF-8. Перенос исходных файлов выполнен через DC с побайтовой сверкой SHA; публичный сайт не использовался как источник новой редакции.\n\n4. Команда libreoffice отсутствовала в PATH. Использован установленный runtime-wrapper soffice, который применяет штатный renderer. Новые пакеты и приложения не устанавливались. Печать XLSX проверена в PDF на обеих страницах.\n\n5. Второй движок: десять сценариев дали 50 совпавших значений. Логическое TRUE оказалось числом 1 в итоговом показателе, несмотря на входной XML t=b; ожидаемое значение не изменялось. Последний случай с отрицательной датой не получил экспортированный XLSX до лимита 120 секунд. Причина этапа экспорта не установлена. Правило: проверять типы тестовых входов и различать расчётный дефект, несовместимость движков и сбой экспорта. Gate остаётся закрытым до независимой проверки в Excel, а не заменяется PASS по кешу. Исходники и результаты этих опытов сохранены. Автоматического повторного запуска после таймаута не было.\n\n6. Сигнал ONLINE и свежие GET подтверждают связь с агентом; они не доказывают создание COM-приложения. После последнего отказа контрольного Word/Excel новый продуктовый пакет в очередь не отправлялся. Ожидается новое наблюдение восстановления приложений или диагностика их процессов.\n')
(D/'README.md').write_text('# Исправление бесплатного комплекта Аванс\n\nПодготовлены отдельные кандидаты четырёх файлов и полный QA ZIP из пяти вложений. Публичная выдача, канонические мастера и ранее принятые файлы не менялись.\n\nВ реестре устранена сумма разнородных величин под названием «денег объекта не у вас». Теперь отдельно показаны удержанные и заблокированные деньги, затраты, остаток аванса, непринятые работы и иные списания. Пустое поле отличается от подтверждённого нуля; отрицательные и нечисловые суммы не дают корректного итога. Контроль повторов оснований требует сверки документов в графе G и не объявлен автоматическим.\n\nВ трёх DOCX согласованы инструкции с новой моделью. Уточнены условия приостановки, смысл независимой гарантии и зачёта, риск работ без подписи. Добавлены проверенные ссылки на конкретные статьи ГК РФ и действующие контакты проекта. Письмо с подписью помещается на первой странице, пояснения для команды идут отдельно. Все 12 страниц канонического render_docx.py просмотрены.\n\nОсновной расчётный прогон: Artifact Tool — 12 сценариев, 60 проверок PASS. Печать LibreOffice — один A3 реестра и один A4 инструкции, обе страницы просмотрены. Дополнительный пересчёт LibreOffice: 10 сценариев / 50 проверок подтверждены; логическое значение даёт несовпадение, случай некорректной даты завершился без экспортированного файла по таймауту. Эти два случая НЕ приняты, расхождение не скрыто изменением ожидаемых значений.\n\nЭто QA_CANDIDATE_NOT_NATIVE_ACCEPTED. Подготовлены два замороженных задания с точными SHA, но они не отправлены: последний минимальный контроль Office дал COM 0x80080005 у Excel и TIMEOUT у Word. Свежая сеть не заменяет подтверждения запуска приложений. Следующий нативный прогон должен подтвердить конкретные SHA и спорные типы входа, затем требуется просмотр нативных PDF. Оригинальный 99 PDF с ценой и ссылками сохранён точно; его страница просмотрена.\n\nФайлы рендеров сохранены без потери пикселей в WebP; соответствие каждому просмотренному PNG подтверждено в PIXEL_PRESERVATION.json. Исходные PDF и параметры renderer доступны для воспроизведения. Общая проверка P5/P9/P11 и остальных материалов остаётся открытой.\n')
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}']
for p in D.rglob('*'):
 if p.is_file():assert not any(re.search(s,p.read_bytes())for s in patterns),p
inventory=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(D.rglob('*'))if p.is_file()]
write('ARTIFACTS_SHA256.json',inventory)
archive=P/'avans-checkpoint.tar.gz'
with tarfile.open(archive,'w:gz')as t:
 for p in sorted(D.rglob('*')):
  if p.is_file():t.add(p,arcname=str(p.relative_to(D)),recursive=False)
print(json.dumps({'checkpoint':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'files':len(inventory)+1},ensure_ascii=False))
