from pathlib import Path
import json,hashlib,subprocess,zipfile,io,xml.etree.ElementTree as E,re,collections,posixpath,sys,datetime
SITE=Path('/home/denis/projects/marzhavbetone.ru');R=Path(sys.argv[1]);C=json.loads((R/'config.json').read_text());SHA=C['sha'];S=Path(C['author']);wn={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};xn={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def dump(n,x): (R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def git(*a):return subprocess.run(['git',*a],cwd=SITE,capture_output=True,check=True).stdout
def hashb(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text())
checks=[];errors=[]
def check(ok,label,detail=None):
 x={'check':label,'pass':bool(ok),'detail':detail};checks.append(x)
 if not ok:errors.append(x)
# Independent broad vocabulary, exact noun endings avoid "закончена"/"закончил".
broad=re.compile(r'(?i)(?:\bст\.\s*\d|\bстать(?:я|и|ю|е|ей|ями)\b|\b(?:ГрК|ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК)\b|Пленум\w*|Верховн\w*\s+суд\w*|Федеральн\w*\s+закон(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b|\bзакон(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b|№\s*\d+|\d+\s*[-–]ФЗ\b|\bкодекс\w*|\b(?:СанПиН|ВСН|РД)\b|\bГОСТ\b|\bСП\s*\d|\bСНиП\b|\bФСБУ\b|\bприказ\w*|\bпостановлен\w*)')
receiptbytes=Path(C['membership']).read_bytes();receipt=json.loads(receiptbytes)
members=receipt.get('buyer_members',receipt.get('members'))
if not isinstance(members,list):raise ValueError('No actual ZIP member list')
if members and isinstance(members[0],str):raise ValueError('Member receipt without hashes requires explicit schema review')
files=[];frags=[];extra=[];pdfs=[];xmlroots={}
# Narrow refreeze review: preserve original independently extracted native/PDF evidence; no PDF rerender/re-extraction.
pins=[]
for name in ['citation-inventory.json','input-hashes.json','extract.py','verification-receipt.json','passport.json']:
 p=S/name;b=p.read_bytes();pins.append({'path':str(p),'sha256':hashb(b),'bytes':len(b)})
check(next(x['sha256'] for x in pins if x['path'].endswith('/citation-inventory.json'))==C['maphash'],'Expected corrected frozen map hash')
check(next(x['sha256'] for x in pins if x['path'].endswith('/extract.py'))==C['scripthash'],'Expected corrected frozen script hash')
dump('author-artifact-pins-before-review.json',pins)
files=load(R/'independent-input-hashes.json')['buyers'];frags=load(R/'independent-visible-fragments.json');extra=load(R/'independent-extra-part-hits.json');pdfs=load(R/'independent-pdf-extraction.json')
check(load(R/'independent-input-hashes.json')['receipt_sha256']==hashb(receiptbytes),'Unchanged accepted PHP membership receipt')
for f in files:
 check(any(m['name']==f['path'].split('/')[-1] and m['sha256']==f['sha256'] for m in members),'Accepted membership prior independent extraction exact',f['path'])
 if f['path'].endswith('.docx'):
  with zipfile.ZipFile(io.BytesIO(git('show',SHA+':'+f['path']))) as z:xmlroots[f['path']]=E.fromstring(z.read('word/document.xml'))
author=load(S/'citation-inventory.json');manifest=load(S/'input-hashes.json');filemap={x['path']:x for x in files}
# Schema adapter only; author bytes untouched. Native locator fields remain independently resolved.
author['occurrences']=author['literal_occurrences'];author['unresolved_legal_markers']=author['unresolved_legal_and_standard_markers']
for d in author['documents']+manifest['buyer_files']:d['path']=d['document'];d['size']=d['bytes']
manifest['required_inputs']={k:{**d,'path':d['source_path']} for k,d in manifest['contracts'].items()}
for row in author['occurrences']+author['unresolved_legal_markers']:
 loc=row['location']
 if loc['kind']=='docx_xml_paragraph':loc['kind']='docx_paragraph';loc['xml_path']=loc['xml_path'].removeprefix('/document')

check(len(files)==C['count']==len(author['documents'])==len(manifest['buyer_files']),'All accepted buyer members exact count')
check(author['source_sha']==manifest['source_sha']==SHA,'Exact current source SHA')
for d in author['documents']+manifest['buyer_files']:
 ours=filemap.get(d['path']);check(ours is not None and d['sha256']==ours['sha256'] and d['size']==ours['bytes'] and d['git_blob']==ours['git_blob'] and d['source_sha']==SHA,'Author exact input hash/size/blob',d['path'])
for label,d in manifest['required_inputs'].items():
 b=Path(d['path']).read_bytes();check(hashb(b)==d['sha256'] and len(b)==d.get('bytes',d.get('size')),'Exact current contract input',label)
def fk(f):
 if f['kind'] in ['docx','txt','pdf']:return(f['path'],f['kind'],f['ordinal'])
 return(f['path'],'xlsx',f['sheet'],f['cell'])
bykey={fk(f):f for f in frags}
def resolve(row):
 loc=row['location'];p=row['document'];k=loc['kind'];ident=row.get('occurrence_id',row.get('marker_id'))
 if k=='docx_paragraph':
  key=(p,'docx',loc['global_paragraph_ordinal_including_empty']);f=bykey[key]
  check(loc['nonempty_paragraph_ordinal']==f['nonempty'] and loc['part']=='word/document.xml','DOCX ordinal binding',ident)
  node=xmlroots[p].find('.'+re.sub(r'/([A-Za-z]+)',r'/w:\1',loc['xml_path']),wn);txt=''.join(t.text or '' for t in node.findall('.//w:t',wn)) if node is not None else None
  check(txt==f['text'],'DOCX exact native XPath',ident)
 elif k=='xlsx_cell':
  key=(p,'xlsx',loc['sheet'],loc['cell']);f=bykey[key];check(loc['value_mode']==f['mode'] and loc['data_type']==f['type'],'XLSX native cell/formula type',ident)
 elif k=='txt_line':
  key=(p,'txt',loc['physical_line']);f=bykey[key];check(loc['nonempty_line']==f['nonempty'],'TXT physical/nonempty line',ident)
 elif k=='pdf_page_text':
  key=(p,'pdf',loc['physical_page']);f=bykey[key];lo,hi=row['span'];lines=f['text'].splitlines(keepends=True);starts=[];total=0
  for line in lines:starts.append(total);total+=len(line)
  first=max(i for i,a in enumerate(starts) if a<=lo);last=max(i for i,a in enumerate(starts) if a<=hi-1)
  check(loc['page_char_span']==[lo,hi] and loc['physical_line_start']==first+1 and loc['physical_line_end']==last+1 and loc['line_start_char_offset']==starts[first] and loc['column_start_0based']==lo-starts[first],'PDF literal page/span/physical line/column exact',ident)
  if 'line_context_char_span' in loc:check(loc['line_context_char_span'][0]==starts[first] and f['text'][loc['line_context_char_span'][0]:loc['line_context_char_span'][1]]==lines[first].rstrip('\r\n'),'PDF exact physical line context',ident)
 else:raise ValueError('Unknown locator '+k)
 return key,f
spans=collections.defaultdict(list);codes=re.compile(r'\b(?:ГрК|ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК)\b')
for row in author['occurrences']+author['unresolved_legal_markers']:
 ident=row.get('occurrence_id',row.get('marker_id'));key,f=resolve(row);txt=f['text'];lo,hi=row['span'];literal=row.get('literal',row.get('marker'));ql,qh=row['quote_span']
 check(0<=lo<hi<=len(txt) and txt[lo:hi]==literal,'Exact native literal/marker Unicode span',ident)
 check(0<=ql<qh<=len(txt) and txt[ql:qh]==row['short_quote'],'Exact native quote Unicode span',ident)
 check(row['registry_norm_id'] is None and row['normative_verdict']=='NOT_VERIFIED','No invented norm ID/verdict',ident);spans[key].append((lo,hi,ident))
 if 'occurrence_id' in row:
  check(row['file_sha256']==filemap[row['document']]['sha256'],'Exact occurrence source hash',ident)
  unit=txt
  if f['kind']=='pdf':
   lines=txt.splitlines(keepends=True);start=sum(len(t) for t in lines[:row['location']['physical_line_start']-1]);unit=lines[row['location']['physical_line_start']-1].rstrip('\r\n')
  lc=set(codes.findall(literal));tc=set(codes.findall(unit));binding=row['code_binding'];observed=row['code']
  check((binding=='explicit_literal' and lc=={observed}) or (binding=='one_explicit_code_in_same_text_unit' and not lc and tc=={observed}) or (binding=='UNRESOLVED_NO_OR_MULTIPLE_EXPLICIT_CODE' and observed is None and not lc and len(tc)!=1),'Code binding independent; PDF line only',ident)
  match=re.search(r'(?:ст\.|статья|статьи|статью|статье|статей)\s*([0-9][0-9.,\sи–-]*)',literal,re.I);nums=re.findall(r'\d+(?:\.\d+)?',match[1]) if match else []
  check(nums==row['articles_as_written'],'Article numbers as written without range expansion',ident)
ids=[x['occurrence_id'] for x in author['occurrences']];grouped=[i for g in author['deduplicated_groups'] for i in g['occurrence_ids']]
check(collections.Counter(ids)==collections.Counter(grouped) and len(set(ids))==len(ids),'Every occurrence retained once in grouping')
for g in author['deduplicated_groups']:
 rows=[x for x in author['occurrences'] if x['occurrence_id'] in g['occurrence_ids']];check(all(' '.join(x['literal'].split()).casefold()==g['literal_normalized'].casefold() and x['code']==g['code'] and x['articles_as_written']==g['articles_as_written'] for x in rows),'Exact dedup grouping',g['group_id'])
coverage=[]
for f in frags:
 tokens=[]
 for m in broad.finditer(f['text']):
  covered=[ident for lo,hi,ident in spans.get(fk(f),[]) if max(lo,m.start())<min(hi,m.end())];tokens.append({'token':m.group(),'span':[m.start(),m.end()],'overlapping_inventory_records':covered})
  check(bool(covered),'Independent broad legal/standard token covered',{'key':fk(f),'token':m.group(),'span':[m.start(),m.end()]})
 if tokens:coverage.append({'native_key':fk(f),'text':f['text'],'tokens':tokens})
check(not extra,'No unaccounted legal/standard signal in additional XML parts',extra)
check(author['source_currentness']=='NOT_VERIFIED' and author['human_legal']=='NOT_PERFORMED' and author.get('registry_norm_ids_assigned',False) is False,'No official currentness/human legal acceptance claimed')
for p in pins:check(hashb(Path(p['path']).read_bytes())==p['sha256'],'Frozen author artifact unchanged',Path(p['path']).name)
for f in files:check(hashb(git('show',SHA+':'+f['path']))==f['sha256'],'Exact source still unchanged',f['path'])
summary={'status':'ACCEPT_FACTUAL_INVENTORY' if not errors else 'CHANGES_REQUESTED_FACTUAL_INVENTORY','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha':SHA,'inventory_sha256':hashb((S/'citation-inventory.json').read_bytes()),'buyer_hashes_checked':len(files),'literal_occurrences_checked':len(ids),'unresolved_markers_checked':len(author['unresolved_legal_markers']),'dedup_groups_checked':len(author['deduplicated_groups']),'independent_native_text_fragments':len(frags),'independent_broad_signal_passages':len(coverage),'independent_broad_signal_tokens':sum(len(x['tokens']) for x in coverage),'pdfs':pdfs,'checks':len(checks),'errors':errors,'model_calls':0,'api_usd':0,'source_currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','normative_verdict':'NOT_VERIFIED','scope':'Independent factual input membership/hash, native locator/quote/span, observational code grammar and broad law/standard token coverage only. Not applicability/edition/currentness/semantic legal completeness or human acceptance.'}
dump('independent-check-details.json',checks);dump('independent-broad-coverage.json',coverage);dump('independent-review-receipt.json',summary)
report='# Independent factual citation inventory review\n\n'+json.dumps({k:v for k,v in summary.items() if k not in ('pdfs','errors')},ensure_ascii=False,indent=2)+'\n\nErrors:\n'+json.dumps(errors,ensure_ascii=False,indent=2)+'\n\nPDF evidence limitations:\n'+json.dumps(pdfs,ensure_ascii=False,indent=2)+'\n'
(R/'independent-review-report.md').write_text(report)
print(json.dumps(summary,ensure_ascii=False))
