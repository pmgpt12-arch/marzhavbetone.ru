"""Four bounded native read-only structural audits. No financial/visual/legal verdict."""
import pathlib,subprocess,json,hashlib,datetime,sys,zipfile,xml.etree.ElementTree as ET,posixpath,re,urllib.parse,time,os
R=pathlib.Path(__file__).parent
S='/home/denis/projects/marzhavbetone.ru'
PIN='264d75a06d59de82602dc1bcef347913c44cc648'
def git(*a):return subprocess.check_output(['git','-C',S,*a],timeout=15)
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def worker(sku):
 tasks=json.loads((R/'next-atomic-passports.json').read_text())['tasks'];task=next(x for x in tasks if x['task_id'].startswith('readonly-ooxml-'+sku+'-'))
 O=pathlib.Path(task['output_dir']);passport=json.loads((O/'passport.json').read_text());assert passport['source_sha']==PIN
 results=[];before={};after={}
 for item in task['required_inputs']:
  path=item['path'];raw=git('show',PIN+':'+path);assert sha(raw)==item['sha256']
  assert git('rev-parse',PIN+':'+path).decode().strip()==item['git_blob']
  local=O/'exact-buyers'/item['relative_name'];local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(raw);before[path]=sha(raw)
  result={'path':path,'sha256':sha(raw),'bytes':len(raw),'extension':local.suffix,'issues':[],'status':'NOT_APPLICABLE_NON_OOXML'}
  if local.suffix in {'.docx','.xlsx'}:
   result['status']='OBSERVED_STRUCTURAL_PACKAGE';result['external_relationships']=[];result['relationships_checked']=0
   with zipfile.ZipFile(local) as z:
    names=z.namelist();duplicates=sorted(n for n in set(names) if names.count(n)>1);result['duplicate_parts']=duplicates
    if duplicates:result['issues'].append({'type':'DUPLICATE_ZIP_PARTS','parts':duplicates})
    bad=z.testzip();result['zip_crc_test']=bad
    if bad:result['issues'].append({'type':'CRC_FAILURE','part':bad})
    parts=set(names);xmls={}
    for name in names:
     if name.endswith(('.xml','.rels')):
      try:xmls[name]=ET.fromstring(z.read(name))
      except ET.ParseError as e:result['issues'].append({'type':'XML_PARSE_FAILURE','part':name,'error':str(e)})
    result['xml_parts_parsed']=len(xmls);result['zip_parts']=len(names)
    ct=xmls.get('[Content_Types].xml');result['content_type_coverage_missing']=[]
    if ct is None:result['issues'].append({'type':'MISSING_OR_INVALID_CONTENT_TYPES'})
    else:
     defaults={e.attrib.get('Extension'):e.attrib.get('ContentType') for e in ct if e.tag.endswith('}Default')}
     overrides={urllib.parse.unquote(e.attrib.get('PartName','')).lstrip('/'):e.attrib.get('ContentType') for e in ct if e.tag.endswith('}Override')}
     missing=[n for n in names if n!='[Content_Types].xml' and not n.endswith('/') and n not in overrides and n.rsplit('.',1)[-1] not in defaults]
     result['content_type_coverage_missing']=missing
     if missing:result['issues'].append({'type':'CONTENT_TYPE_UNCOVERED_PARTS','parts':missing})
     dangling=[n for n in overrides if n not in parts]
     if dangling:result['issues'].append({'type':'CONTENT_TYPE_OVERRIDE_TARGET_MISSING','parts':dangling})
    for relpart,root in xmls.items():
     if not relpart.endswith('.rels'):continue
     if relpart=='_rels/.rels':base=''
     else:
      directory=posixpath.dirname(relpart);source=posixpath.join(posixpath.dirname(directory),posixpath.basename(relpart)[:-5]);base=posixpath.dirname(source)
     ids=[]
     for relationship in root:
      rid=relationship.attrib.get('Id');ids.append(rid);target=relationship.attrib.get('Target');result['relationships_checked']+=1
      if not rid or not target:result['issues'].append({'type':'RELATIONSHIP_MISSING_ID_OR_TARGET','part':relpart,'attributes':relationship.attrib});continue
      if relationship.attrib.get('TargetMode')=='External':
       result['external_relationships'].append({'part':relpart,'id':rid,'target':target,'scope':'external not fetched or verified'});continue
      decoded=urllib.parse.unquote(target.split('#',1)[0]);resolved=posixpath.normpath(decoded.lstrip('/') if decoded.startswith('/') else posixpath.join(base,decoded))
      if resolved.startswith('../'):result['issues'].append({'type':'INTERNAL_TARGET_ESCAPES_PACKAGE','part':relpart,'id':rid,'target':target})
      elif resolved not in parts:result['issues'].append({'type':'INTERNAL_RELATIONSHIP_TARGET_MISSING','part':relpart,'id':rid,'target':target,'resolved_part':resolved})
     if len(ids)!=len(set(ids)):result['issues'].append({'type':'DUPLICATE_RELATIONSHIP_IDS','part':relpart})
    result['stored_hash_token_signals']=[]
    for name,root in xmls.items():
     for ordinal,node in enumerate(root.iter(),1):
      text=node.text or ''
      if re.search(r'#{2,}',text):result['stored_hash_token_signals'].append({'part':name,'xml_element_ordinal':ordinal,'tag':node.tag.split('}')[-1],'text':text[:300],'classification':'LEXICAL_STORED_TEXT_ONLY_NOT_RENDERED_CLIPPING_VERDICT'})
    if local.suffix=='.xlsx':
     NS={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
     workbook=xmls.get('xl/workbook.xml');result['xlsx_schema']={'workbook_present':workbook is not None,'sheets':[],'cells':0,'formula_cells':0,'shared_formula_records':0,'cell_types':{},'defined_names':0}
     if workbook is None:result['issues'].append({'type':'XLSX_WORKBOOK_XML_MISSING'})
     else:result['xlsx_schema']['defined_names']=len(workbook.findall('.//x:definedName',NS))
     styles=xmls.get('xl/styles.xml');style_count=len(styles.find('x:cellXfs',NS)) if styles is not None and styles.find('x:cellXfs',NS) is not None else None
     typecounts={}
     for name,root in xmls.items():
      if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name):continue
      cells=root.findall('.//x:sheetData/x:row/x:c',NS);coordinates=[];fc=0
      for cell in cells:
       address=cell.attrib.get('r');coordinates.append(address);ctype=cell.attrib.get('t','n');typecounts[ctype]=typecounts.get(ctype,0)+1
       formula=cell.find('x:f',NS)
       if formula is not None:fc+=1;result['xlsx_schema']['shared_formula_records']+=formula.attrib.get('t')=='shared'
       if not address or not re.fullmatch(r'[A-Z]+[1-9][0-9]*',address):result['issues'].append({'type':'CELL_ADDRESS_SCHEMA_SIGNAL','part':name,'cell':address})
       style=cell.attrib.get('s')
       if style is not None and (not style.isdigit() or style_count is not None and int(style)>=style_count):result['issues'].append({'type':'CELL_STYLE_INDEX_SCHEMA_SIGNAL','part':name,'cell':address,'style':style,'style_count':style_count})
      if len(coordinates)!=len(set(coordinates)):result['issues'].append({'type':'DUPLICATE_CELL_COORDINATES','part':name})
      result['xlsx_schema']['sheets'].append({'part':name,'stored_cells':len(cells),'formula_cells':fc});result['xlsx_schema']['cells']+=len(cells);result['xlsx_schema']['formula_cells']+=fc
     result['xlsx_schema']['cell_types']=typecounts
    else:result['docx_schema']={'main_document_present':'word/document.xml' in parts,'paragraphs':sum(1 for n,root in xmls.items() if n.startswith('word/') for x in root.iter() if x.tag=='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')}
    result['status']='STRUCTURAL_OBSERVATIONS_WITH_SIGNALS' if result['issues'] else 'NO_STRUCTURAL_ISSUES_OBSERVED_IN_SCOPE'
  results.append(result);after[path]=sha(local.read_bytes());assert after[path]==before[path]==sha(git('show',PIN+':'+path))
 write(O/'file-observations.json',results)
 receipt={'status':'READ_ONLY_STRUCTURAL_AUDIT_COMPLETED','sku':sku,'pid':os.getpid(),'source_sha':PIN,'verified_at':now(),'all_member_count':len(results),'ooxml_files':sum(x['extension'] in {'.docx','.xlsx'} for x in results),'non_ooxml_not_applicable':sum(x['extension'] not in {'.docx','.xlsx'} for x in results),'issue_signal_count':sum(len(x['issues']) for x in results),'stored_hash_token_signal_count':sum(len(x.get('stored_hash_token_signals',[])) for x in results),'before_sha256':before,'after_sha256':after,'all_source_and_copy_bytes_unchanged':before==after,'file_observations_sha256':sha((O/'file-observations.json').read_bytes()),'scope':'ZIP CRC/XML/contenttypes/internal relationships/native cell-formula schema observations only, no formula/layout/legal acceptance','model_calls':0,'api_usd':0}
 write(O/'receipt.json',receipt);print(json.dumps(receipt))
