#!/usr/bin/env python3
"""Inventory every current package member and record the owner's original-form comparison."""
from pathlib import Path
from zipfile import ZipFile
import json,hashlib,re
B=Path(__file__).resolve().parents[1]/'tools/candidates/remaining-batch-r3-20261018/form-originals-audit'
B.mkdir(exist_ok=True,parents=True)
sources=[
 ('/tmp/mb-r3/work','/tmp/mb-r3/audit-r3','R3_WIP_NOT_ACCEPTED'),
 ('/tmp/mb-r3/all-packages-extra','/tmp/mb-r3/audit-extra','RECORDED_RELEASE_MEMBER_SNAPSHOT')]
direct={
 ('P1','01-ks-2.xls'):('КС-2','https://www.consultant.ru/document/cons_doc_LAW_26303/dcaa7085e4a308d45f6b131e6506737ef9230c7c/','ks2-reference.pdf','NATIVE_PRINT_PENDING_LOCAL_FAIL','Группы реквизитов и восемь граф сохранены. В локальной печати три страницы вместо двух: итог первой страницы вынесен на отдельный лист. Исходный XLS сохранён без правок; подтверждения корректной native Excel печати нет.'),
 ('P1','02-ks-3.xls'):('КС-3','https://www.consultant.ru/document/cons_doc_LAW_26303/d3a70f222015da0dd6e786b0d839d57d0b6359cb/','ks3-reference.pdf','NATIVE_PRINT_PENDING_LOCAL_FAIL','Шесть граф, три периода стоимости, итоги и подписи сохранены. Локальная печать даёт второй пустой лист; эталонная форма помещается на одном. Исходный XLS сохранён без правок; native Excel не подтверждён.'),
 ('P2','04-akt-skrytyh-rabot.xlsx'):('АОСР, приложение 3 к приказу 344/пр','https://minjust.consultant.ru/files/47785','aosr-344-original.pdf','REPLACE_ORIGINAL_LAYOUT','Опубликованный сторонний XLSX сжат до двух страниц: уменьшены интервалы, шапка сокращена, отсутствует надпись о рекомендуемом образце. Официальный образец занимает четыре страницы. Совпадение состава полей не подтверждает сохранение оформления.'),
 ('P4','31-akt-osvidetelstvovaniya-skrytyh-rabot.xlsx'):('АОСР, приложение 3 к приказу 344/пр','https://minjust.consultant.ru/files/47785','aosr-344-original.pdf','REPLACE_ORIGINAL_LAYOUT','Точный дубликат P2/04; те же отличия от четырёхстраничного официального образца.'),
 ('P3','03-akt-skrytyh-rabot.docx'):('АОСР, приложение 3 к приказу 344/пр','https://minjust.consultant.ru/files/47785','aosr-344-original.pdf','REPLACE_ORIGINAL_LAYOUT','Одиннадцать страниц: вводная и пять переработанных двухстраничных актов. Добавлены фирменные колонтитулы, золотистые линии и названия видов работ в заголовках; сведения организованы таблицами, подписи размещены иначе. Все пять актов визуально отличаются от установленного образца. Новый конкретный дефект выявлен в ранее принятом файле.'),
 ('P4','35-obshiy-zhurnal-rabot.xlsx'):('Общий журнал, приложение 1 к приказу 1026/пр','https://minjust.consultant.ru/files/28915','general-journal-1026-original.pdf','REPLACE_ORIGINAL_LAYOUT','В пакете одна рабочая таблица с 11 графами и инструкция. Установленная форма содержит титульные сведения, участников, регистрацию и шесть разделов. Переименование рабочей таблицы не восполняет установленную форму.')}
analogs={
 ('P1','06-zhurnal-obemov.xlsx'):('КС-6а','https://www.consultant.ru/document/cons_doc_LAW_26303/dc9b2aa6e521cdef7e924813c565fbec7c69ca6b/','ks6a-reference.pdf','WORKING_REGISTER_NOT_KS6A','Таблица оперативных объёмов с 10 графами отличается от КС-6а: нет титульного листа, расценок, стоимости и помесячной структуры 46 граф. Включать неизменённую КС-6а при её использовании; рабочий журнал учитывать отдельным вспомогательным инструментом.'),
 ('P4','36-vhodnoy-kontrol.xlsx'):('Справочная форма журнала верификации, приложение А ГОСТ 24297-2013','https://base.garant.ru/70651318/53f89421bbdaf741eb2d1ecc4ddb4c33/',None,'REFERENCE_DIFFERS_APPLICABILITY_REQUIRED','В пакете 10 граф в другом порядке; в справочном образце 11. Отсутствуют отдельные поля транспорта, упаковки, даты изготовления, места и даты отбора образца. Если используется данный нормативный образец, включать его исходную форму. Справочный статус не выдаётся за универсальную обязательность.'),
 ('P4','32-kartochka-ispolnitelnoy-shemy.docx'):('Карточка учёта исполнительной схемы',None,None,'PROJECT_DRAWING_REFERENCE_REQUIRED','Документ представляет карточку сведений, а не готовый чертёж конкретного объекта. Для сопоставления самой схемы необходимы проект, измерения и применимые требования к исполнительной графике. Не квалифицировать карточку как воспроизведение установленной исполнительной схемы.')}
