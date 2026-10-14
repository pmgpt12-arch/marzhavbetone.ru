from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
import hashlib,json,subprocess,shutil,datetime
R=Path('/home/denis/projects/mb001-p11-normative-delta-20261013')
C=R/'tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami'
E=C.parent/'p11-f02-f03-20261014'
BASE='cfbc4e3edcf438250bac98a2df04133d96bb27b3'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (E/'acceptance.json').exists(),'Already finalized: reuse evidence'
assert subprocess.run(['git','-C',str(R),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=4).stdout.strip()==BASE
inspection=json.loads((E/'native-inspection.json').read_text())
assert len(inspection['records'])==3 and [r['pages'] for r in inspection['records']]==[3,2,2]
for rec in inspection['records']:
 assert sha((C/rec['name']).read_bytes())==rec['docx_sha256']
 for img in rec['pngs']:assert sha((E/img['path']).read_bytes())==img['sha256']
 # The exact PDF reviewed as page PNGs becomes the PDF candidate; no second renderer or rerun.
 if rec['name'].startswith(('51-','55-')):
  pdf=E/'native'/rec['tag']/'output.pdf';target=(C/rec['name']).with_suffix('.pdf')
  before=target.read_bytes();expected=subprocess.run(['git','-C',str(R),'show',BASE+':'+str(target.relative_to(R))],capture_output=True,check=True,timeout=6).stdout
  assert before==expected;assert sha(pdf.read_bytes())==rec['pdf_sha256'];target.write_bytes(pdf.read_bytes());assert sha(target.read_bytes())==rec['pdf_sha256']
  with ZipFile(C/rec['name']) as z:tree=ET.fromstring(z.read('word/document.xml'))
  text='\n\n'.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in tree.find(W+'body').findall(W+'p'))+'\n'
  target.with_suffix('.source-text.txt').write_text(text)
cmd=['python3',str(R/'tools/test_p11_f02_f03_regression.py'),'--root',str(R),'--report',str(E/'regression-current.json')]
reg=subprocess.run(cmd,capture_output=True,text=True,timeout=12);(E/'regression.stdout').write_text(reg.stdout+'\nSTDERR\n'+reg.stderr);assert reg.returncode==0
checks=json.loads((E/'regression-current.json').read_text());assert len(checks['positive'])==13 and len(checks['negative_mutations_detected'])==15
names=['00-START-HERE.txt','50-slovar-poley-raschet-metrami.docx','51-algoritm-raschet-metrami.pdf','52-chek-list-raschet-metrami.docx','53-zapros-status-obekta.docx','54-zapros-sostoyanie-escrow.docx','55-pamyatka-punkt-ustupki-escrow.pdf']
manifest=[]
for name in names:
 p=C/name;old=subprocess.run(['git','-C',str(R),'show',BASE+':'+str(p.relative_to(R))],capture_output=True,check=True,timeout=5).stdout;data=p.read_bytes()
 changed=name.startswith(('51-','52-','55-'))
 assert (data!=old)==changed
 manifest.append({'name':name,'path':str(p.relative_to(R)),'sha256':sha(data),'bytes':len(data),'before_sha256':sha(old),'changed':changed,'role':'isolated_candidate_NOT_formal_nomination'})
assert len(manifest)==7 and sum(x['changed'] for x in manifest)==3
(E/'input-manifest.json').write_text(json.dumps({'base_commit':BASE,'files':manifest,'formal_nomination':'OPEN'},ensure_ascii=False,indent=2)+'\n')
shutil.copy2('/home/denis/.local/state/p11-f02-f03-recovery-20261014.json',E/'recovery.json')
shutil.copy2('/home/denis/.local/state/p11-f02-f03-inspect-20261014.py',E/'inspect.py')
shutil.copy2(__file__,E/'finalize.py')
scenarios=[
 {'id':'F02_POST_TRANSFER','input':'ДДУ зарегистрирован и оплачен; объект передан по акту 11.10.2026; уступка права на получение объекта предлагается 14.10.2026','expected':'STOP_DETERMINE_DIFFERENT_TRANSACTION','evidence':'51: шаг 1; 52: раздел 1; 55: граница применения','author_read_result':'Все три документа требуют остановки, хотя цена оплачена'},
 {'id':'F02_UNKNOWN_TRANSFER','input':'ДДУ зарегистрирован, но документы о стадии передачи не предоставлены','expected':'STOP_REQUEST_TRANSFER_STATUS','author_read_result':'В каждом документе прямо предусмотрен СТОП при неподтверждённой стадии'},
 {'id':'F02_COMMISSIONING_ONLY','input':'Дом введён, акт передачи сторонами не подписан; остальные условия проверяются отдельно','expected':'DO_NOT_CONFUSE_COMMISSIONING_WITH_TRANSFER','author_read_result':'Ввод не приравнен к передаче; автоматического разрешения сделки нет'},
 {'id':'F03_TWO_FLAGS','input':'Перенос ввода и истекающее разрешение; правовая оценка и меры защиты ещё не подтверждены','expected':'STOP_IN_51_AND_52','author_read_result':'Оба документа используют дословно одинаковое правило остановки'},
 {'id':'F03_LAWYER_ONLY','input':'Два флага; юрист просмотрел документы, но нет согласованных мер защиты и письменного решения руководителя','expected':'STOP_REMAINS','author_read_result':'Наличие юриста или обеспечения само по себе не разрешает подписать'},
 {'id':'F03_LEGAL_OBSTACLE','input':'Руководитель готов подписать, но выявленное правовое препятствие не устранено','expected':'STOP_REMAINS','author_read_result':'Устранение правовых препятствий указано как обязательное условие'}]
