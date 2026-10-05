"""Independent review of frozen baseline structural observations, not author audit execution."""
from pathlib import Path
import json,hashlib,subprocess,zipfile,io,binascii,collections,xml.etree.ElementTree as E,posixpath,urllib.parse,re,time,datetime,sys
O=Path(__file__).resolve().parent
P=O.parent/'catalog-structural-extension-20261005'
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
def review_native(raw,path,a,f):
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
  return f
passport=json.loads((O/'passport.json').read_text())
for p,h in passport['input_files'].items():check(digest(Path(p).read_bytes())==h,'frozen_input_hash',path=p)
manifest=json.loads((P/'input-hashes.json').read_text());tasks=json.loads((P/'task-passports.json').read_text())['tasks']
receipt=json.loads((P/'execution-receipt.json').read_text());ready=json.loads((P/'READY.json').read_text())
facts=json.loads((P/'unique-structural-facts.json').read_text());bindings=json.loads((P/'all-path-bindings.json').read_text());reuse=json.loads((P/'reuse-provenance.json').read_text())
check(manifest['source_sha']==receipt['source_sha']==ready['source_sha']==PIN,'all_exact_baseline_pins')
check(ready['execution_receipt_sha256']==digest((P/'execution-receipt.json').read_bytes()),'READY_receipt_hash')
items=[dict(i,sku=m['sku']) for m in manifest['modules'] for i in m['members']]
check(len(items)==84 and len({i['path'] for i in items})==84,'84_exact_distinct_path_bindings')
check([i['path'] for i in items]==[b['path'] for b in bindings],'all_path_binding_order_and_membership')
check(set(receipt['before_sha256'])==set(receipt['after_sha256'])=={i['path'] for i in items},'all_receipt_input_paths_exact')
groups={}
for item in items:
 path=item['path'];raw=git('show',PIN+':'+path);h=digest(raw);b=next(x for x in bindings if x['path']==path)
 check(h==item['sha256']==b['sha256']==receipt['before_sha256'][path]==receipt['after_sha256'][path]==digest((P/'exact-inputs'/path).read_bytes()),'84_actual_source_copy_manifest_hashes',path=path)
 check(git('rev-parse',PIN+':'+path).decode().strip()==item['git_blob']==b['git_blob'] and len(raw)==item['size'],'84_git_blob_size_binding',path=path)
 ext=Path(path).suffix
 check(b['sku']==item['sku'] and b['source_sha']==PIN,'explicit_current_path_binding',path=path)
 if ext in ('.docx','.xlsx'):
  check(b['fact_sha256']==h,'binding_fact_fullSHA',path=path)
  groups.setdefault(h,[]).append(item)
 else:check(b['fact_sha256'] is None and b['fact_origin']=='NOT_APPLICABLE_NON_OOXML','non_OOXML_hash_only_applicability',path=path)
 files.append(dict(sku=item['sku'],path=path,sha256=h,git_blob=item['git_blob'],extension=ext,binding_origin=b['fact_origin']))
check(len(groups)==62 and sum(map(len,groups.values()))==71 and len(items)-71==13,'71_OOXML_62_unique_13_NA')
check(set(groups)==set(facts),'all_unique_facts_exact_membership')
first=O.parent/'readonly-pool-independent-20261005'
prior_receipt=json.loads((first/'independent-review-receipt.json').read_text());prior_facts=json.loads((first/'independent-file-facts.json').read_text())
check(prior_receipt['status']=='ACCEPT_SCOPED_BASELINE_STRUCTURAL_FACTS' and prior_receipt['checks']==1373 and prior_receipt['error_count']==0 and prior_receipt['source_sha']==PIN,'first_accepted1373_scope_unchanged')
first_hashes={i['sha256'] for i in prior_facts if i['extension'] in ('.docx','.xlsx')}
check(set(groups)&first_hashes==set(reuse) and len(reuse)==1,'exact_first_pool_reuse_intersection')
independent_unique=[]
for h,provenance in reuse.items():
 oldraw=Path(provenance['original_observation_path']).read_bytes();oldreceipt=Path(provenance['original_receipt_path']).read_bytes()
 check(digest(oldraw)==provenance['original_observation_sha256'] and digest(oldreceipt)==provenance['original_receipt_sha256'],'reused_fact_frozen_original_receipts')
 original=next(x for x in json.loads(oldraw) if x['sha256']==h)
 prior=next(x for x in prior_facts if x['sha256']==h)
 check(original==facts[h] and provenance['observed_original_path']==original['path']==prior['path'] and provenance['source_sha']==PIN,'reused_exact_fact_identity_and_original_path')
 check(sorted(provenance['new_paths'])==sorted(i['path'] for i in groups[h]),'reused_fact_explicit_current_paths')
 for item in groups[h]:
  b=next(x for x in bindings if x['path']==item['path']);check(b['fact_origin']=='REUSED_FIRST_ACCEPTED_42','reused_binding_origin',path=item['path'])
 independent_unique.append({'sha256':h,'reuse':'FROZEN_FIRST_INDEPENDENT_PROOF_NO_NATIVE_REEXECUTION','original_independent_fact':prior,'current_paths':provenance['new_paths']})
