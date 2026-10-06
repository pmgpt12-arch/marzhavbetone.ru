from pathlib import Path
import json,hashlib,subprocess,zipfile,io,xml.etree.ElementTree as E,re,collections
R=Path(__file__).resolve().parent;S=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261004/s1-current-citation-inventory-20261005');SITE=Path('/home/denis/projects/marzhavbetone.ru');SHA='a77422195c2c68281a7797ad99f9f6b70426d740'
load=lambda p:json.loads(p.read_text())
author=load(S/'citation-inventory.json');manifest=load(S/'input-hashes.json');pins=load(R/'author-artifact-pins-before-review.json');native=load(R/'independent-input-hashes.json');oldinputs=load(R/'independent-required-old-input-hashes.json');frags=load(R/'independent-visible-fragments.json');hits=load(R/'independent-broad-token-hits.json');extra=load(R/'independent-extra-part-hits.json');errors=[];checks=[]
def check(ok,label,detail=None):
 checks.append({'check':label,'pass':bool(ok),'detail':detail})
 if not ok:errors.append({'check':label,'detail':detail})
def git(*a):return subprocess.run(['git',*a],cwd=SITE,capture_output=True,check=True).stdout
check(author['source_sha']==manifest['source_sha']==native['source_commit']==SHA,'Exact source SHA')
files={x['path']:x for x in native['buyers']};check(len(files)==len(author['documents'])==len(manifest['buyer_files'])==11,'Eleven actual buyer files')
for d in author['documents']+manifest['buyer_files']:
 f=files[d['path']];blob=git('rev-parse',SHA+':'+d['path']).decode().strip();check(d['sha256']==f['sha256'] and d['source_sha']==SHA and d['size']==f['bytes'] and d['git_blob']==blob,'Source hash/blob/size',d['path'])
for name,p in manifest['required_inputs'].items():
 ours=next(x for x in oldinputs if x['path']==p['path']);check(p['sha256']==ours['sha256'] and p['size']==ours['bytes'],'Old-map or contract input',name)
check(files['tools/candidates/s1-oplata-za-raboty/02-proverka-i-kontrol-otveta.xlsx']['sha256']=='5918714b4e4e95abc546e1fe7a43f515af50680ecf75352a2949a2ebecac47f0','02 corrected pin')
check(files['tools/candidates/s1-oplata-za-raboty/08-raschet-procentov-395.xlsx']['sha256']=='e0ed0206c17f1b3638bba14dd472c3acad0da80c87dd640169e9c094dec266b4','08 corrected pin')
check(native['04_native_pin_pass'],'04 native owner exact pin')
def fk(f):
 if f['kind']=='docx_visible_paragraph':return(f['path'],'docx',f['physical_p_ordinal1'])
 if f['kind']=='xlsx_visible_cell':return(f['path'],'xlsx',f['sheet'],f['cell'])
 return(f['path'],'txt',f['physical_line_ordinal1'])