(E/'author-scenarios.json').write_text(json.dumps({'scope':'AUTHOR_DESK_REVIEW_NOT_INDEPENDENT_BUYER','scenarios':scenarios,'scenario_count':len(scenarios)},ensure_ascii=False,indent=2)+'\n')
review={'51':['All three pages read; new boundary and stop rule visible; no clipping or overlap. Step 5 continues on next page with heading and opening line kept together.'], '52':['Both pages read; boundary checkbox visible on page 1; unified stop/resume paragraph and all red-flag rows visible on page 2. Source blue headings/italic subtitle remain.'], '55':['Both pages read; transfer-boundary section and final paragraph fully visible; no clipping or orphan page. Source blue title rule remains.']}
accept={'id':'P11-F02-F03-AUTHOR-DELTA-20261014','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_commit':BASE,'source_review_id':5507097044,'scope':'F02_F03_IMPLEMENTATION_TECHNICAL_NATIVE_AND_AUTHOR_REVIEW_ONLY','changes':'3 editable DOCX; 2 PDF exported by Microsoft Word; 2 synchronized text extracts','native_job':inspection['job'],'native_raw_report_sha256':inspection['raw_report_sha256'],'native_input_passed':3,'native_pages':7,'rendered_pages_examined':7,'positive_checks':13,'negative_mutations_detected':15,'author_desk_scenarios':6,'visual_review':review,'F02':'IMPLEMENTED_AUTHOR_CHECKED_PENDING_INDEPENDENT_ACCEPTANCE','F03':'IMPLEMENTED_AUTHOR_CHECKED_PENDING_INDEPENDENT_ACCEPTANCE','F01_and_START_HERE':'ACCEPTED_PRIOR_EXACT_SHA_UNCHANGED','normative_source':'214-ФЗ ч.2 ст.11; ConsultantPlus source recorded separately','independent_legal_signoff':'NOT_RUN_FOR_THIS_DELTA','independent_buyer_signoff':'NOT_RUN_FOR_THIS_DELTA','remaining':['P11+T6 completeness/disposition','formal nominations/release manifest','brand-style residual','independent F02/F03 delta review','full G1-G8'],'G1_G8':'0/13','release':'HOLD','product_source_roots_modified':False,'prices_sku_checkout_vpn_production_modified':False,'native_replays':0,'paid_model_calls':0,'ci_integration':'Regression command exists; mandatory CI registration not claimed'}
(E/'acceptance.json').write_text(json.dumps(accept,ensure_ascii=False,indent=2)+'\n')
(E/'REVIEW.md').write_text('# P11 — F02/F03: проверенная авторская дельта\n\nБаза: `'+BASE+'`. Изменены алгоритм 51, чек-лист 52 и памятка 55; исходные продукты и production не изменены.\n\nЧасть 2 статьи 11 Закона №214-ФЗ: проверяется регистрация ДДУ и отсутствие передачи объекта; передача оформлена или стадия неизвестна — остановка до определения применимой сделки. Два красных флага: одинаковое правило СТОП, проверки мер защиты и письменного решения руководителя. Это правило работы с рисками комплекта, а не установленный законом числовой порог.\n\nНативный Word: 3/3, 7 страниц; каждая страница просмотрена. Для PDF 51/55 использованы точные проверенные native-выходы, не непроверенные конвертации. Сохранены 13 положительных проверок, 15 отрицательных мутаций, 6 авторских desk-сценариев.\n\nНезависимая приёмка этой дельты не выдана. Границы: оформление, P11+T6, номинации, полный buyer/legal/G1–G8 и release остаются OPEN/HOLD. Старые F01 и START HERE не затронуты.\n\nПовторяемый тест: `python tools/test_p11_f02_f03_regression.py --root .`. Совпадающий exact SHA + native job + scope использовать повторно; не перезапускать Word из-за новой сессии.\n')
files=[]
for p in sorted(E.rglob('*')):
 if p.is_file():files.append({'path':str(p.relative_to(E)),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size})
(E/'evidence-manifest.json').write_text(json.dumps({'files':files,'excludes':'this self-referential manifest','all_paths_relative_to_evidence_root':True},ensure_ascii=False,indent=2)+'\n')
assert all(sha((E/x['path']).read_bytes())==x['sha256'] for x in files)
print(json.dumps({'status':'FINAL_EVIDENCE_VERIFIED_NOT_COMMITTED','evidence_files':len(files),'acceptance_sha256':sha((E/'acceptance.json').read_bytes()),'manifest_sha256':sha((E/'input-manifest.json').read_bytes()),'buyer_files_changed':3,'native':3,'pages':7},ensure_ascii=False))