if len(sys.argv)>1:worker(sys.argv[1]);sys.exit(0)
assert sha((R/'module-input-hashes.json').read_bytes())=='7ef66ed269183a671269c033d80b4c85f06eff53a452b4e4cd3a3a15b8b4e08e'
assert sha((R/'next-atomic-passports.json').read_bytes())=='e3e3a972d785ea579e207881b88e771fa41d038be52ac011092ef74a5f664f42'
history=[]
for pr,pin in [(409,'a47f868812d287d82540c5c5194c2625bf6c4d88'),(408,'2aef70e0fae06baca8ef981800cc9aff7ef6533c')]:
 assert git('rev-parse',pin).decode().strip()==pin;history.append({'pr':pr,'actual_merge_sha':pin})
write(R/'root-scope-addendum.json',{'history_pointer_correction':history,'raw_report_retained':True,'known_four_update':'P3 PR481 completedf7dee...; P2d5cef... PR482 pending. Abbreviated owner states are reference-only, not source pins for this pool.','frozen_selected_inputs_unchanged':True})
tasks=json.loads((R/'next-atomic-passports.json').read_text())['tasks'];launch=[];start=time.monotonic()
for task in tasks:
 O=pathlib.Path(task['output_dir'])
 if O.exists():raise RuntimeError('DUPLICATE_SCOPE_OUTPUT_EXISTS '+str(O))
 O.mkdir(parents=True);write(O/'passport.json',dict(task,scope_authorized_by_root=True,capacity_snapshot=str(R/'capacity.json'),duplicate_gate='No existing exact output; bounded located reports do not claim this exact structural scope'))
 for item in task['required_inputs']:assert sha(git('show',PIN+':'+item['path']))==item['sha256']
 log=(O/'execution.log').open('w');process=subprocess.Popen([sys.executable,str(pathlib.Path(__file__).resolve()),task['task_id'].split('-')[2]],stdout=log,stderr=subprocess.STDOUT);launch.append((process,log,O,task['task_id']))
