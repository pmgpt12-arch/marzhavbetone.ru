from pathlib import Path
import json,hashlib,subprocess,shutil,xml.etree.ElementTree as E,datetime,os,signal,re,sys
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo'
S=Q/'office-control-20261022-233620';assert (S/'COMPLETED.txt').is_file()
rows=json.loads((S/'RESULTS.json').read_text());assert len(rows)==2 and {r['channel']for r in rows}=={'native','word'}
base='bec8a82b25b033ab52c6c99aea38dbf04dadccb3';rel='tools/nsp-next-corrections-20261022/office-control-20261022-233620';D=R/rel
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
assert not run(['git','status','--short']).strip()
assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(base)
assert not D.exists();shutil.copytree(S,D)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in rows:
 ch=row['channel'];rp=D/'evidence'/ch/row['job']/'report.xml';assert rp.exists()and sha(rp)==row['receipt_sha256']
 assert E.parse(rp).getroot().get('status')==row['status']
 src=E.parse(D/'inputs'/ch/'job.xml').getroot().find('file')
 assert sha(D/'inputs'/ch/src.get('name'))==src.get('sha256')
 # These are frozen source copies, not edits to accepted files.
 row['source_sha256']=src.get('sha256')
shutil.copy2(Q/'check-office-control.log',D/'controller.log.txt')
shutil.copy2(Q/'scripts/check_office_control.py',D/'check_office_control.py')
shutil.copy2(Path(__file__),D/Path(__file__).name)
start=json.loads((D/'PREFLIGHT.json').read_text())['created_utc']
log=subprocess.run(['journalctl','_PID=1606','--since',start,'-n','200','--no-pager','-o','cat'],capture_output=True,text=True,timeout=15)
assert log.returncode==0,log.stderr
lines=[l for l in log.stdout.splitlines()if any('/'+r['job']+'/'in l for r in rows)]
assert all(any('POST /'+r['channel']+'/result/'+r['job']+'/'in l for l in lines)for r in rows)
(D/'TRANSPORT.log.txt').write_text('\n'.join(lines)+'\n')
native=next(r for r in rows if r['channel']=='native');word=next(r for r in rows if r['channel']=='word')
parts=['# Проверка работы Word и Excel','', 'Контроль 23.10.2026 по Красноярску. Один ранее принятый файл на каждую программу; задания выполнены последовательно. Исходники и программные настройки не изменялись.','',
 'Гипотеза: свежие статусы ONLINE после предыдущих отказов могли соответствовать восстановлению агентов. Это не доказательство запуска самих приложений. Поэтому вместо продуктового пакета использованы известные контрольные исходники.',
 '', 'Excel: '+native['status']+'. Проверок в квитанции: '+str(len(native.get('checks',[])))+'.',
 'Word: '+word['status']+'. Квитанции файлов: '+json.dumps(word.get('file_receipts',[]),ensure_ascii=False)+'.']
if native['status']!='PASS':
 parts+=['','Excel не выполнил даже контроль на ранее успешном файле. Первичная ошибка: '+(native.get('error')or'Квитанция не содержит подробной ошибки').splitlines()[0]+'.']
if word['status']!='PASS':
 parts+=['','Для Word причина таймаута не установлена: сама квитанция не различает запуск приложения, открытие документа и экспорт. Это не доказательство дефекта контрольного DOCX.']
parts+=['','Граница результата: проверяется автоматизированный путь через существующих агентов. Возможность ручной работы в открытом окне напрямую не наблюдалась; DC предоставляет доступ только к ai-workstation. Обновлять, переустанавливать, менять защиту или принудительно закрывать пользовательские процессы не выполнялось.',
 '', 'Правило после повторяемого сбоя: ONLINE → минимальный известный контроль → точный SHA и исходная квитанция → разрешение продуктовых пакетов только после PASS. Повтор без нового наблюдения, гипотезы или восстановления запрещён. Сбой COM до открытия файла относится к активации приложения; таймаут без подробностей остаётся неопределённым этапом runtime.',
 '', 'Если оба контроля PASS, это подтверждает только эти операции и эти исходники, а не общую приёмку продуктов. Если FAIL, повторную продуктовую очередь не запускать.',
 '', 'Следующий диагностический шаг при отказе: получить с ноутбука список процессов EXCEL и WINWORD с Responding и MainWindowTitle, чтобы различить отсутствие процесса, зависание и окно/диалог. Такой вывод пока не получен.']
(D/'README.md').write_text('\n'.join(parts)+'\n')
(D/'GATE.json').write_text(json.dumps({'transport':'PASS_FRESH_INPUT_DOWNLOAD_AND_RECEIPT_UPLOAD','native_control':native['status'],'word_control':word['status'],'product_batch_allowed':all(r['status']=='PASS'for r in rows),'manual_GUI_operation':'NOT_OBSERVED','excel_failure_stage':'COM_ACTIVATION_BEFORE_WORKBOOK_OPEN'if native['status']=='FAIL'and '0x80080005'in (native.get('error')or'')else'CHECK_RECEIPT','word_failure_stage':'UNDETERMINED_TIMEOUT'if any(f.get('status')=='TIMEOUT'for f in word.get('file_receipts',[]))else'CHECK_RECEIPT','automatic_retry_allowed':False,'next_gate':'New observed recovery or process/window diagnostics, then a new immutable known-good control job'},ensure_ascii=False,indent=2)+'\n')
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}']
for p in D.rglob('*'):
 if p.is_file():assert not any(re.search(pat,p.read_bytes())for pat in patterns),p
inv=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(D.rglob('*'))if p.is_file()]
(D/'ARTIFACTS_SHA256.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
run(['git','add','--sparse','-f','--',rel]);names=run(['git','diff','--cached','--name-only']).splitlines()
assert len(names)==len(inv)+1 and all(n.startswith(rel+'/')for n in names)
exclusions=[':(exclude)'+rel+'/evidence/'+r['channel']+'/'+r['job']+'/report.xml'for r in rows]
exclusions+=[':(exclude)'+rel+'/controller.log.txt']
# Raw native XML and error text retain the Windows-generated whitespace.
assert all(not l.endswith(' ') for l in (D/'README.md').read_text().splitlines())
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--',rel]+exclusions)
for x in inv:assert sha(D/x['path'])==x['sha256']
run(['git','commit','-m','Check Word and Excel with known-good single-file controls [skip deploy]'])
head=run(['git','rev-parse','HEAD']).strip();print('COMMIT',head,flush=True)
with (Q/'push-office-control.log').open('w')as log:
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
print('REMOTE_VERIFIED',head,'RESULTS',[(r['channel'],r['status'])for r in rows],flush=True)
