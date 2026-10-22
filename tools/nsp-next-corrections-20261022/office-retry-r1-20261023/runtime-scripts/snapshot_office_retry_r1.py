from pathlib import Path
import json, hashlib, shutil, subprocess, zipfile, io, re, os, signal, datetime
from lxml import etree as E
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022')
P=Q/'paid-followup-20261023';R=Q.parent/'integration-20261022/repo'
rel='tools/nsp-next-corrections-20261022/office-retry-r1-20261023';D=R/rel
base='cecccbb798dfd444ef8d5a88b645762117015fe7'
sha=lambda b:hashlib.sha256(b).hexdigest()
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
assert run(['git','rev-parse','HEAD']).strip()==base
assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
assert not run(['git','status','--short']).strip()
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(base)
assert not D.exists();D.mkdir(parents=True)
def write(name,obj): (D/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
for ch,jid in [('native','nsp-p5-final-print-r1-20261023'),('word','nsp-p11-final-letters-r1-20261023')]:
 st=json.loads((P/('RETRY_'+ch.upper()+'.json')).read_text());assert st['job']==jid and st['status']=='FAIL'
 shutil.copy2(P/('RETRY_'+ch.upper()+'.json'),D/('RETRY_'+ch.upper()+'.json'))
 dest=D/'evidence'/ch/jid;dest.mkdir(parents=True)
 src=P/'evidence'/ch/jid/'report.xml';assert sha(src.read_bytes())==st['receipt_sha256'];shutil.copy2(src,dest/'report.xml')
 shutil.copy2(P/('retry-'+ch+'.log'),D/('retry-'+ch+'.log.txt'))
j=subprocess.run(['journalctl','_PID=1606','--since','2026-10-23 06:22:00','--until','2026-10-23 06:28:00','--no-pager','-o','cat'],capture_output=True,text=True,timeout=15)
assert j.returncode==0
lines=[l for l in j.stdout.splitlines()if '/nsp-p5-final-print-r1-20261023/'in l or '/nsp-p11-final-letters-r1-20261023/'in l]
assert any('POST /native/result/'in l for l in lines)and any('POST /word/result/'in l for l in lines)
(D/'TRANSPORT_RECEIPTS.log.txt').write_text('\n'.join(lines)+'\n')
shutil.copy2(Q/'native-recovery-20261022/PRESERVATION_GATE.json',D/'PRESERVATION_GATE.json')
assert json.loads((D/'PRESERVATION_GATE.json').read_text())['status']=='PASS'
V=D/'preliminary-print-review';V.mkdir()
for src in sorted((P/'print-review-r1').glob('*-contact-*.jpg')):shutil.copy2(src,V/src.name)
for name in ['p22-5.png','p23-7.png','p29-20.png']:shutil.copy2(P/'print-review-r1'/name,V/name)
review=[]
for tag,folder,stem,count in [('p22','rendered-paid-print-v2','22-reestr-garantiynyh-uderzhaniy',5),('p23','rendered-paid-print-v2','23-reestr-ispolnitelnoy-dokumentacii',7),('p29','rendered-paid-print-v4','29-opis-dokazatelstv-po-defektu',21)]:
 pdf=P/folder/(stem+'.pdf');text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True);pages=text.split('\f');assert len(pages)-1==count
 review.append({'file':stem,'pdf_sha256':sha(pdf.read_bytes()),'pages':count,'contact_review_pages':list(range(1,count+1)),'enlarged_example_page':{'p22':5,'p23':7,'p29':20}[tag],'status':'PRELIMINARY_REVIEW_ONLY_NATIVE_GATE_OPEN'})
 if tag=='p29':
  for i in range(1,13):assert all(s in pages[i]for s in ['Вид документа','Наименование','№'])