write(R/'pool-launch.json',{'started_at':now(),'worker_count':len(launch),'max_seconds':120,'workers':[{'pid':p.pid,'task':t,'output_dir':str(o)} for p,l,o,t in launch]})
completed=[]
for process,log,O,taskid in launch:
 try:code=process.wait(timeout=max(1,120-(time.monotonic()-start)))
 except subprocess.TimeoutExpired:process.terminate();code=process.wait(timeout=5)
 log.close();completed.append({'task':taskid,'pid':process.pid,'exit_code':code,'output_dir':str(O),'receipt':json.loads((O/'receipt.json').read_text()) if (O/'receipt.json').exists() else None})
summary={'status':'FOUR_WORKERS_COMPLETED' if all(x['exit_code']==0 for x in completed) else 'BLOCKED_WORKER_FAILURE','source_sha':PIN,'elapsed_seconds':time.monotonic()-start,'workers':completed,'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'model_calls':0,'api_usd':0,'no_product_git_mutation':True}
write(R/'pool-receipt.json',summary);write(R/'POOL_READY.json',{'status':'READY_FOR_INDEPENDENT_STRUCTURAL_COVERAGE_REVIEW','pool_receipt_sha256':sha((R/'pool-receipt.json').read_bytes()),'script_sha256':summary['script_sha256'],'source_sha':PIN})
print(json.dumps({k:v for k,v in summary.items() if k!='workers'}));print([(x['task'],x['exit_code'],x['receipt']['issue_signal_count'] if x['receipt'] else None) for x in completed])
