import json, shutil, subprocess, time, os, hashlib, traceback, re
from pathlib import Path
import uno
from com.sun.star.beans import PropertyValue
R=Path(__file__).resolve().parent
SRC=Path('/home/denis/projects/marzhavbetone.ru/.worktrees/codex-s1-excel-wording-overlay-20261005/tools/candidates/s1-oplata-za-raboty/04-uchet-raschetov-i-otpravok.xlsx')
EXPECTED='f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt={'status':'RUNNING','synthetic':True,'excel_manual_pass':False,'source_before':sha(SRC),'runs':[]}
assert receipt['source_before']==EXPECTED
COPY=R/'native-disposable-copy.xlsx';shutil.copy2(SRC,COPY);receipt['copy_before']=sha(COPY);assert receipt['copy_before']==EXPECTED
PROF=R/'profile';xcu=PROF/'user/registrymodifications.xcu';xcu.parent.mkdir(parents=True)
xcu.write_text('<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooLocale" oor:op="fuse"><value>ru-RU</value></prop><prop oor:name="ooSetupSystemLocale" oor:op="fuse"><value>ru-RU</value></prop></item></oor:items>')
def pv(n,v):
 p=PropertyValue();p.Name=n;p.Value=v;return p
def norm(t):return re.sub(r'\s+','',t).lower()
pipe=f'actsel{os.getpid()}'
log=(R/'soffice.log').open('w');proc=subprocess.Popen(['soffice',f'-env:UserInstallation={PROF.as_uri()}','--headless','--norestore','--nologo',f'--accept=pipe,name={pipe};urp;'],stdout=log,stderr=log)
desktop=None;doc=None
try:
 local=uno.getComponentContext();resolver=local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',local)
 deadline=time.monotonic()+30
 while True:
  try:ctx=resolver.resolve(f'uno:pipe,name={pipe};urp;StarOffice.ComponentContext');break
  except Exception:
   if time.monotonic()>deadline:raise
   time.sleep(.25)
 desktop=ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',ctx)
 for n,last,acts,ops,expected_j,total in [
  ('one-act',6,[('TEST-A','КС-2 № TEST-A',46270)],[(46266,'Начисление по акту','КС-2 № TEST-A',100000,'TEST-A'),(46275,'Оплата','ПП № TEST-PAY-A',25000,'TEST-A')],[100000,75000],75000),
  ('two-acts',8,[('TEST-A','КС-2 № TEST-A',46270),('TEST-B','КС-2 № TEST-B',46280)],[(46266,'Начисление по акту','КС-2 № TEST-A',100000,'TEST-A'),(46275,'Оплата','ПП № TEST-PAY-A',25000,'TEST-A'),(46275,'Начисление по акту','КС-2 № TEST-B',200000,'TEST-B'),(46285,'Оплата','ПП № TEST-PAY-B',50000,'TEST-B')],[100000,75000,275000,225000],225000)]:
  entry={'name':n,'range':f'A4:J{last}'};receipt['runs'].append(entry)
  doc=desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(COPY)),'_blank',0,(pv('Hidden',True),))
  assert doc is not None
  sheet=doc.Sheets.getByName('Взаиморасчёты');ak=doc.Sheets.getByName('Долг по актам')
  for row,act in enumerate(acts,5):
   for col,val in zip('BCD',act):
    c=ak.getCellRangeByName(f'{col}{row}')
    if isinstance(val,str):c.String=val
    else:c.Value=val
  for row,op in enumerate(ops,5):
   for col,val in zip('BCDEF',op):
    c=sheet.getCellRangeByName(f'{col}{row}')
    if isinstance(val,str):c.String=val
    else:c.Value=val
  doc.calculateAll()
  entry['actual_i']=[sheet.getCellRangeByName(f'I{r}').String for r in range(5,last+1)]
  entry['actual_j']=[sheet.getCellRangeByName(f'J{r}').Value for r in range(5,last+1)]
  entry['actual_m10']=sheet.getCellRangeByName('M10').Value
  entry['formula_gate']=entry['actual_i']==['ок']*len(ops) and entry['actual_j']==expected_j and entry['actual_m10']==total
  assert entry['formula_gate'],entry
  ctrl=doc.CurrentController;ctrl.setActiveSheet(sheet);ctrl.select(sheet.getCellRangeByName(entry['range']))
  selection=doc.getCurrentSelection();a=selection.getRangeAddress();entry['actual_range']={k:getattr(a,k) for k in ['Sheet','StartColumn','EndColumn','StartRow','EndRow']}
  assert entry['actual_range']=={'Sheet':0,'StartColumn':0,'EndColumn':9,'StartRow':3,'EndRow':last-1},entry
  entry['export_properties']={'FilterName':'calc_pdf_Export','FilterData':['Selection=currentSelection']}
  pdf=R/f'{n}.pdf';doc.storeToURL(uno.systemPathToFileUrl(str(pdf)),(pv('FilterName','calc_pdf_Export'),pv('FilterData',(pv('Selection',selection),))))
  entry['pdf_sha256']=sha(pdf)
  subprocess.run(['pdftotext','-layout',str(pdf),str(R/f'{n}.txt')],check=True,timeout=30)
  info=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True,timeout=30).stdout;(R/f'{n}.pdfinfo.txt').write_text(info)
  entry['pages']=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
  subprocess.run(['pdftoppm','-png','-scale-to','1400',str(pdf),str(R/f'{n}-page')],check=True,timeout=45)
  text=(R/f'{n}.txt').read_text();flat=norm(text)
  headers=[sheet.getCellRangeByName(f'{c}4').String for c in 'ABCDEFGHIJ'];entry['headers']={h:norm(h) in flat for h in headers}
  entry['fixture_tokens']={s:norm(s) in flat for op in ops for s in [op[2],op[4],str(op[3])]}
  forbidden=['Сверка с авансом','Начислено по актам','ОБЩИЙ ДОЛГ ПО ДАННЫМ СУБПОДРЯДЧИКА','Реестр передачи','Реестр приложений','Переносить в файл 08','Подписи сторон']
  entry['unexpected_tokens']=[s for s in forbidden if norm(s) in flat]
  entry['has_hash_marks']='####' in text
  entry['text_gate']=all(entry['headers'].values()) and all(entry['fixture_tokens'].values()) and not entry['unexpected_tokens'] and not entry['has_hash_marks']
  entry['visual_gate']='NOT_REVIEWED';entry['status']='EXPORTED_TEXT_CHECKED'
  doc.setModified(False);doc.close(True);doc=None
 receipt['status']='EXPORTED_AWAITING_VISUAL_REVIEW' if all(x['text_gate'] for x in receipt['runs']) else 'FAIL_TEXT_GATE'
except Exception:
 receipt['status']='FAIL';receipt['error']=traceback.format_exc();print(receipt['error'])
finally:
 if doc is not None:
  try:doc.setModified(False);doc.close(True)
  except Exception as e:receipt['close_error']=str(e)
 if desktop is not None:
  try:desktop.terminate()
  except Exception as e:receipt['terminate_error']=str(e)
 try:proc.wait(timeout=15)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
 log.close();receipt['source_after']=sha(SRC);receipt['copy_after']=sha(COPY);receipt['native_preserved']=receipt['source_after']==receipt['source_before']==receipt['copy_before']==receipt['copy_after']==EXPECTED
 (R/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False,indent=2))