write('P5_PRELIMINARY_VISUAL.json',{'files':review,'total_pages':33,'scope':'Contact views of all pages and enlarged example pages; not full 100-percent page acceptance or native Excel acceptance.','observations':['22 example page 5: label for alternative return rate is clipped at adjacent populated cell; confirm and repair as a separate layout issue.','23 page 4 mostly empty table continuation. 29 page 15 repeated header with no data; printing efficiency remains open.','29 main register pages 2-13 retain repeated document identifiers and column headers in text extraction.','No claim that native Excel Print_Area or Print_Titles recognition has been repaired.']})
S=Q.parent/'remaining-audit-20261022/free-sources/downloads/avans.zip'
raw=S.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
line=run(['git','ls-tree',base,'downloads/avans.zip']);assert line.split()[2]==blob
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
idx=[];content=[];cells={}
with zipfile.ZipFile(S)as z:
 assert z.testzip()is None
 for n in z.namelist():
  b=z.read(n);idx.append({'file':n,'sha256':sha(b),'bytes':len(b)})
  if n.endswith('.docx'):
   with zipfile.ZipFile(io.BytesIO(b))as d:
    root=E.fromstring(d.read('word/document.xml'))
    content+=['FILE '+n,'\n'.join(''.join(p.xpath('.//w:t/text()',namespaces=ns))for p in root.xpath('//w:p',namespaces=ns)),'']
  elif n.endswith('.xlsx'):
   with zipfile.ZipFile(io.BytesIO(b))as x:
    for xml in ['xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml']:
     cs={}
     for c in E.fromstring(x.read(xml)).xpath('//m:sheetData/m:row/m:c',namespaces=ns):
      f=c.find('m:f',ns);v=c.find('m:v',ns)
      val=''.join(c.xpath('.//m:t/text()',namespaces=ns))
      if f is not None:val='='+f.text
      elif v is not None:val=v.text
      if val:cs[c.get('r')]=val
     cells[xml]=cs
assert cells['xl/worksheets/sheet1.xml']['D12']=='=SUM(D4:D11)'
write('AVANS_SOURCE_INDEX.json',{'archive_sha256':sha(raw),'git_blob':blob,'verified_against':base,'members':idx,'reviewed':'3 DOCX full paragraph text and 2 XLSX sheets; 99 PDF not yet reviewed','source_changed':False})
(D/'AVANS_SOURCE_DOCX_TEXT.txt').write_text('\n'.join(content))
write('AVANS_SOURCE_CELLS.json',cells)
write('AVANS_MODEL_DEFECTS.json',{'status':'SOURCE_DEFECTS_CONFIRMED_CORRECTIONS_NOT_AUTHORED','formula':'Изъятия!D12=SUM(D4:D11)','issues':[
 {'id':'AVANS-01','severity':'critical','where':'Изъятия!A4,D12 and Как считать!C5,C8,C9','defect':'Outstanding received advance, withheld/blocked money, costs and gross unaccepted work are summed as cash not held. Stock, cost flow and contractual exposure are not additive cash shortages.','counterexample':{'assumption':'Advance of 1000000 received today and remains fully available; no work, withholdings, expenses or security deposit.','inputs_D4_D11':[1000000,0,0,0,0,0,0,0],'source_SUM_result':1000000,'cash_unavailable_due_to_listed_deductions':0,'native_execution':False},'fix_rule':'Separate advance exposure, actual withheld/blocked money, paid costs and work receivable. Remove the single money-not-with-us total and the claim that its ratio to monthly need proves funding runway. Require actual cash, dates and forecast payments for liquidity assessment.','gates':['Advance-only case must not become an unavailable-cash amount.','Guarantee face amount is not cash expenditure. Fee and actual collateral are separate.','100000 gross work including 10000 retained must not be added to the same 10000 again.','Retention base follows contract and underlying certificates, not an unconditional percent of net payments.']},
 {'id':'AVANS-02','severity':'high','where':'01 checklist: no explicit suspension right means advance exists only on paper','defect':'Categorical loss of statutory protection is unsupported.','law':['GK 328 paragraphs 2 and 4','GK 719 paragraphs 1 and 2'],'fix_rule':'Check due advance, linkage to work, obstruction, contract terms and written notice; absence of a repeated clause is not by itself absence of a statutory remedy.'},
 {'id':'AVANS-03','severity':'high','where':'01/03 guarantee descriptions','defect':'Irrevocability is equated with automatic payment; end-of-obligations wording is treated as a valid unlimited guarantee.','law':['GK 368 paragraph 4'],'fix_rule':'Review the guarantee itself, stated term, circumstances, documentary demand and bank agreement. Irrevocability describes amendment/revocation, not automatic compliance of any demand.'},
 {'id':'AVANS-04','severity':'high','where':'01/03 offset and unsigned work clauses','defect':'Unilateral setoff is presented as necessarily improper; unsigned work is described as automatically zeroed.','law':['GK 410'],'fix_rule':'Distinguish contractual advance deduction, payment adjustment and statutory setoff. Check statement, grounds and restrictions. Distinguish contractual evidentiary risk from established loss of the value of completed work.'},
 {'id':'AVANS-05','severity':'medium','where':'04 reply interpretation','defect':'Reply consistency promises no surprises; absence of reply predicts all future correspondence.','fix_rule':'Remove outcome guarantees and predictions; preserve correspondence, reconcile final contract text and identify unresolved matters.'}],
 'primary_work_next':'Author separate revised candidates; validate model semantics before native numeric checks; 99 PDF and full bundle/native/visual gates remain open.'})
