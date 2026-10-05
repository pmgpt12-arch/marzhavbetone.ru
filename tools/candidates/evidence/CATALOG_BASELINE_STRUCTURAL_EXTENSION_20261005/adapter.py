import pathlib,subprocess,json,hashlib,datetime,sys,zipfile,xml.etree.ElementTree as ET,posixpath,re,urllib.parse,time,os
R=pathlib.Path(__file__).parent
S='/home/denis/projects/marzhavbetone.ru'
PIN='264d75a06d59de82602dc1bcef347913c44cc648'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',S,*a],timeout=15)
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def audit(local,raw,path):
 result={'path':path,'sha256':sha(raw),'bytes':len(raw),'extension':local.suffix,'issues':[],'external_relationships':[],'relationships_checked':0}
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
 return result

if len(sys.argv)>1:
 job=json.loads(pathlib.Path(sys.argv[1]).read_text());facts={}
 for item in job['units']:
  local=pathlib.Path(item['local_path']);raw=local.read_bytes();assert sha(raw)==item['sha256'];facts[item['sha256']]=audit(local,raw,item['path']);assert sha(local.read_bytes())==item['sha256']
 write(pathlib.Path(job['output']),{'worker_pid':os.getpid(),'facts':facts,'units':len(facts),'finished_at':now()});print(json.dumps({'pid':os.getpid(),'new_unique_facts':len(facts),'output':job['output']}));sys.exit(0)
manifest_raw=(R/'input-hashes.json').read_bytes();assert sha(manifest_raw)=='7771bc15bfae652585622a9b166f3f125b3afbf24964a2aa1f398287f109197e'
assert sha((R/'task-passports.json').read_bytes())=='211d7728286bbe20907b2fb4ca7c904df51ca674882d3f754273a056a89dbf0d'
manifest=json.loads(manifest_raw); assert manifest['source_sha']==PIN
before={};items=[]
for module in manifest['modules']:
 for original in module['members']:
  item=dict(original,sku=module['sku']);raw=git('show',PIN+':'+item['path']);assert sha(raw)==item['sha256'];assert git('rev-parse',PIN+':'+item['path']).decode().strip()==item['git_blob'];before[item['path']]=sha(raw)
  local=R/'exact-inputs'/item['path'];local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(raw);item['local_path']=str(local);items.append(item)
first=R.parent/'catalog-next-queue-20261005-recovery';accepted=json.loads((first/'documentary-bundle/final-scoped-acceptance.json').read_text());assert accepted['status']=='ACCEPT_SCOPED_BASELINE_STRUCTURAL_FACTS'
existing={};provenance={}
for entry in json.loads((first/'pool-receipt.json').read_text())['workers']:
 O=pathlib.Path(entry['output_dir']);receipt_raw=(O/'receipt.json').read_bytes();receipt=json.loads(receipt_raw);observations_raw=(O/'file-observations.json').read_bytes();assert sha(observations_raw)==receipt['file_observations_sha256']
 for fact in json.loads(observations_raw):
  if fact['extension'] not in {'.docx','.xlsx'}:continue
  existing[fact['sha256']]=fact
  provenance[fact['sha256']]={'observed_original_path':fact['path'],'original_receipt_path':str(O/'receipt.json'),'original_receipt_sha256':sha(receipt_raw),'original_observation_path':str(O/'file-observations.json'),'original_observation_sha256':sha(observations_raw),'accepted_scope':'first42 native structural baseline facts1373independentchecks','source_sha':PIN}
groups={}
for item in items:
 if pathlib.Path(item['path']).suffix in {'.docx','.xlsx'}:groups.setdefault(item['sha256'],[]).append(item)
new=[members[0] for digest,members in groups.items() if digest not in existing]
reuse={digest:dict(provenance[digest],new_paths=[i['path'] for i in members]) for digest,members in groups.items() if digest in existing}
write(R/'reuse-provenance.json',reuse)
write(R/'execution-passport.json',{'execution_pattern':'one_shot','primary_result':'10 configured paidentry baseline structural facts with exacthashreuse','feedback_loop_required':False,'checkpoint_policy':'verified_only','source_sha':PIN,'source_manifest_sha256':sha(manifest_raw),'input_paths':84,'OOXML_bindings':71,'distinct_OOXML_hashes':len(groups),'new_unique_hashes':len(new),'reused_unique_hashes':len(reuse),'scope':'Same read-only ZIP/XML/native structural observations, no accepted package/formula/layout/legal claims','workers':min(4,len(new)),'overall_worker_budget_seconds':120,'root_dispatch':'Authorized actual extension max4workers/120s','api_usd':0})
launch=[];start=time.monotonic();N=min(4,len(new))
for index in range(N):
 W=R/'workers'/str(index+1);W.mkdir(parents=True,exist_ok=False);units=new[index::N];job={'units':units,'output':str(W/'facts.json')};write(W/'job.json',job);log=(W/'execution.log').open('w');p=subprocess.Popen([sys.executable,str(pathlib.Path(__file__).resolve()),str(W/'job.json')],stdout=log,stderr=subprocess.STDOUT);launch.append((p,log,W))
