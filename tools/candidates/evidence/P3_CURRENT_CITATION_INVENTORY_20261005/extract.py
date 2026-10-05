"""P3 factual law/technical-norm markers from frozen actual11 buyer inputs; no judgments."""
from pathlib import Path
import subprocess, json, hashlib, re, zipfile, xml.etree.ElementTree as ET
import collections, datetime, time, bisect, posixpath
R=Path(__file__).resolve().parent
REPO=Path('/home/denis/projects/marzhavbetone.ru')
PIN='7cdf72d77ade7a377e0f01ca68fee3d233152832'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
X='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
def h(b):return hashlib.sha256(b).hexdigest()
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=REPO,timeout=20)
def norm(s):return re.sub(r'\s+',' ',s).strip()
def xmlpath(root,node):
 parent={c:p for p in root.iter() for c in p};parts=[]
 while node in parent:
  p=parent[node];siblings=[c for c in p if c.tag==node.tag]
  parts.append(node.tag.split('}')[-1]+'['+str(siblings.index(node)+1)+']');node=p
 return '/'+root.tag.split('}')[-1]+'/'+('/'.join(reversed(parts)))
manifest=json.loads((R/'input-hashes.json').read_text())
assert manifest['source_sha']==PIN and len(manifest['buyer_files'])==11
assert json.loads((R/'passport.json').read_text())['execution_pattern']=='iterative'
started=time.monotonic();commands=[];units=[];documents=[];pdf_pages=[]
codes=r'ГрК|ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК'
number=r'\d+(?:\.\d+)?'
prefix=r'(?:(?:пп?|пункт(?:а|ы|ов|у|ом)?|ч|част(?:ь|и|ью)|абз|абзац(?:а|ы|ев)?)\.?\s*'+number+r'\s*){0,4}'
articleword=r'(?:ст\.|стать(?:я|и|ю|е|ей|ями))'
article=re.compile(r'(?<![А-Яа-яA-Za-z])'+prefix+articleword+r'\s*'+number+r'(?:\s*(?:,|и|–|-)\s*'+number+r')*(?:\s*(?:'+codes+r')(?:\s*РФ)?)?',re.I)
codepat=re.compile(r'\b('+codes+r')\b',re.I)
canonical={c.lower():c for c in ['ГрК','ГК','АПК','НК','ГПК','ТК','КоАП','БК','СК','ЗК','ЖК']}
standard=re.compile(r'(?<!\w)(?:ГОСТ(?:\s+Р)?|СП|СНиП|ФСБУ|СанПиН|СН|ВСН|РД)\b(?:\s+\d[\d./–-]*)?|\b\d+\s*[-–]\s*ФЗ\b',re.I)
numeric=re.compile(r'№\s*\d+(?:[./–-]\d+)*(?:/[A-Za-zА-Яа-я]+)?')
law=re.compile(r'\b(?:'+codes+r')\b|\bст\.\s*\d|\bстать(?:я|и|ю|е|ей|ями)\b|Пленум|Верховн\w*\s+[Сс]уд\w*|[Фф]едеральн\w*\s+закон\w*|[Пп]риказ\w*|[Пп]остановлен\w*|\bзакон(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b|[Пп]оложени\w*|\bкодекс\w*|Минстро\w*|Ростехнадзор\w*',re.I)
def add(doc,location,text):
 if text.strip():units.append({'unit_id':'unit-'+str(len(units)+1).zfill(5),'document':doc,'location':location,'text':text})
