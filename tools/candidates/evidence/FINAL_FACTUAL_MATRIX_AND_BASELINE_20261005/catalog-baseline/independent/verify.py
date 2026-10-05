"""Independent review of frozen baseline structural observations, not author audit execution."""
from pathlib import Path
import json,hashlib,subprocess,zipfile,io,binascii,collections,xml.etree.ElementTree as E,posixpath,urllib.parse,re,time,datetime,sys
O=Path(__file__).resolve().parent
P=O.parent/'catalog-next-queue-20261005-recovery'
S='/home/denis/projects/marzhavbetone.ru'
PIN='264d75a06d59de82602dc1bcef347913c44cc648'
start=time.monotonic();checks=[];errors=[];files=[];modules=[]
def digest(b):return hashlib.sha256(b).hexdigest()
def check(ok,label,**context):
 checks.append(label)
 if not ok:errors.append(dict(check=label,**context))
def git(*a):return subprocess.check_output(['git','-C',S,*a],timeout=15)
def save(name,data):(O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def target_part(relname,target):
 # Derive source URI independently by removing /_rels/ and .rels.
 if relname=='_rels/.rels':source=''
 else:
  folder,tail=relname.rsplit('/_rels/',1) if '/_rels/' in relname else ('',relname.removeprefix('_rels/'))
  source=posixpath.join(folder,tail.removesuffix('.rels'))
 parsed=urllib.parse.urlsplit(target)
 decoded=urllib.parse.unquote(parsed.path)
 return posixpath.normpath(decoded.lstrip('/') if decoded.startswith('/') else posixpath.join(posixpath.dirname(source),decoded))
passport=json.loads((O/'passport.json').read_text())
for p,h in passport['input_files'].items():check(digest(Path(p).read_bytes())==h,'frozen_input_hash',path=p)
ready=json.loads((P/'POOL_READY.json').read_text());pool=json.loads((P/'pool-receipt.json').read_text())
check(pool['source_sha']==ready['source_sha']==PIN,'pool_source_sha')
check(ready['pool_receipt_sha256']==digest((P/'pool-receipt.json').read_bytes()),'READY_receipt_hash')
tasks=json.loads((P/'next-atomic-passports.json').read_text())['tasks']
expected={'p4':(23,19,13,6),'p8':(11,10,8,2),'p9':(10,9,8,1),'p11':(7,4,4,0)}
for task in tasks:
 sku=task['task_id'].split('-')[2];A=Path(task['output_dir'])
 worker=next(w for w in pool['workers'] if w['task']==task['task_id'])
 receipt=json.loads((A/'receipt.json').read_text());observed=json.loads((A/'file-observations.json').read_text())
 check(worker['exit_code']==0 and worker['receipt']==receipt,'actual_worker_receipt',sku=sku)
 check(receipt['file_observations_sha256']==digest((A/'file-observations.json').read_bytes()),'frozen_observation_hash',sku=sku)
 paths=[i['path'] for i in task['required_inputs']]
 check(len(paths)==len(set(paths)) and paths==[f['path'] for f in observed],'exact_membership_order',sku=sku)
 check(set(paths)==set(receipt['before_sha256'])==set(receipt['after_sha256']),'exact_receipt_membership',sku=sku)
 bypath={f['path']:f for f in observed};counts=collections.Counter(Path(p).suffix for p in paths)
 actual=(len(paths),counts['.docx']+counts['.xlsx'],counts['.docx'],counts['.xlsx'])
 check(actual==expected[sku],'module_scope_counts',sku=sku,actual=actual)
 for item in task['required_inputs']:
  path=item['path'];a=bypath[path];raw=git('show',PIN+':'+path);h=digest(raw)
  check(h==item['sha256']==a['sha256']==receipt['before_sha256'][path]==receipt['after_sha256'][path]==digest((A/'exact-buyers'/item['relative_name']).read_bytes()),'source_manifest_copy_hashes',path=path)
  check(git('rev-parse',PIN+':'+path).decode().strip()==item['git_blob'] and len(raw)==item['size']==a['bytes'],'git_blob_and_size',path=path)
  f={'sku':sku,'path':path,'sha256':h,'git_blob':item['git_blob'],'extension':Path(path).suffix}
  if f['extension'] not in ('.docx','.xlsx'):
   check(a['status']=='NOT_APPLICABLE_NON_OOXML','non_OOXML_applicability',path=path)
   f['scope']='HASH_AND_APPLICABILITY_ONLY';files.append(f);continue
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   infos=z.infolist();names=[i.filename for i in infos];parts=set(names);xml={}
   duplicates=[n for n,c in collections.Counter(names).items() if c>1]
   check(not duplicates and duplicates==a['duplicate_parts'],'duplicate_ZIP_entries',path=path)
   crc_failed=[]
   for inf in infos:
    b=z.read(inf)
    if binascii.crc32(b)&0xffffffff != inf.CRC:crc_failed.append(inf.filename)
    if inf.filename.endswith(('.xml','.rels')):
     try:xml[inf.filename]=E.fromstring(b)
     except E.ParseError as exc:check(False,'XML_parse',path=path,part=inf.filename,error=str(exc))
   check(not crc_failed and a['zip_crc_test'] is None,'every_ZIP_member_CRC',path=path)
   check(len(xml)==a['xml_parts_parsed'] and len(infos)==a['zip_parts'],'XML_and_part_counts',path=path)
   ct=xml.get('[Content_Types].xml');check(ct is not None,'content_types_present',path=path)
   if ct is not None:
    defaults={x.attrib['Extension'] for x in ct if x.tag.endswith('}Default')}
    overrides={urllib.parse.unquote(x.attrib['PartName']).lstrip('/') for x in ct if x.tag.endswith('}Override')}
    absent=sorted(overrides-parts)
    uncovered=[n for n in names if not n.endswith('/') and n!='[Content_Types].xml' and n not in overrides and n.rsplit('.',1)[-1] not in defaults]
    check(not absent and not uncovered and uncovered==a['content_type_coverage_missing'],'content_type_coverage_and_override_targets',path=path,absent=absent,uncovered=uncovered)
   relationship_count=0;external=[];targets=[];unresolved=[]
   for part,root in xml.items():
    if not part.endswith('.rels'):continue
    rels=list(root);ids=[x.attrib.get('Id') for x in rels]
    check(all(ids) and len(set(ids))==len(ids),'relationship_ID_uniqueness',path=path,part=part)
    for rel in rels:
     relationship_count+=1;target=rel.attrib.get('Target')
     check(bool(target),'relationship_target_attribute',path=path,part=part)
     if not target:continue
     if rel.attrib.get('TargetMode')=='External':
      external.append({'part':part,'id':rel.attrib['Id'],'target':target});continue
     resolved=target_part(part,target);targets.append({'relationship_part':part,'id':rel.attrib['Id'],'literal':target,'resolved_part':resolved})
     if resolved not in parts or resolved.startswith('../'):unresolved.append(targets[-1])
   check(not unresolved,'all_internal_relationship_targets',path=path,unresolved=unresolved)
   check(relationship_count==a['relationships_checked'] and external==[{k:v for k,v in x.items() if k!='scope'} for x in a['external_relationships']],'relationship_and_external_counts',path=path)
   tokens=[(part,ordinal) for part,root in xml.items() for ordinal,node in enumerate(root.iter(),1) if re.search(r'#{2,}',node.text or '')]
   check(len(tokens)==len(a['stored_hash_token_signals'])==0,'stored_hash_token_count',path=path)
   f.update(zip_parts=len(infos),xml_parts=len(xml),relationship_count=relationship_count,internal_relationship_targets=targets,external_relationship_count=len(external),CRC_all_members=True)
   if f['extension']=='.docx':
    check('word/document.xml' in xml and a['docx_schema']['main_document_present'] is True,'DOCX_main_document_actually_present',path=path)
    paragraphs=sum(n.tag=='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p' for part,root in xml.items() if part.startswith('word/') for n in root.iter())
    check(paragraphs==a['docx_schema']['paragraphs'],'DOCX_stored_paragraph_count',path=path)
    f.update(main_document_present=True,paragraphs=paragraphs)
   else:
    ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}';rid='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    workbook=xml.get('xl/workbook.xml');rels=xml.get('xl/_rels/workbook.xml.rels')
    check(workbook is not None and rels is not None,'XLSX_workbook_and_relationships_present',path=path)
    relmap={x.attrib['Id']:x for x in rels};linked=[];sheets=[]
    for sheet in workbook.findall(ns+'sheets/'+ns+'sheet'):
     rel=relmap.get(sheet.attrib[rid]);check(rel is not None,'workbook_sheet_relation_exists',path=path)
     if rel is None:continue
     resolved=target_part('xl/_rels/workbook.xml.rels',rel.attrib['Target'])
     check(rel.attrib.get('Type','').endswith('/worksheet') and resolved in xml,'workbook_sheet_targets_worksheet',path=path,part=resolved)
     linked.append(resolved);root=xml[resolved];cells=root.findall(ns+'sheetData/'+ns+'row/'+ns+'c')
     formulas=sum(c.find(ns+'f') is not None for c in cells)
     sheets.append({'part':resolved,'stored_cells':len(cells),'formula_cells':formulas})
    authored=a['xlsx_schema'];actual_worksheets={p for p,r in xml.items() if r.tag==ns+'worksheet'}
    check(set(linked)==actual_worksheets=={x['part'] for x in authored['sheets']} and len(linked)==len(set(linked)),'all_actual_workbook_worksheet_parts_covered',path=path,linked=linked)
    check(sorted(sheets,key=lambda x:x['part'])==sorted(authored['sheets'],key=lambda x:x['part']),'linked_worksheet_cell_formula_counts',path=path)
    check(sum(x['stored_cells'] for x in sheets)==authored['cells'] and sum(x['formula_cells'] for x in sheets)==authored['formula_cells'],'workbook_cell_formula_totals',path=path)
    f.update(workbook_linked_sheets=sheets)
   check(not a['issues'],'author_issue_signals_zero',path=path)
  check(digest(git('show',PIN+':'+path))==h==digest((A/'exact-buyers'/item['relative_name']).read_bytes()),'postreview_source_and_copy_unchanged',path=path)
  files.append(f)
 modules.append({'sku':sku,'eligible':actual[0],'ooxml':actual[1],'docx':actual[2],'xlsx':actual[3],'non_ooxml':actual[0]-actual[1]})