write('AVANS_LEGAL_SOURCES.json',{'checked_on':'2026-10-23 Asia/Krasnoyarsk','sources':[
 {'article':'GK 328','url':'https://www.consultant.ru/document/cons_doc_LAW_5142/331033e3d6e7b72213bd9903b03e29dfb9e608fe/','read':'full current article','scope':'Conditions and contract qualification of reciprocal performance'},
 {'article':'GK 719','url':'https://www.consultant.ru/document/cons_doc_LAW_9027/3a590316d2440dd63f7510f9238f24357b93bf61/','read':'full current article','scope':'Contractor response to obstructing nonperformance'},
 {'article':'GK 410','url':'https://www.consultant.ru/document/cons_doc_LAW_5142/ce09e59d11f3a60c30a1601c0f6c7cceb9835dfa/','read':'full current article','scope':'Unilateral statement can suffice subject to statutory conditions'},
 {'article':'GK 368','url':'https://www.consultant.ru/document/cons_doc_LAW_5142/03edc46b2ef855fddfaaa3d77dac1d071ef3dba1/','read':'full current article','scope':'Independent guarantee terms include duration and payment circumstances'}],'not_relied_upon':['GK376 Garant page unavailable403; one unverified Consultant URL inaccessible; GK411 click timed out. No substantive conclusion from those failed requests.'],'limits':'No real contract or cash position supplied; findings concern categorical template claims and mixed model categories.'})
