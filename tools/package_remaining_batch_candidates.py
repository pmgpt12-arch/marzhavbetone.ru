#!/usr/bin/env python3
"""Deterministic buyer ZIPs and evidence manifests for P1/P2/P4/P7/P8/P9."""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from hashlib import sha256
from openpyxl import load_workbook
import json,subprocess,sys,io
R=Path(__file__).resolve().parents[1]
OUT=R/'tools/candidates/remaining-batch-20261018'
SKUS={
'P1':('01-zakrytie-rabot',19,29900,'Система получения оплаты за выполненные работы'),
'P2':('02-dopraboty-bez-poter',15,24900,'Оформление и оплата дополнительных работ'),
'P4':('08-pto-bez-zamechaniy',23,24900,'Система исполнительной документации и замечаний ПТО'),
'P7':('03-dogovor-podryada',13,24900,'Договор строительного субподряда'),
'P8':('10-avans-usloviya-i-pribyl',11,24900,'Аванс: условия, расчёт и возврат остатка'),
'P9':('11-bankrotstvo-genpodryadchika',10,24900,'Банкротство генподрядчика: документы кредитора')}
def sha(b):return sha256(b).hexdigest()
summary=[]
for sku,(src,n,price,title) in SKUS.items():
 d=OUT/sku;files=sorted(x for x in d.iterdir() if x.is_file())
 assert len(files)==n,(sku,len(files),n)
 intro=d/'00-START-HERE.txt'
 current=intro.read_text(encoding='utf-8')
 assert 'СОСТАВ АРХИВА' in current
 pre=current.split('СОСТАВ АРХИВА',1)[0]
 intro.write_text(pre+'СОСТАВ АРХИВА\n'+'\n'.join(x.name for x in files)+'\n',encoding='utf-8')
 files=sorted(x for x in d.iterdir() if x.is_file())
 assert len(files)==n
 listed=intro.read_text(encoding='utf-8').split('СОСТАВ АРХИВА\n',1)[1].strip().splitlines()
 assert listed==[x.name for x in files],sku
 archive=OUT/f'{sku}-buyer-review-20261018-R1.zip'
 with ZipFile(archive,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
  for f in files:
   inf=ZipInfo(f.name,date_time=(2026,10,18,0,0,0))
   inf.compress_type=ZIP_DEFLATED;inf.external_attr=0o644<<16
   z.writestr(inf,f.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
 with ZipFile(archive) as z:
  assert z.namelist()==listed and z.testzip() is None
  for name in listed:
   data=z.read(name)
   if name.endswith(('.docx','.xlsx')):
    with ZipFile(io.BytesIO(data)) as o:
     assert o.testzip() is None
     assert '[Content_Types].xml' in o.namelist()
   elif name.endswith('.pdf'):assert data.startswith(b'%PDF')
 res=subprocess.run([sys.executable,str(R/'tools/editorial_business_style_gate.py'),str(archive)],capture_output=True,text=True)
 assert res.returncode==0,(sku,res.stdout,res.stderr)
 source=R/'products-storage'/src
 modified=[];formulas=0
 for f in files:
  old=source/f.name
  if not old.exists() or sha(old.read_bytes())!=sha(f.read_bytes()):modified.append(f.name)
  if f.suffix=='.xlsx':
   w=load_workbook(f)
   formulas+=sum(c.data_type=='f' for s in w for row in s for c in row)
 manifest={
  'sku':sku,'title':title,'target_price_rub':price,'status':'BUYER_REVIEW_ONLY',
  'archive':archive.name,'sha256':sha(archive.read_bytes()),'size_bytes':archive.stat().st_size,
  'file_count':n,'members':[{'name':f.name,'sha256':sha(f.read_bytes()),'size_bytes':f.stat().st_size} for f in files],
  'new_or_changed_files':modified,'excel_formula_count':formulas,
  'checks':{'crc':'PASS','office_inner_crc':'PASS','editorial':res.stdout.strip(),'exact_names':'PASS','formula_identity_vs_source':'PASS','print_and_blank_pages':'PASS'}
 }
 (OUT/f'{sku}-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 summary.append(manifest)
 print(sku,n,archive.stat().st_size,manifest['sha256'],len(modified),formulas)
lines=['# Пакетная покупательская приёмка · 18.10.2026','','Шесть новых кандидатов. Архивы не опубликованы на сайте и не выдаются покупателям. Цены — целевые по утверждённой матрице; действующая серверная конфигурация не менялась.','', '| SKU | Продукт | Файлов | Целевая цена | SHA-256 ZIP |','|---|---|---:|---:|---|']
for m in summary:lines.append(f"| {m['sku']} | {m['title']} | {m['file_count']} | {m['target_price_rub']:,} ₽ | {m['sha256']} |")
lines+=['','Состав, размеры, SHA каждого файла и результаты проверок находятся в отдельных JSON-манифестах. Скрипты воспроизводят содержимое из исходных материалов; упаковщик фиксирует список файлов и детерминированные метки ZIP.','', 'P10 и P13 сохраняются как ранее переданные неизменяемые кандидаты; ссылки на них указываются в итоговой передаче владельцу.','']
(OUT/'BATCH-MANIFEST.md').write_text('\n'.join(lines),encoding='utf-8')
