from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib,shutil,subprocess,xml.etree.ElementTree as E,copy
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';O=Q/'native-recovery-20261022';R=Q.parent/'integration-20261022/repo';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();bsha=lambda b:hashlib.sha256(b).hexdigest()
# Persist failure stage before any PDF assumptions; missing outputs are not product failures.
nr=P/'evidence/native/nsp-p5-print-v2-20261023/report.xml';wr=P/'evidence/word/nsp-p11-final-letter-tests-20261023/report.xml';ne=E.parse(nr).getroot();we=E.parse(wr).getroot()
assert ne.get('status')=='FAIL'and '0x80080005'in(ne.findtext('error')or'')and not ne.findall('check')
assert we.get('status')=='FAIL'and we.find('file').get('status')=='TIMEOUT'
blocker={'excel':{'receipt_sha256':sha(nr),'error':'COM activation 0x80080005','stage':'Before any workbook opening; all 3 files NOT_RUN','source_or_formula_failure_proven':False},'word':{'receipt_sha256':sha(wr),'first_file':'54-zapros-sostoyanie-escrow.docx','first_status':'TIMEOUT','following_2_synthetic_examples':'NOT_RUN','cause':'Not established; no direct laptop DC surface available'},'changes_to_office_windows_agents_services':False,'new_jobs_after_failure':'NONE; completed failed current.xml preserved','owner_step':'Save your work; close Excel/Word windows normally; launch Excel and Word manually, dismiss visible startup dialogs, confirm both open. No reinstall, service restart or security setting changes requested.'}
(P/'OFFICE_BLOCKER.json').write_text(json.dumps(blocker,ensure_ascii=False,indent=2))
manifest=json.loads((P/'paid-print-v2/MANIFEST.json').read_text());v4=json.loads((P/'paid-print-v4/MANIFEST.json').read_text());finalxls=[(P/'paid-print-v2'/r['file'],r['new_sha256'])for r in manifest if r['source_job']in(2,3)]+[(P/'paid-print-v4'/v4['file'],v4['new_sha256'])]
native53=json.loads((P/'P11_LAYOUT_NATIVE_V3.json').read_text())[0];assert native53['status']=='PASS'and native53['sha256']==sha(P/'p11-layout-v3'/native53['file'])
new54=json.loads((P/'P11_FINAL_LETTER_TESTS.json').read_text())[0];assert new54['role']=='BUYER_CANDIDATE'
old=json.loads(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/nsp-next-corrections-20261022/CANDIDATE_ARCHIVES.json'],text=True,timeout=15))
protected=json.loads(subprocess.check_output(['git','-C',str(R),'show','HEAD:tools/nsp-next-corrections-20261022/PROTECTED_ACCEPTED_MANIFEST.json'],text=True,timeout=15))['files']
report=[]
for sku,folder in [('P5','07-uderzhaniya-shtrafy-zachety'),('P11','13-raschet-metrami')]:
 dest=P/'package-sources/products-storage'/folder;assert not dest.exists();shutil.copytree(Q/'package-sources/products-storage'/folder,dest)
 if sku=='P5':chosen=finalxls;expected={p.name for p,h in chosen}
 else:chosen=[(O/'additional-candidates/products-storage/13-raschet-metrami/00-START-HERE.txt','5ae080f3ec510868433b9fafdc94fac6e8eeeb7780a55f969ec6615453cb0aec'),(P/'p11-layout-v3'/native53['file'],native53['sha256']),(P/'p11-final-letter-tests'/new54['path'],new54['new_sha256'])];expected={p.name for p,h in chosen}
 for p,h in chosen:assert sha(p)==h;shutil.copy2(p,dest/p.name)
 for row in protected:
  if row['sku']==sku:assert sha(dest/row['filename'])==row['accepted_sha256']
 orders=P/'orders-qa';delivery=P/'candidate-archives';orders.mkdir(exist_ok=True);delivery.mkdir(exist_ok=True)
 php="define('ORDERS_DIR',"+json.dumps(str(orders))+");define('PRODUCTS_DIR',"+json.dumps(str(dest.parent))+");define('DELIVERY_DIR',"+json.dumps(str(delivery))+");require "+json.dumps(str(R/'products-config.php'))+";echo mvb_build_product_zip("+json.dumps(sku.lower())+");"
 x=subprocess.run(['php','-r',php],capture_output=True,text=True,check=True,timeout=15);zp=Path(x.stdout);before=next(r for r in old['archives']if r['sku']==sku);bm={r['name']:r['sha256']for r in before['members']};members=[];changed=[]
 with ZipFile(zp)as z:
  assert z.testzip()is None and set(z.namelist())==set(bm)
  for n in z.namelist():
   h=bsha(z.read(n));members.append({'name':n,'sha256':h})
   if h!=bm[n]:changed.append(n)
 assert set(changed)==expected,(sku,changed,expected)
 report.append({'sku':sku,'archive':str(zp.relative_to(P)),'sha256':sha(zp),'members':members,'member_count':len(members),'changed_vs_previous_qa':changed,'builder':'unchanged mvb_build_product_zip','status':'PACKAGE_VERIFIED_NATIVE_ACCEPTANCE_BLOCKED','native_pending':[p.name for p,h in chosen if p.suffix=='.xlsx'or p.name.startswith('54-')],'canonical_or_public_changed':False})
(P/'FOLLOWUP_ARCHIVES.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Freeze the exact next inputs; do not change transport queues or submit.
deferred=P/'deferred-office-jobs';deferred.mkdir(exist_ok=True)
for channel,previous,jid in [('native','nsp-p5-print-v2-20261023','nsp-p5-final-print-r1-20261023'),('word','nsp-p11-final-letter-tests-20261023','nsp-p11-final-letters-r1-20261023')]:
 root=E.parse(P/'frozen-inputs'/previous/'job.xml').getroot();root.set('id',jid);root.set('scope','Deferred until owner confirms normal Office startup; never overwrite failed job')
 d=deferred/jid;d.mkdir(exist_ok=True)
 for f in root.findall('file'):
  p=next(p for p,h in finalxls if p.name==f.get('name'))if channel=='native'else P/'frozen-inputs'/previous/f.get('name')
  f.set('sha256',sha(p));shutil.copy2(p,d/p.name)
 E.ElementTree(root).write(d/'job.xml',encoding='utf-8',xml_declaration=True)
readme='ПАКЕТ ПРОВЕРКИ ВЛАДЕЛЬЦЕМ — НЕ ДЛЯ ВЫДАЧИ ПОКУПАТЕЛЮ\n\nExcel не запустился через COM (0x80080005) до открытия файлов; Word остановился по таймауту на 54. Эти версии пока не приняты в Office.\nСохраните свою работу, закройте окна Excel и Word обычным способом. Запустите обе программы вручную и проверьте отсутствие стартовых диалогов. Сообщите результат. Переустановка, смена настроек безопасности и установка скриптов не требуются.\nПосле восстановления будут отправлены два подготовленных задания с новыми id; старые квитанции и очереди сохраняются.\n\n53: нативный Word PASS, все 3 страницы просмотрены; отправляемая форма на одной странице.\n54: все 3 страницы LibreOffice просмотрены; Word TIMEOUT, нативная приёмка не состоялась.\nP5/22,23,29: печатные кандидаты с неизменными ячейками и формулами; нативная приёмка новых SHA не состоялась. 29 печатает 21 графу группами с повторением №/вида/реквизитов. Полный просмотр финальной печати ещё требуется.\n'
(P/'OWNER_STEP.txt').write_text(readme)
packet=P/'OWNER_REVIEW_ONLY.zip'
with ZipFile(packet,'w',ZIP_DEFLATED)as z:
 for p,h in finalxls:z.writestr('P5/'+p.name,p.read_bytes())
 for p in [P/'p11-layout-v3'/native53['file'],P/'p11-final-letter-tests'/new54['path']]:z.writestr('P11/'+p.name,p.read_bytes())
 z.writestr('START_HERE.txt',readme)
with ZipFile(packet)as z:assert z.testzip()is None and len(z.namelist())==6
print(json.dumps([{'sku':r['sku'],'archive':r['archive'],'sha256':r['sha256'],'member_count':r['member_count'],'status':r['status']}for r in report],ensure_ascii=False),flush=True);print('OWNER_PACKET',sha(packet),flush=True)