rows=[]
qualified=json.loads((B/'qualified-buyer-originals.json').read_text())
for q in qualified:
 direct[(q['sku'],q['file'])]=('Исходный установленный или справочный бланк',q['reference_url'],None,'ORIGINAL_PAGES_IDENTICAL','Исходные страницы выделены без переработки оформления; визуальные пиксели и размеры страниц совпадают с опубликованным источником. PDF для печати и заполнения, без интерактивных полей.')
direct[('P1','06-zhurnal-ucheta-rabot-ks-6a.xls')]=('КС-6а','https://www.consultant.ru/document/cons_doc_LAW_26303/dc9b2aa6e521cdef7e924813c565fbec7c69ca6b/','ks6a-reference.pdf','NATIVE_PRINT_PENDING','Исходный опубликованный XLS сохранён побайтно. Контроль обычного открытия и печати в native Excel ожидается.')
for old,new in json.loads((B/'workbook-path-map.json').read_text()).items():
 sku,name=old.split('/');_,dest=new.split('/')
 analogs[(sku,dest)]=('Вспомогательный рабочий реестр',None,None,'AUXILIARY_REGISTER_PRESERVED','Содержимое книги сохранено побайтно относительно проверяемой рабочей редакции; исходный нормативный бланк включён отдельно и не подменяется этой таблицей.')
for root,audit,role in sources:
 root=Path(root);audit=Path(audit)
 for folder in sorted(root.iterdir()):
  if role=='RECORDED_RELEASE_MEMBER_SNAPSHOT' and (Path('/tmp/mb-r3/work')/folder.name).exists():continue
  text={f['file']:f['rows'] for f in json.loads((audit/(folder.name+'.json')).read_text())}
  for p in sorted(folder.iterdir()):
   if not p.is_file():continue
   k=(folder.name,p.name);tr=text.get(p.name,[]);title=tr[0]['text'][:180] if tr else ''
   r={'sku':folder.name,'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'snapshot_role':role,'title':title}
   comparison=direct.get(k) or analogs.get(k)
   if comparison:
    r.update(dict(zip(['reference_name','reference_url','reference_pdf','decision','finding'],comparison)))
    r['classification']='ESTABLISHED_FORM' if k in direct else 'RELATED_STANDARD_OR_PROJECT_RECORD'
   elif re.search(r'algoritm|slovar|pamyatka|chek|checklist|krasnye|tipovye|sroki-hraneniya|razbor|reglament|markery|proverochnyy|sravnitelnaya|vstavnye|poryadok|00-',p.name,re.I) and k!=('P7','04-poryadok-priemki.docx'):
    r.update(classification='GUIDE_CHECKLIST_OR_INSTRUCTION',decision='NOT_AN_ESTABLISHED_FORM')
   elif p.suffix in {'.docx','.xlsx','.xls'} and re.search(r'akt|zhurnal|opis|reestr|dogovor|soglash|protokol|shem|prikaz|raschet|grafik|plan|pismo|uvedom|otvet|pretenz|zapros|trebov|zayavlen|preduprezh|karta|perechen-rabot|vozrazhen|izmenenie-srokov|soglasovanie|poryadok-priemki',p.name,re.I):
    r.update(classification='AUTHOR_CONTRACT_FORM_OR_WORKING_REGISTER',decision='NO_IDENTIFIED_UNIFIED_FORM_CLAIM',finding='Собственная договорная форма или рабочий учёт. Для конкретного объекта сверять с согласованной договорной формой. Не обозначать как неизменённый государственный бланк.')
   else:r.update(classification='GUIDE_CHECKLIST_OR_INSTRUCTION',decision='NOT_AN_ESTABLISHED_FORM')
   rows.append(r)
report={'status':'REPLACEMENTS_APPLIED_NATIVE_OFFICE_PENDING','owner_rule':'Унифицированные и установленные образцы сохраняются без переработки оформления. Проверяется визуальное воспроизведение, а не только реквизиты или SHA стороннего файла.','scope_files':len(rows),'scope_packages':sorted({x['sku'] for x in rows}),'established_form_files':sum(x['classification']=='ESTABLISHED_FORM' for x in rows),'related_records':sum(x['classification']=='RELATED_STANDARD_OR_PROJECT_RECORD' for x in rows),'visual_engine':'Official PDF source-page pixels identical; editable original XLS native Microsoft Excel print qualification pending.','release_member_evidence':{'P3':'https://github.com/pmgpt12-arch/marzhavbetone.ru/issues/291#issuecomment-6209248579','other_release_snapshots':'Existing recorded repository archives; no new production download or production mutation performed.'},'files':rows}
(B/'forms-register.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('INVENTORY',len(rows),'PACKAGES',len(report['scope_packages']),'DIRECT',len(direct),'RELATED',len(analogs))