save('independent-file-facts.json',files)
receipt={'status':'ACCEPT_SCOPED_BASELINE_STRUCTURAL_FACTS' if not errors else 'REVISE_REQUIRED','source_sha':PIN,'execution_pattern':'one_shot','command':passport['actual_command'],'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'checks':len(checks),'error_count':len(errors),'errors':errors,'modules':modules,'total_eligible':len(files),'total_OOXML':sum(x['extension'] in ('.docx','.xlsx') for x in files),'all_source_and_copy_bytes_unchanged':not any(x['check'] in ('source_manifest_copy_hashes','postreview_source_and_copy_unchanged') for x in errors),'author_script_executed':False,'scope':'Targeted independent native package/hash facts, all33 DOCX main parts; workbook-rel worksheet coverage for9 XLSX. No formal XSD/formula/layout/legal/currentness/package acceptance. Baseline observational only.','not_claimed':passport['not_claimed'],'script_sha256':digest(Path(__file__).read_bytes()),'file_facts_sha256':digest((O/'independent-file-facts.json').read_bytes()),'model_calls':0,'api_usd':0}
save('independent-review-receipt.json',receipt)
(O/'report.md').write_text('# Independent baseline structural review\n\n'+receipt['status']+' at '+PIN+'.\n\n'+str(len(checks))+' scoped assertions, '+str(len(errors))+' failures. 51 eligible source inputs: 33 DOCX, 9 XLSX, 4 TXT and 5 PDF. TXT/PDF only hash/applicability checked. All42 native packages independently read for member CRC, duplicate entries, XML parsing, content-type coverage and internal targets. All33 main DOCX parts present; workbook-linked sheet parts in all9 XLSX match author inventory, native stored cell/formula counts match. External targets not fetched. Author audit script inspected but not executed.\n\nBaseline source membership is dry-policy inventory, not actual PHP delivery or accepted repackaging. No formal XSD, calculation, layout, legal/currentness, human acceptance or sale readiness verdict.\n')
save('READY.json',{'receipt_sha256':digest((O/'independent-review-receipt.json').read_bytes()),'report_sha256':digest((O/'report.md').read_bytes()),'script_sha256':receipt['script_sha256'],'facts_sha256':receipt['file_facts_sha256'],'status':receipt['status']})
print(json.dumps(receipt,ensure_ascii=False));sys.exit(bool(errors))