(D/'EXECUTION_ERROR_LEDGER.md').write_text('# Ошибки выполнения\n\nОдин запуск Word не состоялся из-за опечатки в каталоге перенаправления журнала: shell завершился до запуска Python и до изменения очереди. Путь исправлен; выполнена ровно одна успешная отправка уникального Word id.\n\nПовторная активация Excel снова дала 0x80080005 до открытия книг. Word получил TIMEOUT на pt1; для pt2 и pt3 результатов нет. Оба исходных XML сохранены побайтно. Новых повторов после этих квитанций не было.\n')
(D/'README.md').write_text('# Повторная проверка Office и аудит аванса\n\nПроверка 23 октября 2026 года по Красноярску. Статус PARTIAL_PROGRESS_OFFICE_RUNTIME_BLOCKER.\n\nСвязь подтверждена свежими GET входных файлов и POST обеих квитанций с ноутбука. Excel и Word проверены последовательно. Excel снова отказал при создании Excel.Application с COM 0x80080005, до открытия книг: ноль проверок, PDF нет. Word снова завершился TIMEOUT на первом файле pt1 (новая форма P11/54); два последующих учебных примера не проверены. Причина Word по этой квитанции не установлена. Само восстановление сети не устранило запуск Office. Одновременный запуск двух наших заданий не объясняет этот повторный отказ Excel.\n\nРанее принятый P11/53 остаётся принят для своего SHA. Новые три печатные версии P5 и P11/54 не получили нативную приёмку. Автоматических повторов, принудительного закрытия пользовательских процессов, изменений Office, служб, защиты или агентов после отказов нет.\n\nВсе 33 страницы печатных PDF P5 просмотрены в контактных листах, примеры отдельно увеличены. Это предварительный просмотр LibreOffice, а не полный просмотр всех страниц в масштабе 100% и не приёмка Excel. В 22 на странице примера обнаружена обрезанная подпись ставки; остаётся отдельная правка оформления. Для 29 повторяемые идентификаторы проверены также извлечением текста на страницах 2–13. Не утверждается, что распознавание печатных имён в Excel исправлено.\n\nНезависимо проверен исходный бесплатный комплект avans.zip: три DOCX и обе страницы модели XLSX прочитаны целиком. Подтверждена критическая ошибка модели: SUM(D4:D11) складывает остаток полученного аванса, удержания, залог, расходы и стоимость непринятых работ под общей подписью «денег объекта не у вас». Контрпример: полученный и полностью доступный аванс 1 млн даёт в таком итоге 1 млн недоступных денег при фактическом отсутствии удержаний и расходов. Это анализ исходной формулы, не имитация нативного прогона. Найдены также категорические неточности про приостановку, гарантию, зачёт и неподписанные работы; правила исправления и действующие статьи сведены в отдельных JSON. Исправленные файлы аванса ещё не создавались, его 99 PDF не проверен. Комплект не принят.\n\nПовторный контроль сохранности прошёл: 19 исходных кандидатов, 13 принятых файлов, шесть удержанных оригиналов и 13 прежних QA ZIP с 172 вложениями неизменны. P8/02 и P8/09 не повторялись. main, канонические мастера, публичные ZIP, цены и платежи не изменялись нами.\n\nДля продолжения нативной приёмки владельцу нужно сохранить работу и обычным способом закрыть и снова открыть Excel и Word на ноутбуке; сообщить точный текст стартовой ошибки или диалога, если появится. Прямой доступ DC сейчас есть только к ai-workstation. Новое задание после такого восстановления должно получить новый id; уже использованные id не повторять. Общая приёмка линейки остаётся открытой.\n')
Sdir=D/'runtime-scripts';Sdir.mkdir();shutil.copy2(Path(__file__),Sdir/Path(__file__).name)
shutil.copy2(Q/'scripts/retry_office_after_owner.py',Sdir/'retry_office_after_owner.py')
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}']
for p in D.rglob('*'):
 if p.is_file():assert not any(re.search(pat,p.read_bytes())for pat in patterns),p
inv=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(D.rglob('*'))if p.is_file()]
write('ARTIFACTS_SHA256.json',inv)
run(['git','add','--sparse','-f','--',rel]);names=run(['git','diff','--cached','--name-only']).splitlines()
assert len(names)==len(inv)+1 and all(n.startswith(rel+'/')for n in names)
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--',rel,':(exclude)'+rel+'/evidence/native/nsp-p5-final-print-r1-20261023/report.xml'])
for x in inv:assert sha((D/x['path']).read_bytes())==x['sha256']
run(['git','commit','-m','Record sequential Office failures and advance model audit [skip deploy]'])
head=run(['git','rev-parse','HEAD']).strip();print('COMMIT',head,flush=True)
with (Q/'push-office-retry-r1.log').open('w')as log:
 p=subprocess.Popen(['git','-c','pack.threads=2','-c','core.compression=1','push','--progress','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,stdout=log,stderr=log,start_new_session=True)
 try:rc=p.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  raise
 assert rc==0,('PUSH_FAILED',rc)
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(head)
assert not run(['git','status','--short']).strip()
print('REMOTE_VERIFIED',head,'FILES',len(inv)+1,flush=True)