write(R/'launch.json',{'started_at':now(),'worker_budget_seconds':120,'workers':[{'pid':p.pid,'dir':str(w)} for p,l,w in launch]})
facts={digest:existing[digest] for digest in reuse};worker_status=[]
for p,log,W in launch:
 try:code=p.wait(timeout=max(1,120-(time.monotonic()-start)))
 except subprocess.TimeoutExpired:p.terminate();code=p.wait(timeout=5)
 log.close();worker_status.append({'pid':p.pid,'exit_code':code,'dir':str(W)});assert code==0,(W,(W/'execution.log').read_text());generated=json.loads((W/'facts.json').read_text());assert not set(generated['facts'])&set(facts);facts.update(generated['facts'])
assert set(facts)==set(groups)
bindings=[]
for item in items:
 ext=pathlib.Path(item['path']).suffix
 bindings.append({'sku':item['sku'],'path':item['path'],'source_sha':PIN,'sha256':item['sha256'],'git_blob':item['git_blob'],'fact_sha256':item['sha256'] if ext in {'.docx','.xlsx'} else None,'fact_origin':'REUSED_FIRST_ACCEPTED_42' if item['sha256'] in reuse else 'NEW_UNIQUE_AUDIT' if ext in {'.docx','.xlsx'} else 'NOT_APPLICABLE_NON_OOXML','scope':'Native structural observations only'})
after={}
for item in items:
 after[item['path']]=sha(pathlib.Path(item['local_path']).read_bytes());assert after[item['path']]==before[item['path']]==sha(git('show',PIN+':'+item['path']))
write(R/'unique-structural-facts.json',facts);write(R/'all-path-bindings.json',bindings)
summary={'status':'BASELINE_STRUCTURAL_EXTENSION_COMPLETED_PENDING_INDEPENDENT_QA','source_sha':PIN,'all_member_bindings':len(items),'OOXML_bindings':sum(x['fact_sha256'] is not None for x in bindings),'nonOOXML_NA':sum(x['fact_sha256'] is None for x in bindings),'distinct_OOXML_hashes':len(groups),'reused_first42_unique_hashes':len(reuse),'reused_first42_bindings':sum(x['fact_origin']=='REUSED_FIRST_ACCEPTED_42' for x in bindings),'new_unique_hashes_audited_once':len(new),'intra_extension_duplicate_bindings':71-len(groups),'structural_issue_signals_unique':sum(len(f['issues']) for f in facts.values()),'stored_hash_token_signals_unique':sum(len(f.get('stored_hash_token_signals',[])) for f in facts.values()),'worker_status':worker_status,'elapsed_worker_seconds':time.monotonic()-start,'before_sha256':before,'after_sha256':after,'all_source_and_copy_bytes_unchanged':before==after,'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'unique_facts_sha256':sha((R/'unique-structural-facts.json').read_bytes()),'reuse_provenance_sha256':sha((R/'reuse-provenance.json').read_bytes()),'scope':'Scoped baseline native observations only, no accepted repackaging source/formalXSD/formula/layout/legal/currentness/human/release claim','model_calls':0,'api_usd':0}
write(R/'execution-receipt.json',summary);write(R/'READY.json',{'status':'READY_FOR_INDEPENDENT_BASELINE_STRUCTURAL_REVIEW','source_sha':PIN,'script_sha256':summary['script_sha256'],'execution_receipt_sha256':sha((R/'execution-receipt.json').read_bytes()),'unique_facts_sha256':summary['unique_facts_sha256'],'reuse_provenance_sha256':summary['reuse_provenance_sha256']})
(R/'SHA256SUMS').write_text('\n'.join(sha(p.read_bytes())+'  '+str(p.relative_to(R)) for p in sorted(R.rglob('*')) if p.is_file() and 'exact-inputs' not in p.parts and p!=R/'SHA256SUMS')+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['before_sha256','after_sha256']}))
