#!/usr/bin/env python3
"""Final, idempotent original-form overlay after workbook editing and stitching.

Never restyle official pages. Keep working registers, with their formulas and
features, as separate supplementary files. Does not nominate or publish ZIPs.
"""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from hashlib import sha256
from lxml import etree as E
from docx import Document
import json, shutil, copy

R=Path(__file__).resolve().parents[1]
B=R/'tools/candidates/remaining-batch-r3-20261018'
A=B/'form-originals-audit'
W=Path('/tmp/mb-r3/work')
EXTRA=Path('/tmp/mb-r3/all-packages-extra/P3')
def digest(p): return sha256(p.read_bytes()).hexdigest()
def writejson(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
if not (W/'P3').exists(): shutil.copytree(EXTRA,W/'P3')
before={str(p.relative_to(W)):digest(p) for p in W.rglob('*') if p.is_file()}
aux={
 ('P1','06-zhurnal-obemov.xlsx'):'06A-rabochiy-reestr-obemov.xlsx',
 ('P4','35-obshiy-zhurnal-rabot.xlsx'):'35A-rabochiy-zhurnal-proizvodstva-rabot.xlsx',
 ('P4','36-vhodnoy-kontrol.xlsx'):'36A-rabochiy-reestr-vhodnogo-kontrolya.xlsx',
}
for (sku,old),new in aux.items():
 p=W/sku/old; q=W/sku/new
 if p.exists():
  assert not q.exists() or digest(p)==digest(q),('auxiliary collision',sku,new)
  p.rename(q)
forms=[
 ('P1','06-zhurnal-ucheta-rabot-ks-6a.xls',B/'sources/KS-6a-original.xls'),
 ('P2','04-akt-skrytyh-rabot.pdf',A/'aosr-344-original.pdf'),
 ('P3','03-akt-skrytyh-rabot.pdf',A/'aosr-344-original.pdf'),
 ('P4','31-akt-osvidetelstvovaniya-skrytyh-rabot.pdf',A/'aosr-344-original.pdf'),
 ('P4','35-obshiy-zhurnal-rabot.pdf',A/'general-journal-1026-original.pdf'),
 ('P4','36-zhurnal-vhodnoy-verifikacii.pdf',A/'incoming-verification-24297-original.pdf'),
]
for sku,name,source in forms: shutil.copyfile(source,W/sku/name)
for sku,name in [('P2','04-akt-skrytyh-rabot.xlsx'),('P3','03-akt-skrytyh-rabot.docx'),('P4','31-akt-osvidetelstvovaniya-skrytyh-rabot.xlsx')]:
 (W/sku/name).unlink(missing_ok=True)
refs={old:new for (_,old),new in aux.items()}
refs.update({'04-akt-skrytyh-rabot.xlsx':'04-akt-skrytyh-rabot.pdf','03-akt-skrytyh-rabot.docx':'03-akt-skrytyh-rabot.pdf','31-akt-osvidetelstvovaniya-skrytyh-rabot.xlsx':'31-akt-osvidetelstvovaniya-skrytyh-rabot.pdf'})

def canonical(p):
 with ZipFile(p) as z: parts={n:z.read(n) for n in z.namelist()}
 with ZipFile(p,'w',ZIP_DEFLATED) as z:
  for n,data in sorted(parts.items()):
   i=ZipInfo(n,(2026,10,18,0,0,0));i.compress_type=ZIP_DEFLATED;z.writestr(i,data)

changes=[]
for p in sorted(W.rglob('*.docx')):
 with ZipFile(p) as z: parts={n:z.read(n) for n in z.namelist()}
 changed=False
 for n,data in list(parts.items()):
  if n.startswith('word/') and n.endswith(('.xml','.rels')):
   for old,new in refs.items(): data=data.replace(old.encode(),new.encode())
   if data!=parts[n]:parts[n]=data;changed=True
 if changed:
  with ZipFile(p,'w',ZIP_DEFLATED) as z:
   for n,data in parts.items():z.writestr(n,data)
 if p.name=='00-INSTRUKCIYA.docx' and p.parent.name in {'P1','P2'}:
  d=Document(p)
  def replace(prefix,text):
   candidates=[x for x in d.paragraphs if x.text.startswith(prefix)]
   assert len(candidates)==1,(str(p),prefix,len(candidates))
   para=candidates[0]
   if para.text!=text:
    runs=para.runs
    if runs:runs[0].text=text
    else:para.add_run(text)
    for run in runs[1:]:run.text=''
   changes.append({'file':str(p.relative_to(W)),'paragraph_prefix':prefix,'text':text})
  if p.parent.name=='P1':
   replace('По каждому предъявляемому объёму','По каждому предъявляемому объёму проверьте основание, подтверждающие документы, стоимость, дату передачи и срок оплаты. Форма КС-6а — файл 06; оперативный учёт объёмов и подтверждений — 06A. Реестр 07 содержит замечания, реестр 08 — передачу документов. До расчёта процентов в файле 14 сверьте остаток с банковскими выписками.')
   replace('Файлы 01-ks-2.xls','Файлы 01-ks-2.xls, 02-ks-3.xls и 06-zhurnal-ucheta-rabot-ks-6a.xls — опубликованные бланки КС-2, КС-3 и КС-6а по постановлению Госкомстата России от 11.11.1999 № 100. Текст, графы и оформление сохранены. Заполните их в Excel по документам объекта; применимость проверьте по договору и учётной политике.')
   replace('Файл 06','Файл 06A предназначен для оперативного учёта объёмов и подтверждений. Форму КС-6а заполняйте в файле 06 по документам объекта. Источник бланков КС-2, КС-3 и КС-6а: https://www.consultant.ru/document/cons_doc_LAW_26303/ .')
   for row in d.tables[0].rows:
    if row.cells[0].text=='06A-rabochiy-reestr-obemov.xlsx':
     for cell,text in zip(row.cells,['06-zhurnal-ucheta-rabot-ks-6a.xls','Для учёта выполненных работ','Журнал по форме КС-6а']):
      pp=cell.paragraphs[0];rr=pp.runs
      if rr:rr[0].text=text
      else:pp.add_run(text)
      for run in rr[1:]:run.text=''
   table=d.tables[0]
   if not any(row.cells[0].text=='06A-rabochiy-reestr-obemov.xlsx' for row in table.rows):
    original=next(row for row in table.rows if row.cells[0].text=='06-zhurnal-ucheta-rabot-ks-6a.xls')
    tr=copy.deepcopy(original._tr);original._tr.addnext(tr)
    row=next(row for row in table.rows if row._tr is tr)
    for cell,text in zip(row.cells,['06A-rabochiy-reestr-obemov.xlsx','Для оперативного учёта объёмов','Записи и ссылки на подтверждения']):
     pp=cell.paragraphs[0];rr=pp.runs
     if rr:rr[0].text=text
     else:pp.add_run(text)
     for run in rr[1:]:run.text=''
  else:
   replace('Формы Word и расчёты Excel','Формы Word и расчёты Excel заполните по документам объекта. Файл 04 — исходный бланк АОСР в PDF для печати и заполнения; интерактивные поля в нём отсутствуют. Остальные PDF содержат инструкции и проверочные листы.')
   replace('Файл 04','Файл 04 содержит неизменённые страницы рекомендуемого образца АОСР из приложения № 3 к составу исполнительной документации по приказу Минстроя России от 16.05.2023 № 344/пр. Заполните реквизиты объекта и участников, пункты 1–7, приложения и подписи по фактическим обстоятельствам. Освидетельствование оформите до выполнения последующих работ.')
   replace('Связь с дополнительным объёмом','Связь с дополнительным объёмом, журналом 08, фотоматериалами и согласованием 02 отразите в предусмотренных разделах акта и приложениях. Сохраните все графы и реквизиты исходного бланка. Источник: https://minjust.consultant.ru/files/47785, страницы 13–16.')
  d.save(p);changed=True
 if changed:canonical(p)

p1='Формы КС-2 и КС-3 находятся в файлах 01 и 02; журнал по форме КС-6а — в 06-zhurnal-ucheta-rabot-ks-6a.xls. Бланки XLS сохранены в опубликованном оформлении. Оперативный учёт объёмов и ссылок на подтверждения ведите отдельно в 06A-rabochiy-reestr-obemov.xlsx. Проверьте применимость форм по договору и учётной политике.\n'
p2='Файл 04-akt-skrytyh-rabot.pdf содержит исходные страницы рекомендуемого образца АОСР из приложения № 3 к приказу Минстроя России от 16.05.2023 № 344/пр. Бланк PDF предназначен для печати и заполнения; интерактивные поля отсутствуют. Заполните реквизиты, пункты 1–7, приложения и подписи по фактическим обстоятельствам. Сохраните графы и оформление исходного бланка.\n'
p4='Файл 31 содержит неизменённые страницы рекомендуемого образца АОСР из приложения № 3 к приказу Минстроя России № 344/пр. Файл 35 — форма общего журнала работ из приложения № 1 к приказу Минстроя России от 02.12.2022 № 1026/пр. Файл 36 — журнал результатов входной верификации из справочного приложения А ГОСТ 24297-2013; его применение определяйте по проекту и принятому порядку контроля. Эти PDF предназначены для печати и заполнения, интерактивные поля отсутствуют. Сохраните графы, реквизиты и оформление бланков.\n\nОперативные записи ведите отдельно в 35A-rabochiy-zhurnal-proizvodstva-rabot.xlsx и 36A-rabochiy-reestr-vhodnogo-kontrolya.xlsx. При переносе сведений в формы 35 и 36 заполните все предусмотренные графы по подтверждающим документам. В карточке 32 укажите реквизиты и связь с подготовленной исполнительной схемой; саму схему оформите по проекту и применимым требованиям.\n'
for sku,extra in [('P1',p1),('P2',p2),('P4',p4)]:
 p=W/sku/'00-START-HERE.txt';text=p.read_text().split('СОСТАВ АРХИВА',1)[0]
 if sku=='P4':
  old='Файл 31 содержит'
  if old in text:text=text.split(old,1)[0]
 marker='ИСХОДНЫЕ ФОРМЫ И РАБОЧИЕ РЕЕСТРЫ'
 if marker in text:text=text.split(marker,1)[0]
 for old,new in refs.items():text=text.replace(old,new)
 p.write_text(text.rstrip()+'\n\n'+marker+'\n'+extra+'\nСОСТАВ АРХИВА\n'+'\n'.join(sorted(x.name for x in p.parent.iterdir() if x.is_file()))+'\n')
p=W/'P3/00-START-HERE.txt';text=p.read_text()
old='4. Для применимых скрытых работ используйте 03-akt-skrytyh-rabot.docx. Выберите одну из пяти форм, заполните её по фактам и установите участников по применимости.'
new='4. Для скрытых работ по перечню объекта используйте 03-akt-skrytyh-rabot.pdf — неизменённые страницы рекомендуемого образца АОСР из приложения № 3 к приказу Минстроя России от 16.05.2023 № 344/пр. Это бланк для печати и заполнения; интерактивные поля отсутствуют. Заполните реквизиты, пункты 1–7, приложения и подписи по фактическим ролям участников. Сохраните все графы и оформление.'
if old in text:text=text.replace(old,new)
assert new in text, 'P3 original instruction differs'
text=text.replace('7 DOCX, 2 XLSX, 1 PDF и этот TXT: 11 файлов.','6 DOCX, 2 XLSX, 2 PDF и этот TXT: 11 файлов.')
marker='ПРИМЕНЕНИЕ АОСР ПО ВИДАМ РАБОТ'
if marker in text:text=text.split(marker,1)[0]
text=text.rstrip()+'\n\n'+marker+'\nОдин исходный бланк применяется к бетонированию, гидроизоляции, электромонтажу, отоплению и водоснабжению и иным скрытым работам по перечню объекта. В пункте 1 укажите конкретные работы, участок, оси и отметки; в пунктах 2–4 — проект, материалы, документы качества, исполнительные схемы и результаты испытаний, относящиеся к этому объёму. Укажите фактические даты, требования, решение о последующих работах и приложения. Проверьте участников, полномочия и подписи по предусмотренным в бланке ролям. Оформите освидетельствование до закрытия участка последующими работами. Источник бланка: https://minjust.consultant.ru/files/47785, страницы 13–16.\n'
p.write_text(text)

mapping={sku+'/'+old:sku+'/'+new for (sku,old),new in aux.items()}
writejson(A/'workbook-path-map.json',mapping)
references={r['file']:r for r in json.loads((A/'reference-manifest.json').read_text())}
qualifications=[]
for sku,name,source in forms:
 if source.suffix!='.pdf':continue
 ref=references[source.name]
 assert ref['source_page_pixels_unchanged'] and digest(source)==ref['sha256']
 qualifications.append({'sku':sku,'file':name,'sha256':digest(W/sku/name),'visual_status':'PASS','reference_url':ref['source_url'],'evidence':'reference-manifest.json: exact source page pixels preserved','pages':ref['pages'],'interactive_fields':False})
writejson(A/'qualified-buyer-originals.json',qualifications)
locks=[{'sku':'P1','member':name,'source':src,'sha256':digest(B/'sources'/src)} for name,src in [('01-ks-2.xls','KS-2-original.xls'),('02-ks-3.xls','KS-3-original.xls'),('06-zhurnal-ucheta-rabot-ks-6a.xls','KS-6a-original.xls')]]
locks += [{'sku':sku,'member':name,'source':str(source.relative_to(B)),'sha256':digest(source)} for sku,name,source in forms if source.suffix=='.pdf']
writejson(B/'original-form-lock.json',locks)
after={str(p.relative_to(W)):digest(p) for p in W.rglob('*') if p.is_file()}
for (sku,old),new in aux.items():
 assert before.get(sku+'/'+old,before.get(sku+'/'+new))==after[sku+'/'+new],('working register changed',sku,old)
report={'status':'ORIGINAL_PDF_REPLACEMENTS_APPLIED_NATIVE_OFFICE_PENDING','original_forms':locks,'working_registers_renamed_byte_identically':mapping,'guide_edits':changes,'files':len(after),'changed_files':[{'file':name,'before_sha256':before.get(name),'sha256':h} for name,h in after.items() if before.get(name)!=h],'removed_files':[name for name in before if name not in after],'native_office':'PENDING','publication':'NOT_PERFORMED'}
writejson(A/'applied-replacements.json',report)
print('APPLIED',len(forms),'original forms;',len(after),'working files;',len(report['changed_files']),'changed; native Office pending')