def run(cmd):
 t=time.monotonic();p=subprocess.run(cmd,capture_output=True,timeout=20)
 commands.append({'command':cmd,'cwd':str(R),'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-t,'stdout_sha256':h(p.stdout),'stderr':p.stderr.decode(errors='replace')})
 assert p.returncode==0,(cmd,p.returncode,p.stderr)
 return p.stdout
for src in manifest['buyer_files']:
 file=Path(src['local_path']);raw=file.read_bytes();doc=src['document'];assert h(raw)==src['sha256'] and raw==git('show',PIN+':'+doc)
 before=len(units);item=dict(src);item['limitations']=[]
 if file.suffix=='.docx':
  with zipfile.ZipFile(file) as z:
   assert z.testzip() is None
   parts=[n for n in z.namelist() if n=='word/document.xml' or re.fullmatch(r'word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml',n)]
   for part in parts:
    root=ET.fromstring(z.read(part));nonempty=0
    for ordinal,p in enumerate(root.iter(W+'p'),1):
     text=''.join(t.text or '' for t in p.iter(W+'t'))
     if not text.strip():continue
     nonempty+=1;add(doc,{'kind':'docx_xml_paragraph','part':part,'xml_path':xmlpath(root,p),'global_paragraph_ordinal_including_empty':ordinal,'nonempty_paragraph_ordinal':nonempty},text)
   media=[n for n in z.namelist() if n.startswith('word/media/')]
   if media:item['limitations'].append({'kind':'EMBEDDED_MEDIA_NOT_OCR','members':media})
   item['read_xml_parts']=parts
 elif file.suffix=='.xlsx':
  with zipfile.ZipFile(file) as z:
   assert z.testzip() is None
   shared=[]
   if 'xl/sharedStrings.xml' in z.namelist():
    shared=[''.join(t.text or '' for t in si.iter(X+'t')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(X+'si')]
   workbook=ET.fromstring(z.read('xl/workbook.xml'))
   targets={n.attrib['Id']:n.attrib['Target'] for n in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
   sheets=[]
   for sheet in workbook.iter(X+'sheet'):
    target=targets[sheet.attrib[REL+'id']]
    part=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
    name=sheet.attrib['name'];sheets.append({'sheet':name,'xml_part':part,'state':sheet.attrib.get('state','visible')})
    root=ET.fromstring(z.read(part))
    for c in root.iter(X+'c'):
     address=c.attrib['r'];dtype=c.attrib.get('t','n');v=c.find(X+'v');formula=c.find(X+'f')
     if formula is not None:
      add(doc,{'kind':'xlsx_cell','sheet':name,'cell':address,'part':part,'xml_path':xmlpath(root,c),'data_type':dtype,'value_mode':'stored_formula_no_recalculation'},'='+str(formula.text or ''))
      if v is not None and v.text:add(doc,{'kind':'xlsx_cell_cache','sheet':name,'cell':address,'part':part,'value_mode':'stored_cache_not_verified'},v.text)
     elif dtype=='s' and v is not None:add(doc,{'kind':'xlsx_cell','sheet':name,'cell':address,'part':part,'xml_path':xmlpath(root,c),'value_mode':'stored_shared_string'},shared[int(v.text)])
     elif dtype=='inlineStr':add(doc,{'kind':'xlsx_cell','sheet':name,'cell':address,'part':part,'xml_path':xmlpath(root,c),'value_mode':'stored_inline_string'},''.join(t.text or '' for t in c.iter(X+'t')))
     elif v is not None and v.text:add(doc,{'kind':'xlsx_cell','sheet':name,'cell':address,'part':part,'xml_path':xmlpath(root,c),'value_mode':'stored_value'},v.text)
    for tag in ['oddHeader','oddFooter','evenHeader','evenFooter','firstHeader','firstFooter']:
     for e in root.iter(X+tag):
      if e.text:add(doc,{'kind':'xlsx_header_footer','sheet':name,'part':part,'xml_path':xmlpath(root,e)},e.text)
    for e in root.iter(X+'dataValidation'):
     for attr in ['promptTitle','prompt','errorTitle','error']:
      if e.attrib.get(attr):add(doc,{'kind':'xlsx_validation_text','sheet':name,'part':part,'xml_path':xmlpath(root,e),'attribute':attr,'sqref':e.attrib.get('sqref')},e.attrib[attr])
   for part in z.namelist():
    if re.fullmatch(r'xl/comments/comment\d+\.xml|xl/comments\d+\.xml',part):
     root=ET.fromstring(z.read(part))
     for c in root.iter(X+'comment'):add(doc,{'kind':'xlsx_comment','part':part,'cell':c.attrib.get('ref'),'xml_path':xmlpath(root,c)},''.join(t.text or '' for t in c.iter(X+'t')))
   item['read_sheets']=sheets;item['read_mode']='ZIP/XML readonly; stored values/formulas/caches only'
   images=[n for n in z.namelist() if n.startswith('xl/media/')]
   if images:item['limitations'].append({'kind':'EMBEDDED_MEDIA_NOT_OCR','members':images})
 elif file.suffix=='.txt':
  for line,text in enumerate(raw.decode('utf-8').splitlines(),1):add(doc,{'kind':'txt_line','physical_line':line},text)
 elif file.suffix=='.pdf':
  info=run(['pdfinfo',str(file)]).decode();(R/'pdfinfo-08.txt').write_text(info)
  pages_count=int(re.search(r'^Pages:\s*(\d+)',info,re.M).group(1))
  imageout=run(['pdfimages','-list',str(file)]).decode();(R/'pdfimages-08.txt').write_text(imageout)
  image_rows=[line for line in imageout.splitlines() if re.match(r'^\s*\d+\s+\d+\s+',line)]
  text=run(['pdftotext','-layout','-enc','UTF-8',str(file),'-']).decode('utf-8')
  (R/'pdf-08-raw-pdftotext.txt').write_text(text)
  page_texts=text.split('\f')
  if page_texts[-1]=='':page_texts.pop()
  assert len(page_texts)==pages_count,(len(page_texts),pages_count)
  empty=[]
  for page,t in enumerate(page_texts,1):
   pdf_pages.append({'page':page,'text_sha256':h(t.encode()),'characters':len(t),'physical_lines':len(t.splitlines()),'text_empty':not bool(t.strip())})
   if not t.strip():empty.append(page)
   add(doc,{'kind':'pdf_pdftotext_page','page':page,'extraction':'pdftotext -layout -enc UTF-8','text_sha256':h(t.encode()),'line_numbering':'1-based physical lines in this raw extracted page'},t)
  item['pdf_pages']=pages_count;item['pdf_image_rows']=image_rows
  item['limitations'].append({'kind':'PDF_LAYOUT_AND_IMAGES_NOT_VISUALLY_VALIDATED','image_rows':len(image_rows),'empty_text_pages':empty,'scope':'exact extracted text only; no OCR/layout/legal mechanism completeness claim'})
 else:raise ValueError('Unsupported actual buyer '+str(file))
 item['text_units']=len(units)-before;documents.append(item)
occurrences=[];markers=[]
for unit in units:
 text=unit['text'];matches=list(article.finditer(text))
 def loc(a,b):
  location=dict(unit['location'])
  if location['kind']=='pdf_pdftotext_page':
   offsets=[0]+[m.end() for m in re.finditer('\n',text)]
   la=bisect.bisect_right(offsets,a);lb=bisect.bisect_right(offsets,max(a,b-1))
   location.update(physical_line_start=la,physical_line_end=lb,page_character_span=[a,b])
  return location
 def quote(a,b):return max(0,a-70),min(len(text),b+100)
 for m in matches:
  literal=m.group();explicit=codepat.findall(literal)
  context=text
  context_kind='one_explicit_code_in_same_paragraph_or_cell_or_txt_line'
  if unit['location']['kind']=='pdf_pdftotext_page':
   starts=text.rfind('\n',0,m.start())+1;ends=text.find('\n',m.end())
   if ends<0:ends=len(text)
   context=text[starts:ends] if '\n' not in text[m.start():m.end()] else ''
   context_kind='one_explicit_code_in_same_pdf_physical_line'
  contextcodes=sorted(set(canonical[c.lower()] for c in codepat.findall(context)))
  code=canonical[explicit[-1].lower()] if explicit else contextcodes[0] if len(contextcodes)==1 else None
  binding='explicit_literal' if explicit else context_kind if code else 'UNRESOLVED_NO_OR_MULTIPLE_EXPLICIT_CODE'
  after=re.split(articleword,literal,maxsplit=1,flags=re.I)[-1]
  articles=re.findall(number,re.split(codepat,after,maxsplit=1)[0])
  a,b=quote(m.start(),m.end());ranges=bool(re.search(r'\d\s*[–-]\s*\d',after));variants=[]
  if code is None:variants.append('UNRESOLVED_CODE_BINDING')
  if ranges:variants.append('RANGE_RETAINED_AS_WRITTEN_NOT_EXPANDED')
  if len(articles)>1:variants.append('LIST_OR_RANGE_RETAINED_AS_ONE_LITERAL_NOT_SPLIT_INTO_NORMS')
  occurrences.append({'occurrence_id':'ref-'+str(len(occurrences)+1).zfill(4),'unit_id':unit['unit_id'],'document':unit['document'],'file_sha256':next(d['sha256'] for d in documents if d['document']==unit['document']),'location':loc(m.start(),m.end()),'literal':literal,'span':[m.start(),m.end()],'short_quote':text[a:b],'quote_span':[a,b],'code':code,'code_binding':binding,'articles_as_written':articles,'ranges_or_variants':variants,'registry_norm_id':None,'normative_verdict':'NOT_VERIFIED'})
 seen=[]
 for pattern,classification in [(standard,'UNRESOLVED_STANDARD_OR_OTHER_NORMATIVE_MARKER'),(law,'UNRESOLVED_OR_NON_ARTICLE_LEGAL_MARKER'),(numeric,'UNRESOLVED_NUMBERED_REFERENCE_SIGNAL')]:
  for m in pattern.finditer(text):
   if classification.endswith('LEGAL_MARKER') and any(a.start()<=m.start() and m.end()<=a.end() for a in matches):continue
   if any(a==m.start() and b==m.end() for a,b in seen):continue
   seen.append((m.start(),m.end()));a,b=quote(m.start(),m.end())
   markers.append({'marker_id':'marker-'+str(len(markers)+1).zfill(4),'unit_id':unit['unit_id'],'document':unit['document'],'file_sha256':next(d['sha256'] for d in documents if d['document']==unit['document']),'location':loc(m.start(),m.end()),'marker':m.group(),'span':[m.start(),m.end()],'short_quote':text[a:b],'quote_span':[a,b],'classification':classification,'reason':'Literal law/standard/numbered signal only; raw context retained, numbering alone establishes neither normative identity nor procedural meaning; edition/applicability unresolved; marker is not a defect','registry_norm_id':None,'normative_verdict':'NOT_VERIFIED'})
groups=collections.OrderedDict()
for o in occurrences:
 key=(norm(o['literal']).lower(),o['code'],tuple(o['articles_as_written']))
 groups.setdefault(key,{'literal_normalized':norm(o['literal']),'code':o['code'],'articles_as_written':o['articles_as_written'],'occurrence_ids':[]})['occurrence_ids'].append(o['occurrence_id'])
dedup=[dict(group_id='group-'+str(i).zfill(3),registry_norm_id=None,group_is_not_norm=True,**g) for i,g in enumerate(groups.values(),1)]
numeric_expected=[(u['unit_id'],m.start(),m.end()) for u in units for m in numeric.finditer(u['text'])]
numeric_observed=[(m['unit_id'],m['span'][0],m['span'][1]) for m in markers if m['classification']=='UNRESOLVED_NUMBERED_REFERENCE_SIGNAL']
assert numeric_expected==numeric_observed, 'numeric lexical coverage mismatch'
old_review=json.loads((R/'independent-review-v2.json').read_text())
assert len(old_review['errors'])==10
for error in old_review['errors']:
 d=error['detail'];doc,kind,paragraph=d['key'];a,b=d['span']
 assert any(m['document']==doc and m['location'].get('global_paragraph_ordinal_including_empty')==paragraph and m['span'][0]<=a and b<=m['span'][1] and m['classification']=='UNRESOLVED_NUMBERED_REFERENCE_SIGNAL' for m in markers), d
unitindex={u['unit_id']:u for u in units};kept=set()
for row in occurrences+markers:
 unit=unitindex[row['unit_id']];text=unit['text'];a,b=row['span'];assert text[a:b]==row.get('literal',row.get('marker'));a,b=row['quote_span'];assert text[a:b]==row['short_quote'];kept.add(unit['unit_id'])
 if unit['location']['kind']=='pdf_pdftotext_page':
  a,b=row['span'];assert row['location']['physical_line_start']==text.count('\n',0,a)+1
  assert row['location']['physical_line_end']==text.count('\n',0,max(a,b-1))+1
assert sorted(x for g in dedup for x in g['occurrence_ids'])==sorted(o['occurrence_id'] for o in occurrences)
for src in manifest['buyer_files']:assert h(Path(src['local_path']).read_bytes())==src['sha256'] and git('show',PIN+':'+src['document'])==Path(src['local_path']).read_bytes()
inventory={'source_sha':PIN,'execution_pattern':'iterative','primary_result':'P3_current_factual_citation_handoff_for_lawyer','feedback_loop_required':True,'checkpoint_policy':'verified_only','documents':documents,'parser':{'article_regex':article.pattern,'standard_regex':standard.pattern,'law_marker_regex':law.pattern,'numbered_reference_regex':numeric.pattern,'numbered_reference_rule':'All observed numeric № locators retained separately with raw context; no semantic norm/step classification','code_binding':'Explicit literal or unique explicit code in same source unit; PDF contextual code allowed only same physical line, never whole page','article_list_rule':'Numbers/variants/ranges as written; no expansion into norms','groups_are_not_norms':True},'literal_occurrences':occurrences,'deduplicated_groups':dedup,'unresolved_legal_and_standard_markers':markers,'source_currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','scope_limit':'Factual law and technical-standard lexical signals in captured text of actual11buyers; not legal mechanism coverage, edition/applicability judgment, normative registry or defect list','pdf_limitations':pdf_pages,'old_S1_maps_used':False}
save('citation-inventory.json',inventory)
save('source-text-units.json',{'source_sha':PIN,'units':units})
save('citation-source-units.json',{'source_sha':PIN,'units':[u for u in units if u['unit_id'] in kept],'full_source_units_server_only':'source-text-units.json; all formulas kept as stored, never recalculated'})
save('extract-commands.json',commands)
counts=collections.Counter(o['document'] for o in occurrences);mc=collections.Counter(m['document'] for m in markers)
receipt={'status':'READY_FACTUAL_INVENTORY_PENDING_ROOT_INDEPENDENT_REVIEW','source_sha':PIN,'buyer_files':11,'source_text_units':len(units),'literal_occurrences':len(occurrences),'groups_not_norms':len(dedup),'unresolved_markers_not_defects':len(markers),'standard_or_other_marker_count':sum(m['classification']=='UNRESOLVED_STANDARD_OR_OTHER_NORMATIVE_MARKER' for m in markers),'numeric_reference_markers':len(numeric_observed),'prior_independent10_numeric_gaps_now_explicit':True,'compact_source_units':len(kept),'pdf_pages':pdf_pages,'all_spans_quotes_line_locators_exact':True,'all11_inputs_unchanged':True,'extract_script_sha256':h(Path(__file__).read_bytes()),'map_sha256':h((R/'citation-inventory.json').read_bytes()),'elapsed_seconds':time.monotonic()-started,'model_calls':0,'PHP_build_calls':0,'general_tests_calls':0,'Calc_calls':0,'source_currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','git_commit_push_PR':'NOT_PERFORMED'}
save('verification-receipt.json',receipt)
report=['# P3 current factual citation inventory','','Exact accepted source: '+PIN+'. Lawyer preparation only: source currentness NOT_VERIFIED; human legal NOT_PERFORMED.','','execution_pattern: iterative; primary_result: P3_current_factual_citation_handoff_for_lawyer; feedback_loop_required: true; checkpoint_policy: verified_only.','','All 11 buyer paths and hashes derive from the accepted actual PHP ZIP membership and actual merged input proof. Neither S1 old maps nor product generators provide citation content. Native XLSX was read as ZIP/XML without saving or recalculating.','','| Buyer file | Current SHA256 | Text units | Article literals | Unresolved law/standard markers |','|---|---|---|---|---|']
for d in documents:report.append('| '+Path(d['document']).name+' | '+d['sha256']+' | '+str(d['text_units'])+' | '+str(counts[d['document']])+' | '+str(mc[d['document']])+' |')
report+=['','PDF 08 is included through installed pdftotext -layout -enc UTF-8. Each finding records exact extracted page, page character span and 1-based physical line start/end. No whole-page code inference; surrounding same-line code binding is explicitly labeled. PDF images/empty pages and lack of visual/OCR validation are retained as limitations. Quotes are exact raw substrings, including spaces/newlines; this Markdown escapes newlines only for readability.','','All numeric № locators are retained separately as unresolved lexical signals with exact raw context, including full №344/пр. №3/4/5 remain observed appendix-context literals; numbering alone identifies neither a norm nor a procedure. The previously failed independent10-token coverage checkpoint is retained. Groups are repeated lexical forms, not norms. ГОСТ/СП/СНиП/ФСБУ and numeric ФЗ signals are unresolved technical/other normative markers with raw quotes and locators. Unmatched law tokens, ambiguous bindings, lists and ranges remain visible as written; no edition, norm_id, legal defect or legal mechanism completeness is inferred.','','## Exact article literals','']
for o in occurrences:report.append('- '+o['occurrence_id']+' · '+Path(o['document']).name+' · '+json.dumps(o['location'],ensure_ascii=False)+' · '+json.dumps(o['literal'],ensure_ascii=False)+' · '+json.dumps(o['short_quote'],ensure_ascii=False)+' · binding='+o['code_binding'])
report+=['','## Unresolved law and technical-standard signals','']
for m in markers:report.append('- '+m['marker_id']+' · '+Path(m['document']).name+' · '+json.dumps(m['location'],ensure_ascii=False)+' · '+m['classification']+' · '+json.dumps(m['short_quote'],ensure_ascii=False))
report+=['','## Verified extraction scope','','Every span/quote maps to its frozen source text unit; PDF physical line numbers rechecked. All 11 original Git/input bytes remain exact. Complete source-text-units.json and original buyer inputs remain server-only; citation-source-units.json contains every full source unit supporting an occurrence/marker. Large formula units are disclosed rather than silently dropped. Source-unit capture is textual, not an OCR/layout/legal review.','','Actual invocation: timeout --kill-after=5s 60s python3 '+str(R/'extract.py')+'. Actual Poppler commands/exits recorded in extract-commands.json. No model, PHP rebuild, Calc or general-test invocation. Root independent coverage review is required before any documentary Git commit/push/PR.']
(R/'citation-inventory-report.md').write_text('\n'.join(report)+'\n')
manifest_files=[p for p in R.rglob('*') if p.is_file() and p.name not in ['SHA256SUMS','READY.json']]
(R/'SHA256SUMS').write_text('\n'.join(h(p.read_bytes())+'  '+str(p.relative_to(R)) for p in sorted(manifest_files))+'\n')
ready={'status':receipt['status'],'source_sha':PIN,'extract_script_sha256':receipt['extract_script_sha256'],'citation_map_sha256':receipt['map_sha256'],'report_sha256':h((R/'citation-inventory-report.md').read_bytes()),'verification_receipt_sha256':h((R/'verification-receipt.json').read_bytes()),'manifest_sha256':h((R/'SHA256SUMS').read_bytes()),'compact_source_units_sha256':h((R/'citation-source-units.json').read_bytes()),'full_source_units_sha256':h((R/'source-text-units.json').read_bytes()),'git_commit_push_PR':'NOT_PERFORMED','review_required':'Root independent factual coverage/span review'}
save('READY.json',ready)
print(json.dumps(receipt,ensure_ascii=False));print('READY',R)
