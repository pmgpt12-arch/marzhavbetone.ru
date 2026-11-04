from pathlib import Path
import json,hashlib,shutil,subprocess,os,signal,xml.etree.ElementTree as E,re
from PIL import Image,ImageChops
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');A=Q/'avans-corrections-20261023';C=Q/'office-control-20261023-001210';S=Q/'office-resumed-products-20261023';R=Q.parent/'integration-20261022/repo'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((A/'NATIVE_RESULTS.json').read_text());assert len(rows)==2 and all(r['status']=='PASS'for r in rows)
native=next(r for r in rows if r['channel']=='native');word=next(r for r in rows if r['channel']=='word');assert len(native['checks'])==64 and len(word['files'])==3
reopen=next(r for r in json.loads((S/'RESULTS.json').read_text())if r['job']=='nsp-avans-reopen-v1-20261023');assert reopen['status']=='PASS'and len(reopen['checks'])==9
for row in rows:
 for f in row['files']:
  assert sha(A/'candidates'/f['file'])==f['source_sha256']
  f['visual_review']='PASS_ALL_NATIVE_PAGES'
review={'status':'FULL_FREE_QA_CANDIDATE_NATIVE_VERIFIED','native_excel_checks':64,'business_scenarios':12,'business_expected_values':60,'native_reopen_checks':9,'native_word_files':3,'native_word_pages_viewed':12,'native_excel_pages_viewed':2,'source_99_pdf_viewed_and_unchanged':True,'native_boolean_and_invalid_date_cases':'PASS_EXPECTED_TEXT_VALUES; cross-engine discrepancy retained as diagnostic history','print_area_builtin_name_recognition':'NOT_CLAIMED; complete used-range print fits actual two pages','public_switch':False,'canonical_changes':False}
(A/'POST_NATIVE_REVIEW.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
for old,new in [('PACKAGE_GATE.json','PRE_NATIVE_PACKAGE_GATE.json'),('README.md','README_BEFORE_NATIVE.md')]:assert not (A/new).exists();shutil.copy2(A/old,A/new)
g=json.loads((A/'PACKAGE_GATE.json').read_text());g.update(status=review['status'],native_excel='PASS_64_CHECKS_EXACT_SOURCE_SHA',native_excel_reopen='PASS_9_CHECKS',native_word='PASS_3_FILES_12_PAGES_VIEWED',native_print='PASS_2_PAGES_VIEWED',native_jobs_submitted=True,acceptance_limits='Excel2016 target confirmed. LibreOffice conversion differences remain recorded; no claim of independent native UI typing/paste or localized builtin-name repair.')
(A/'PACKAGE_GATE.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n')
(A/'NATIVE_RESULTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(A/'README.md').write_text('# Исправленный бесплатный комплект Аванс\n\nСтатус FULL_FREE_QA_CANDIDATE_NATIVE_VERIFIED. В архиве пять файлов, изменены четыре. SHA архива: '+g['zip_sha256']+'. Публичная выдача не переключалась.\n\nУстранена общая сумма разнородных величин. Пять показателей разделены: удержано и заблокировано, фактические затраты, остаток аванса, непринятые работы и прочие списания. Ввод различает пустое поле, подтверждённый ноль и ошибочную сумму. Три документа согласованы с новой моделью; исправлены категорические утверждения, добавлены конкретные нормативные ссылки и действующие контакты. Отправляемое письмо отделено от пояснений и помещается с подписью на первой странице.\n\nExcel2016: 12 сценариев / 60 ожидаемых значений плюс четыре проверки артефакта — всего 64 PASS. Нативная сохранённая копия повторно открыта: ещё 9 PASS. В том числе подтверждены ожидаемые результаты логического значения и отрицательной даты, не совпавшие или не завершившиеся в дополнительном экспорте LibreOffice. Модель не менялась для маскировки этих расхождений. Оба нативных листа печати просмотрены: A3 реестра и A4 инструкции. Это не утверждение о распознавании встроенных имён Print_Area: по телеметрии оно остаётся отдельной инфраструктурной темой.\n\nWord2016: три точных исходных SHA прошли открытие и экспорт, все 12 страниц просмотрены. Дополнительно пройден канонический render_docx.py с просмотром 12 страниц. Исходный 99 PDF сохранён побайтно и просмотрен; цена и ссылки не менялись.\n\nАрхив сверён по CRC, составу и SHA всех пяти вложений. Это полный QA-кандидат для утверждённого этапа проверки; канонические мастера, main, публичные ZIP, цены и платежи не изменялись. Ранее принятые 13 файлов, исходные 19 кандидатов, шесть удержанных оригиналов и прежние QA ZIP проверены отдельно. Общая приёмка P5/P9/P11 и оставшейся линейки открыта.\n')
shutil.copy2(Q/'scripts/run_avans_native.py',A/'scripts/run_avans_native.py')
shutil.copy2(Path(__file__),A/'scripts'/Path(__file__).name)
for f in word['files']:
 tag=next(e['tag']for e in word['file_receipts']if e['pdf_sha256']==f['pdf_sha256']);pdf=A/'evidence/word/nsp-avans-docx-v2-20261023'/(tag+'.pdf')
 links=subprocess.check_output(['pdfinfo','-url',str(pdf)],text=True);assert 'consultant.ru/document/'in links and 'nastoronepodryadchika.ru/products/p8-avans-po-dogovoru-subpodryada.html'in links
 if tag=='avd3':
  t=subprocess.check_output(['pdftotext','-f','1','-l','1',str(pdf),'-'],text=True);assert '[подпись]'in t and 'Как подготовить и отправить запрос'not in t
p=subprocess.run(['python3',str(Q/'scripts/verify_recovery_preservation_v2.py')],capture_output=True,text=True,timeout=30);assert p.returncode==0 and json.loads(p.stdout)['status']=='PASS';(A/'PRESERVATION_GATE.json').write_text(p.stdout)
def run(args,t=45):
 p=subprocess.Popen(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:a,b=p.communicate(timeout=t)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(args,a,b)
 return a
base='f69d1dca4df471aaa65c75a18d9be746f003bff9';assert run(['git','rev-parse','HEAD']).strip()==base
assert not run(['git','status','--short']).strip();assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(base)
rels=[]
for source,name in [(A,'avans-corrections-20261023'),(C,'office-recovery-20261023')]:
 rel='tools/nsp-next-corrections-20261022/'+name;D=R/rel;assert not D.exists();shutil.copytree(source,D,ignore=shutil.ignore_patterns('*.png'));rels.append(rel)
 imageproof=[]
 for png in source.rglob('*.png'):
  dst=D/png.relative_to(source);dst=dst.with_suffix('.webp');dst.parent.mkdir(parents=True,exist_ok=True);im=Image.open(png);im.save(dst,format='WEBP',lossless=True,method=6);assert ImageChops.difference(im.convert('RGBA'),Image.open(dst).convert('RGBA')).getbbox()is None;imageproof.append({'png':str(png.relative_to(source)),'png_sha256':sha(png),'webp':str(dst.relative_to(D)),'webp_sha256':sha(dst),'pixels_identical':True})
 (D/'NATIVE_PIXEL_PROOFS.json').write_text(json.dumps(imageproof,ensure_ascii=False,indent=2)+'\n')
 if source==C:
  shutil.copy2(Q/'scripts/check_office_control.py',D/'check_office_control.py');shutil.copy2(Q/'check-office-reconnect.log',D/'controller.log.txt')
  (D/'README.md').write_text('# Office восстановлен\n\nПосле новых ONLINE с ноутбука, наступивших после прошлых FAIL, проверены свежие запросы обоих каналов. Выполнен один новый контроль на канал. Excel PASS 8 проверок, Word PASS одного исходника; все три страницы PDF просмотрены. Это разрешило последующие продуктовые прогоны. Статус ONLINE рассматривается как сообщение запуска агента; живую связь подтверждают реальные GET, запуск Office — только квитанции контрольных заданий. Программы, службы, защита и агенты нами не изменялись.\n')
 for path in D.rglob('*'):
  if path.is_file():assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}',path.read_bytes()),path
 inventory=[{'path':str(x.relative_to(D)),'bytes':x.stat().st_size,'sha256':sha(x)}for x in sorted(D.rglob('*'))if x.is_file()and x.name!='FINAL_ARTIFACTS_SHA256.json']
 (D/'FINAL_ARTIFACTS_SHA256.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
run(['git','add','--sparse','-f','--']+rels);names=[n for n in run(['git','diff','--cached','--name-only','-z']).split('\0')if n];assert names and all(any(n.startswith(r+'/')for r in rels)for n in names)
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--']+rels)
assert not run(['git','diff','--name-only']).strip()
run(['git','commit','-m','Verify restored Office and corrected advance free bundle [skip deploy]']);head=run(['git','rev-parse','HEAD']).strip();print('COMMIT',head,'FILES',len(names),flush=True)
with (Q/'push-avans-native.log').open('w')as log:
 p=subprocess.Popen(['git','-c','pack.threads=2','-c','core.compression=1','push','--progress','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,stdout=log,stderr=log,start_new_session=True)
 try:rc=p.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  raise
 assert rc==0,('PUSH_FAILED',rc)
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(head);assert not run(['git','status','--short']).strip();print('REMOTE_VERIFIED',head,flush=True)