worker_units=[];worker_facts={}
check(len(receipt['worker_status'])==4,'four_actual_worker_receipts')
for worker in receipt['worker_status']:
 W=Path(worker['dir']);job=json.loads((W/'job.json').read_text());generated=json.loads((W/'facts.json').read_text())
 check(worker['exit_code']==0 and generated['worker_pid']==worker['pid'] and generated['units']==len(job['units'])==len(generated['facts']),'actual_worker_exit_PID_units',pid=worker['pid'])
 check(not set(worker_facts)&set(generated['facts']),'worker_unique_hash_partition',pid=worker['pid'])
 worker_facts.update(generated['facts']);worker_units.extend(i['sha256'] for i in job['units'])
check(len(worker_units)==len(set(worker_units))==61 and set(worker_units)==set(groups)-set(reuse),'61_new_actual_units_once_no_reused_work')
check(worker_facts=={h:facts[h] for h in worker_units},'actual_worker_facts_exact_combination')
expected_counts={'p7':13,'p10':9,'p12':20,'p13':10,'t1':6,'t2':6,'t3':5,'t4':5,'t5':5,'t6':5}
check({m['sku']:len(m['members']) for m in manifest['modules']}==expected_counts,'all10_module_scope_counts')
for module in manifest['modules']:
 c=collections.Counter(Path(i['path']).suffix for i in module['members']);modules.append({'sku':module['sku'],'eligible':len(module['members']),'docx':c['.docx'],'xlsx':c['.xlsx'],'OOXML':c['.docx']+c['.xlsx']})
for h,members in groups.items():
 check(facts[h]['sha256']==h,'unique_fact_SHA_binding',sha256=h)
 if h in reuse:continue
 representative=members[0];path=representative['path'];a=facts[h];raw=git('show',PIN+':'+path)
 check(a['path'] in [i['path'] for i in members] and a['bytes']==len(raw),'new_fact_representative_path_same_hash_group',path=path)
 for item in members:
  b=next(x for x in bindings if x['path']==item['path']);check(b['fact_origin']=='NEW_UNIQUE_AUDIT','new_binding_origin',path=item['path'])
 f={'sha256':h,'path':path,'sku':representative['sku'],'extension':Path(path).suffix,'all_current_paths':[i['path'] for i in members]}
 independent_unique.append(review_native(raw,path,a,f))
for item in items:
 check(digest(git('show',PIN+':'+item['path']))==item['sha256']==digest((P/'exact-inputs'/item['path']).read_bytes()),'84_postreview_source_copy_unchanged',path=item['path'])
check(receipt['new_unique_hashes_audited_once']==61 and receipt['reused_first42_unique_hashes']==1 and receipt['intra_extension_duplicate_bindings']==9 and receipt['all_source_and_copy_bytes_unchanged'] is True,'dedup_summary_exact')
save('independent-path-bindings.json',files);save('independent-unique-facts.json',independent_unique)
result={'status':'ACCEPT_SCOPED_BASELINE_EXTENSION_FACTS' if not errors else 'REVISE_REQUIRED','execution_pattern':'one_shot','source_sha':PIN,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':passport['actual_command'],'elapsed_seconds':time.monotonic()-start,'checks':len(checks),'error_count':len(errors),'errors':errors,'all_path_bindings':84,'OOXML_bindings':71,'distinct_OOXML_hashes':62,'reused_first_independent_scope':1,'new_unique_native_reviews':61,'intra_extension_duplicate_bindings':9,'nonOOXML_hash_only':13,'modules':modules,'new_unique_docx':sum(f.get('extension')=='.docx' for f in independent_unique),'new_unique_xlsx':sum(f.get('extension')=='.xlsx' for f in independent_unique),'source_and_copy_bytes_unchanged':not any('source_copy' in x['check'] for x in errors),'author_adapter_executed':False,'first1373_review_not_reexecuted':True,'scope':'Baseline observational facts only; copied fact original representative paths explicitly bound to current paths via fullSHA/provenance. All61 new native CRC/XML/contenttypes/internaltargets/DOCXmain/workbookworksheetcoverage facts independently checked once. No formal XSD/calculation/layout/currentness/legal/buyerpackage acceptance.','not_claimed':passport['not_claimed'],'script_sha256':digest(Path(__file__).read_bytes()),'unique_facts_sha256':digest((O/'independent-unique-facts.json').read_bytes()),'bindings_sha256':digest((O/'independent-path-bindings.json').read_bytes()),'model_calls':0,'api_usd':0}
save('independent-review-receipt.json',result)
(O/'report.md').write_text('# Independent baseline extension fact review\n\n'+result['status']+' at '+PIN+'.\n\n'+str(len(checks))+' scoped assertions, '+str(len(errors))+' errors; 84 immutable bindings, 71 OOXML, 62 distinct byte hashes. One exact hash reuses frozen first1373 independent proof with original representative path and current-path provenance.61 new native package reviews once;9 further duplicate bindings,13 nonOOXML hash/applicability only. All10 module counts and actual4worker PID/exit/partition facts match.\n\nNative CRC/XML/contenttype/internalrelation observations and actual DOCXmain/XLSXworkbook-linked sheet coverage/counts checked. Author adapter never executed. First accepted proof unchanged. Baseline structural observations only; no actual PHPdelivery, accepted current buyerpackage, XSDcompleteness, formula correctness, rendered layout, legal/currentness/human/release verdict.\n')
save('READY.json',{'status':result['status'],'receipt_sha256':digest((O/'independent-review-receipt.json').read_bytes()),'report_sha256':digest((O/'report.md').read_bytes()),'script_sha256':result['script_sha256']})
print(json.dumps(result,ensure_ascii=False));sys.exit(bool(errors))
