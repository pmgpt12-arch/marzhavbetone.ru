"""Scoped substantive edits to four free DOCX sources; preserve other package parts."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import json,hashlib,subprocess,io
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';S=Q.parent/'remaining-audit-20261022/free-sources/downloads'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';REL='{http://schemas.openxmlformats.org/package/2006/relationships}';RR='http://schemas.openxmlformats.org/officeDocument/2006/relationships';ns={'w':W[1:-1]}
LAW743='https://www.consultant.ru/document/cons_doc_LAW_9027/b48c040fb20b324efb339e89ad832027d4b5d97a/'
LAW402='https://www.consultant.ru/document/cons_doc_LAW_122855/b24121ba7152f33673608559f2ca844ef5b6a74c/'
def txt(p):return ''.join(p.xpath('.//w:t/text()',namespaces=ns))
def settext(p,text):
 for x in list(p):
  if x.tag!=W+'pPr':p.remove(x)
 E.SubElement(E.SubElement(p,W+'r'),W+'t').text=text
def pnew(body,text,heading=False):
 p=E.Element(W+'p')
 if heading:
  pr=E.SubElement(p,W+'pPr');E.SubElement(pr,W+'pStyle',{W+'val':'Heading2'});E.SubElement(pr,W+'keepNext')
 E.SubElement(E.SubElement(p,W+'r'),W+'t').text=text
 sect=body.find(W+'sectPr');body.insert(list(body).index(sect)if sect is not None else len(body),p);return p
def br(p):
 pp=p.find(W+'pPr')
 if pp is None:pp=E.Element(W+'pPr');p.insert(0,pp)
 if pp.find(W+'pageBreakBefore')is None:E.SubElement(pp,W+'pageBreakBefore')
def link(body,rels,label,url):
 used={x.get('Id')for x in rels};i=1
 while 'rIdNspReview'+str(i)in used:i+=1
 ident='rIdNspReview'+str(i);E.SubElement(rels,REL+'Relationship',Id=ident,Type=RR+'/hyperlink',Target=url,TargetMode='External')
 p=pnew(body,'');p.remove(p.find(W+'r'));h=E.SubElement(p,W+'hyperlink',{'{'+RR+'}id':ident});r=E.SubElement(h,W+'r');rp=E.SubElement(r,W+'rPr');E.SubElement(rp,W+'color',{W+'val':'1F4E79'});E.SubElement(rp,W+'u',{W+'val':'single'});E.SubElement(r,W+'t').text=label
specs=[
 ('vozvrat-ks','04-poryadok-vnutrenney-proverki.docx',[
 ('Проверяет наличие всех подписей и печатей.','Проверяет подписи уполномоченных представителей и основания их полномочий. Необходимость печати сверяет по применимым требованиям и договору.'),
 ('Подписывает КС-3.','Оформляет внутреннюю визу, если она предусмотрена принятым порядком. Самостоятельного универсального требования подписи бухгалтера на КС-3 нет.'),
 ('Руководитель организации подписывает КС-2, КС-3.','КС-2 и КС-3 подписывают уполномоченные представители организации по принятой форме и подтверждённым полномочиям. Затем комплект направляют заказчику.'),
 ('Составляется акт передачи комплекта КС','Состав передачи фиксируется описью и сопроводительным письмом; акт передачи оформляют, если он предусмотрен договором или согласован сторонами.'),
 ('Комплект передается под расписку','Передайте комплект по договорному каналу. Сохраните состав и версию переданных документов, адресата, дату и доказательства доставки; одного подтверждения отправления недостаточно для всех ситуаций.'),
 ('Нормативный срок','Рекомендуемый внутренний срок')]),
 ('dop-raboty','01-checklist-do-nachala-doprabot.docx',[
 ('Перед началом любых допработ ответьте','Перед началом допработ проверьте условия ниже. Фотографии и внутренние записи помогают сохранить доказательства; обязанности по уведомлению и приостановке определяются отдельно по договору и закону.')]),
 ('dop-raboty','02-shema-fiksacii-porucheniya.docx',[
 ('Что НЕЛЬЗЯ делать','Обычный порядок до согласования'),
 ('Начинать работу без письменного подтверждения стоимости','До начала согласуйте объём, цену и сроки. Отдельно проверьте, нет ли оснований для немедленных действий по п. 4 ст. 743 ГК РФ.'),
 ('Отправлять КС-2 по допработам до подписания','Не подменяйте актом согласование цены. Если работы уже выполнены, сохраните доказательства объёма и сдачи; отсутствие соглашения само по себе не является основанием скрывать фактически выполненные работы или прекращать документирование.')]),
 ('dop-raboty','03-shablon-uvedomleniya.docx',[
 ('Содержание поручения:','Содержание поручения и основание дополнительности работ (неучтённый объём, изменение проекта или иное основание):'),
 ('До согласования условий просим подтвердить','Просим сообщить решение о необходимости работ, увеличении стоимости и изменении сроков. Применимый срок ответа: [10 дней по п. 3 ст. 743 ГК РФ / иной срок, установленный законом или пунктом договора: указать основание].'),
 ('Если ответ не поступит в указанный срок','При отсутствии ответа в применимый срок соответствующие работы подлежат приостановке в порядке п. 3 ст. 743 ГК РФ. О фактической дате и затрагиваемых работах сообщим отдельно. Неотложные обстоятельства, требующие немедленных действий в интересах заказчика: [нет / описание угрозы, действий и подтверждений].')])
]
records=[]
for pack,name,replacements in specs:
 with ZipFile(S/(pack+'.zip'))as arc:raw=arc.read(name)
 dest=O/'additional-candidates/free'/pack/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(io.BytesIO(raw))as z:
  root=E.fromstring(z.read('word/document.xml'));body=root.find(W+'body');rels=E.fromstring(z.read('word/_rels/document.xml.rels'));paras=root.xpath('//w:p',namespaces=ns)
  for prefix,new in replacements:
   hits=[p for p in paras if txt(p).startswith(prefix)];assert len(hits)==1,(name,prefix,len(hits));settext(hits[0],new)
  for p in paras:
   for t in p.xpath('.//w:t',namespaces=ns):
    if t.text:t.text=t.text.replace('🔗 ','').replace('🔗','')
  if pack=='vozvrat-ks':
   pnew(body,'Как применять внутренние сроки',True)
   pnew(body,'Один рабочий день на этап и четыре дня в сумме — организационный ориентир этого порядка. Утвердите ответственных и реальные сроки внутри организации. Этот график не является сроком из закона и не продлевает срок сдачи документов по договору.')
   pnew(body,'Проверяйте КС-2 и КС-3 за один и тот же период, состав работ, накопительные графы и НДС. КС-6а — журнал учёта выполненных работ; он не заменяет общий журнал работ. Состав приложений определяется работами, проектом, договором и применимыми требованиями.')
   link(body,rels,'402-ФЗ, ст. 9, ч. 2 и 4 — реквизиты, подписи и выбор формы',LAW402)
   pnew(body,'Контроль: до отправки сверьте опись и подписи, после отправки сохраните подтверждение доставки. При возврате запросите письменные замечания по конкретным позициям, устраните обоснованные ошибки и зафиксируйте повторную передачу.')
  else:
   if name.startswith('03-'):
    guide=next(p for p in paras if txt(p)=='Как направить уведомление');br(guide)
    guide.addnext(E.fromstring(('<w:p xmlns:w="'+ns['w']+'"><w:r><w:t>Пояснение покупателю: в отправляемое письмо включайте текст до этого раздела. Подсказки, следующие страницы и сведения о продуктах заказчику не направляются.</w:t></w:r></w:p>').encode()))
   pnew(body,'Развилка по дополнительным работам',True)
   pnew(body,'Для неучтённых в технической документации работ, увеличивающих сметную стоимость, проверьте порядок п. 3 ст. 743 ГК РФ: уведомление заказчика, применимый срок ответа и приостановку соответствующих работ при отсутствии ответа. Обычный срок ответа — десять дней; закон или договор могут устанавливать иной.')
   pnew(body,'Нарушение обязанности по п. 3 создаёт риск утраты права требовать оплату допработ и связанные убытки. Исключение по п. 4 требует доказать необходимость немедленных действий в интересах заказчика, например для предотвращения гибели или повреждения объекта. Сохраните хронологию угрозы, акт, фото и обоснование выполненных неотложных действий.')
   pnew(body,'Если работы уже выполнены, соберите подтверждения уведомления, согласования, необходимости, объёма и сдачи. Претензионную позицию выбирайте по фактам; один подписанный акт не заменяет проверку оснований оплаты.')
   link(body,rels,'ГК РФ, ст. 743, п. 3–4 — уведомление, приостановка и неотложные действия',LAW743)
   pnew(body,'Пример расчёта: 150 м² × 850 руб. = 127 500 руб.; ещё 20 шт. × 1 000 руб. дают общий итог 147 500 руб. В реестре 04 неполная или нечисловая строка должна требовать проверки. Укажите источник объёма, цену и единицы, затем подтвердите согласование и сдачу.')
  pnew(body,'Поддержка: nastoronepodryadchika@yandex.ru. В теме укажите FREE-'+pack+' и имя файла; в сообщении — пункт или ячейку, пример и ожидаемый результат. Приложите копию без конфиденциальных данных.')
  updates={'word/document.xml':E.tostring(root,encoding='utf-8',xml_declaration=True,standalone=True),'word/_rels/document.xml.rels':E.tostring(rels,encoding='utf-8',xml_declaration=True,standalone=True)}
  with ZipFile(dest,'w',ZIP_DEFLATED)as out:
   for info in z.infolist():out.writestr(deepcopy(info),updates.get(info.filename,z.read(info.filename)))
  with ZipFile(dest)as out:
   assert out.testzip()is None
   for n in z.namelist():
    if n not in updates:assert out.read(n)==z.read(n)
    if n.endswith(('.xml','.rels')):E.fromstring(out.read(n))
  record={'archive':'downloads/'+pack+'.zip','path':'free/'+pack+'/'+name,'base_sha256':hashlib.sha256(raw).hexdigest(),'new_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'replacements':[x[0]for x in replacements],'native_office':'PENDING','other_parts_byte_exact':True,'sources':[LAW402]if pack=='vozvrat-ks'else[LAW743]}
  records.append(record);print('BUILT',pack,name,flush=True)
  outdir=O/'rendered-free-content'/pack/dest.stem
  subprocess.run(['/home/denis/projects/nsp-audit-fixes-20261021/.render-venv/bin/python','/home/denis/projects/nsp-audit-fixes-20261021/render_docx.py',str(dest),'--output_dir',str(outdir),'--emit_pdf'],check=True,capture_output=True,text=True,timeout=90)
  record['lo_pdf']=str(outdir/(dest.stem+'.pdf'));record['render_pages']=len(list(outdir.glob('page-*.png')))
(O/'FREE_CONTENT_DOCX_MANIFEST.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('RENDERED',[(x['path'],x['render_pages'])for x in records],flush=True)