bykey={fk(f):f for f in frags};xmlcache={}
def resolve(row):
 p=row['document'];loc=row['location'];kind=loc['kind']
 if kind=='docx_paragraph':key=(p,'docx',loc['global_paragraph_ordinal_including_empty'])
 elif kind=='xlsx_cell':key=(p,'xlsx',loc['sheet'],loc['cell'])
 elif kind=='txt_line':key=(p,'txt',loc['physical_line'])
 else:raise ValueError('Unrecognized locator '+kind)
 f=bykey[key];text=f['text']
 if kind=='docx_paragraph':
  check(loc['part']=='word/document.xml' and loc['nonempty_paragraph_ordinal']==f['nonempty_p_ordinal1'],'DOCX ordinal binding',row.get('occurrence_id',row.get('marker_id')))
  if p not in xmlcache:
   with zipfile.ZipFile(io.BytesIO(git('show',SHA+':'+p))) as z:xmlcache[p]=E.fromstring(z.read('word/document.xml'))
  xpath='.'+re.sub(r'/([A-Za-z]+)',r'/w:\1',loc['xml_path']);node=xmlcache[p].find(xpath,{'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'});actual=''.join(t.text or '' for t in node.findall('.//w:t',{'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})) if node is not None else None;check(actual==text,'DOCX actual XPath binding',row.get('occurrence_id',row.get('marker_id')))
 elif kind=='txt_line':check(loc['nonempty_line']==f['nonempty_line_ordinal1'],'TXT physical/nonempty line',row.get('occurrence_id',row.get('marker_id')))
 else:check(loc['value_mode']=='stored_value' and loc['data_type']==f['type'],'XLSX native stored cell type',row.get('occurrence_id',row.get('marker_id')))
 return key,text
allrecords=author['occurrences']+author['unresolved_legal_markers'];record_sources={};source_spans=collections.defaultdict(list);codes=re.compile(r'\b(?:ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК)\b')
for row in allrecords:
 ident=row.get('occurrence_id',row.get('marker_id'));key,text=resolve(row);record_sources[ident]={'key':key,'text':text};lo,hi=row['span'];literal=row.get('literal',row.get('marker'));ql,qh=row['quote_span'];check(text[lo:hi]==literal and 0<=lo<hi<=len(text),'Exact literal/marker span',ident);check(text[ql:qh]==row['short_quote'] and 0<=ql<qh<=len(text),'Exact short-quote span',ident);source_spans[key].append((lo,hi,ident))
 check(row['normative_verdict']=='NOT_VERIFIED','No normative verdict inherited',ident)
 if 'occurrence_id' in row:
  check(row['file_sha256']==files[row['document']]['sha256'],'Occurrence exact buyer hash',ident);check(row['registry_norm_id'] is None,'No invented registry norm ID',ident)
  binding=row['code_binding'];lc=set(codes.findall(literal));tc=set(codes.findall(text));observed=row['code'];check((binding=='explicit_literal' and lc=={observed}) or (binding=='one_explicit_code_in_same_text_unit' and not lc and tc=={observed}) or (binding=='UNRESOLVED_NO_OR_MULTIPLE_EXPLICIT_CODE' and observed is None and not lc and len(tc)!=1),'Observed code binding grammar',ident)
  m=re.search(r'(?:ст\.|статья|статьи|статью|статье|статей)\s*([0-9][0-9.,\sи–-]*)',literal);nums=re.findall(r'\d+(?:\.\d+)?',m.group(1)) if m else [];check(nums==row['articles_as_written'],'Article numbers as written, no range expansion',ident)
ids=[x['occurrence_id'] for x in author['occurrences']];grouped=[i for g in author['deduplicated_groups'] for i in g['occurrence_ids']];check(collections.Counter(grouped)==collections.Counter(ids) and len(set(ids))==len(ids),'Dedup retains every occurrence exactly once')
for g in author['deduplicated_groups']:
 rows=[x for x in author['occurrences'] if x['occurrence_id'] in g['occurrence_ids']];check(all(' '.join(x['literal'].split())==g['literal_normalized'] and x['code']==g['code'] and x['articles_as_written']==g['articles_as_written'] for x in rows),'Dedup grouping exact literal/code/numbers',g['group_id'])
coverage=[];broad=re.compile(r'(?i)(?:\bст\.|\bстать\w*|\bГК\b|\bАПК\b|\bПленум\w*|Федеральн\w*\s+закон\w*|№\s*\d+)')
for f in hits:
 key=fk(f);spans=source_spans.get(key,[]);tokens=[]
 for m in broad.finditer(f['text']):
  covered=[ident for lo,hi,ident in spans if max(lo,m.start())<min(hi,m.end())];tokens.append({'token':m.group(),'span':[m.start(),m.end()],'overlapping_inventory_records':covered});check(bool(covered),'Independent broad token represented',{'key':key,'token':m.group(),'span':[m.start(),m.end()]})
 coverage.append({'native_key':key,'text':f['text'],'tokens':tokens,'pass':all(t['overlapping_inventory_records'] for t in tokens)})
check(len(coverage)==42 and all(x['pass'] for x in coverage),'All42 independent broad-law passages represented')
check(not extra,'No extra header/footer/comment/drawing/formula legal-token hits in independent scan')
old=load(Path(manifest['required_inputs']['old_literal_reference_map']['path']))['references'];disp=author['old_reference_dispositions'];check(len(old)==len(disp)==58,'All58 old rows explicitly disposed')
for n,(o,d) in enumerate(zip(old,disp),1):
 check(d['old_reference_index']==n and d['document']==o['document'] and d['old_literal']==o['literal'] and d['old_file_sha256']==o['file_sha256'] and d['old_location']==o['location'],'Old row input binding',n)
 check(d['current_file_sha256']==files[d['document']]['sha256'] and d['byte_binding_changed']==(d['old_file_sha256']!=d['current_file_sha256']) and d['normative_verdict_not_inherited'] is True,'Old row hash/rebinding isolation',n)
 locations=[x['location'] for x in author['occurrences'] if x['occurrence_id'] in d['current_occurrence_ids']];actualtextmatches=[record_sources[i]['text'] for i in d['current_occurrence_ids'] if i in record_sources];expected_ids=[x['occurrence_id'] for x in author['occurrences'] if x['document']==d['document'] and x['literal']==d['old_literal']]
 check(d['current_occurrence_ids']==expected_ids,'Old exact-literal occurrence IDs',n)
 expected_location_keys={fk(f) for f in frags if f['path']==d['document'] and d['old_literal'] in f['text']}
 actual_location_keys=set()
 for i,loc in enumerate(d['current_literal_text_locations']):
  k,text=resolve({'document':d['document'],'location':loc,'marker_id':f'old-{n}-location-{i+1}'})
  actual_location_keys.add(k);check(d['old_literal'] in text,'Old substring location actual literal',{'old_row':n,'key':k})
 check(d['status']=='CURRENT_LITERAL_RELOCATED' and actualtextmatches and all(d['old_literal'] in t for t in actualtextmatches) and actual_location_keys==expected_location_keys,'Old literal genuinely relocated with separate exact-ID/substring-location sets',n)
check(author['source_currentness']=='NOT_VERIFIED' and author['human_legal']=='NOT_PERFORMED','No official-currentness/human acceptance claim')
for p in pins:check(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest()==p['sha256'],'Frozen author artifact unchanged',Path(p['path']).name)
summary={'status':'ACCEPT_FACTUAL_INVENTORY' if not errors else 'CHANGES_REQUESTED_FACTUAL_INVENTORY','source_sha':SHA,'inventory_sha256':hashlib.sha256((S/'citation-inventory.json').read_bytes()).hexdigest(),'buyer_hashes_checked':11,'literal_occurrences_checked':len(author['occurrences']),'unresolved_markers_checked':len(author['unresolved_legal_markers']),'dedup_groups_checked':len(author['deduplicated_groups']),'old_rows_checked':len(disp),'independent_native_visible_fragments':len(frags),'independent_broad_law_passages':len(coverage),'checks':len(checks),'errors':errors,'registry_files_present':load(R/'independent-registry-availability.json'),'model_calls':0,'api_usd':0,'source_currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','normative_verdict':'NOT_VERIFIED','scope':'Factual quote/locator/hash/grammar/coverage review only; no article applicability or legal-completeness judgment.'}
(R/'independent-check-details.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));(R/'independent-broad-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2));(R/'independent-review-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
