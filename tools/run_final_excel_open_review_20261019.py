#!/usr/bin/env python3
"""Sequential exact-SHA Excel opening/print review; receipt before every next job."""
from pathlib import Path
from hashlib import sha256
import xml.etree.ElementTree as E
import sys,time,json,shutil
from submit_office_review_job import submit
REPO=Path(__file__).resolve().parents[1]
ROOT=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
B=REPO/'tools/candidates/remaining-batch-r3-20261018'
WORK=B/'checkpoint-working';OUT=B/'evidence/native-final-20261019';OUT.mkdir(exist_ok=True,parents=True)
groups=[('p1',[('P1','06A-rabochiy-reestr-obemov.xlsx','p106a','Реестр'),('P1','07-reestr-zamechaniy.xlsx','p107','Реестр'),('P1','08-reestr-peredachi.xlsx','p108','Реестр'),('P1','14-raschet-procentov-395-gk.xlsx','p114','Входные данные')]),
 ('p2-p4',[('P2','07-raschet-stoimosti.xlsx','p207','Реестр'),('P2','08-zhurnal-doprabot.xlsx','p208','Реестр'),('P4','06-reestr-zamechaniy.xlsx','p406','Реестр замечаний по ИД'),('P4','07-grafik-ustraneniya.xlsx','p407','График устранения замечаний')]),
 ('p4-registers',[('P4','35A-rabochiy-zhurnal-proizvodstva-rabot.xlsx','p435a','Реестр'),('P4','36A-rabochiy-reestr-vhodnogo-kontrolya.xlsx','p436a','Реестр'),('P4','37-reestr-pasportov.xlsx','p437','Реестр'),('P4','38-reestr-id.xlsx','p438','Реестр')]),
 ('p7-p13',[('P7','02-perechen-rabot.xlsx','p702','Реестр'),('P7','03-kalendarnyy-plan.xlsx','p703','Реестр'),('P7','05-grafik-platezhey.xlsx','p705','Реестр'),('P13','63-reestr-zatrat-po-obektu.xlsx','p1363','Реестр затрат')]),
 ('p8-p9',[('P8','02-kalkulyator-usloviy-avansa.xlsx','p802','Условия'),('P8','09-raschet-otrabotannoy-chasti-avansa.xlsx','p809','Договор и аванс'),('P9','04-reestr-dokumentov-i-dat-po-obektu.xlsx','p904','Объект и должник')])]
summary=[];deadline=time.monotonic()+1500
for label,items in groups:
 ident='r3f-excel-'+label+'-open-20261019';jobdir=ROOT/'native'/ident
 job=E.Element('job',id=ident,qa_only='true')
 for sku,name,tag,sheet in items:
  data=(WORK/sku/name).read_bytes();E.SubElement(job,'file',name=name,tag=tag,sheet=sheet,sha256=sha256(data).hexdigest())
 receipt=ROOT/'results/native'/ident/'report.xml'
 if not (jobdir/'job.xml').exists():
  jobdir.mkdir(exist_ok=True)
  for sku,name,tag,sheet in items:shutil.copyfile(WORK/sku/name,jobdir/name)
  E.ElementTree(job).write(jobdir/'job.xml',encoding='utf-8',xml_declaration=True)
 else:
  old=E.parse(jobdir/'job.xml').getroot()
  assert old.attrib==job.attrib and [x.attrib for x in old]==[x.attrib for x in job],ident
 if not receipt.exists():
  submit(ROOT,'native',jobdir);print('SUBMITTED',ident,flush=True)
  until=min(deadline,time.monotonic()+300)
  while not receipt.exists() and time.monotonic()<until:time.sleep(3)
 if not receipt.exists():raise SystemExit('RECEIPT_TIMEOUT '+ident)
 report=E.parse(receipt).getroot();assert report.get('job')==ident
 target=OUT/ident;target.mkdir(exist_ok=True);shutil.copyfile(jobdir/'job.xml',target/'job.xml')
 for p in receipt.parent.iterdir():
  if p.is_file():shutil.copyfile(p,target/p.name)
 for source,(sku,name,tag,sheet) in zip(job,items):
  row={'job':ident,'sku':sku,'file':name,'sha256':source.get('sha256'),'tag':tag,'status':report.get('status'),'scope':'Native opening, recalculation and PDF export; visual inspection and case tests recorded separately'}
  if report.get('status')=='PASS':
   for suffix in ['input_sha','pdf_export','source_unchanged']:
    c=report.find("check[@name='"+tag+':'+suffix+"']");assert c is not None and c.get('pass').lower()=='true'
   assert (target/(tag+'-filled.pdf')).read_bytes().startswith(b'%PDF-')
  summary.append(row)
 (OUT/'open-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print('RECEIPT',ident,report.get('status'),'FILES',len(items),flush=True)
 if report.get('status')!='PASS':raise SystemExit('STOP_INSPECT_FAILURE '+ident)
print('ALL_CURRENT_XLSX_OPEN_PASS',len(summary),flush=True)
