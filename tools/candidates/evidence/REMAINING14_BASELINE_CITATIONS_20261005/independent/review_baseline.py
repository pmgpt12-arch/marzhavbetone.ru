"""Independent native corpus factual review; author parser/checker is never executed."""
from pathlib import Path
import json,hashlib,collections,re,datetime
R=Path(__file__).resolve().parent;A=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261005/catalog-baseline-citations-20261005')
load=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
plan=load(R/'source-plan.json');bs=load(R/'source-bindings.json');idx=load(R/'independent-corpus-index.json');ready=load(A/'READY.json');manifest=load(A/'input-hashes.json');agg=load(A/'aggregate-coverage.json')
globalchecks=[];pins=[];errors=[]
def ck(ok,label,detail=None,target=None):
 x={'check':label,'pass':bool(ok),'detail':detail};(target if target is not None else globalchecks).append(x)
 if not ok:errors.append(x)
def pin(p,expected=None):
 b=p.read_bytes();h=sha(b);pins.append({'path':str(p),'sha256':h,'bytes':len(b)});ck(expected is None or h==expected,'Frozen author artifact exact hash',str(p));return h
pin(A/'READY.json','342fd1a66f340a61025df248d004376f61988b8209c1e58216f02435d2289a30');pin(A/'extract_catalog.py','7aaf5760164bf5ed4f5e3f04c231a3b70df85a76a97bc3d44e8b83ed9e1d4705');pin(A/'aggregate-coverage.json','13f0773b3563ef9fdd1d5c8d20942cbe3f73b5c09759dc7a97eda44c2d6edfa6')
for n in ['lexical-grammar.py','input-hashes.json','schema.json','passport.json','verification-receipt.json']:pin(A/n)
ck(ready['source_sha']==manifest['source_sha']==plan['source_sha'],'Exact cached baseline source')
ck(set(ready['modulemaps'])==set(x['sku'] for x in bs) and len(ready['modulemaps'])==14,'Exactly remaining14 modules')
source={(b['sku'],b['path']):b for b in bs};ck(len(source)==len(manifest['bindings'])==135,'All135 separate source context bindings')
for d in manifest['bindings']:
 b=source.get((d['sku'],d['path']));ck(b is not None and all(d[k]==b[k] for k in ['source_sha','sha256','git_blob','size']),'Author exact contextual manifest binding',{'sku':d['sku'],'path':d['path']})
ck(len(manifest['unique_inputs'])==len(idx)==125,'FullSHA native dedup exactly125 unique inputs')
own={h:load(R/'corpus'/f'{h}.json') for h in idx}
def key(u):
 l=u['location'];k=u['kind']
 if k=='docx_paragraph':return('docx',l['part'],l['xml_path'])
 if k=='xlsx_cell':return('xlsx',l['sheet'],l['cell'],l['value_mode'])
 if k=='txt_line':return('txt',l['physical_line'])
 if k=='pdf_page':return('pdf',l['physical_page'])
 if k=='native_xml_attribute':return('attr',l['part'],l['xml_path'],l['attribute'])
 if k=='xlsx_comment':return('comment',l['part'],l['xml_path'])
 return('leaf',l['part'],l['xml_path'])
indexes={h:{key(u):u for u in us} for h,us in own.items()}
def author_key(row):
 l=row['location'];k=l['kind']
 if k=='docx_xml_paragraph':return('docx',l['part'],l['xml_path'])
 if k in ['xlsx_cell','xlsx_cell_cache']:
  mode=l['value_mode'];mode='formula' if mode=='stored_formula_no_recalculation' else 'cached_value' if k=='xlsx_cell_cache' else 'stored_value'
  return('xlsx',l['sheet'],l['cell'],mode)
 if k=='txt_line':return('txt',l['physical_line'])
 if k=='pdf_pdftotext_page':return('pdf',l['page'])
 if k in ['xlsx_sheet_title','xlsx_validation_text']:return('attr',l['part'],l['xml_path'],l['attribute'])
 if k=='xlsx_comment':return('comment',l['part'],l['xml_path'])
 if k in ['ooxml_core_titlefield','xlsx_drawing_chart_text','xlsx_defined_name','xlsx_header_footer']:return('leaf',l['part'],l['xml_path'])
 raise ValueError('Unknown authored native locator '+k)
canonical={c.casefold():c for c in ['ГрК','ГК','АПК','НК','ГПК','ТК','КоАП','БК','СК','ЗК','ЖК']};coderx=re.compile(r'\b(?:ГрК|ГК|АПК|НК|ГПК|ТК|КоАП|БК|СК|ЗК|ЖК)\b',re.I)
results=[];allcoverage=[];(R/'modules').mkdir(exist_ok=True)
for sku,advertised in ready['modulemaps'].items():
 D=R/'modules'/sku;D.mkdir(exist_ok=True);checks=[];beforeerrors=len(errors);mapp=A/'modules'/sku/'citation-inventory.json';compactp=mapp.with_name('citation-source-units.json');pin(mapp,advertised['map_sha256']);pin(compactp,advertised['compact_units_sha256']);m=load(mapp);compact=load(compactp)['units'];compactbyid={u['unit_id']:u for u in compact}
 ck(m['source_sha']==plan['source_sha'] and m['sku']==sku and m['source_status']=='CACHED_CONFIGURED_BASELINE_NOT_ACCEPTED_DELIVERY','Module source baseline status exact',sku,checks)
 ck(m['membership']=='SOURCE_ELIGIBLE_DRY_INVENTORY_NOT_ACTUAL_PHP_ZIP' and m['source_currentness']=='NOT_VERIFIED' and m['human_legal']=='NOT_PERFORMED' and m['normative_verdict']=='NOT_VERIFIED','No approved delivery/edition/human/legal PASS',sku,checks)
 files={d['path']:d for d in m['documents']};mine={b['path']:b for b in bs if b['sku']==sku};ck(set(files)==set(mine) and len(files)==advertised['files'],'Exact module eligible path membership',sku,checks)
 for p,d in files.items():
  b=mine[p];ck(all(d[k]==b[k] for k in ['source_sha','sha256','git_blob','size']) and d['native_corpus_key']==b['sha256'],'Module document hash/blob/size/dedup binding',p,checks)
  if p.endswith('.pdf'):
   meta=d['native_metadata'];ours=idx[b['sha256']];ck(meta['pdf_raw_text_sha256']==ours['raw_text_sha256'] and len(meta['pdf_pages'])==ours['physical_pages'],'All PDF rawtext/pages exact',p,checks)
   for page,actual in zip(meta['pdf_pages'],ours['pages']):
    ck(page['page']==actual['physical_page'] and page['text_sha256']==actual['text_sha256'] and page['characters']==actual['characters'] and page['physical_lines']==actual['lines'] and page['text_empty']==actual['empty_or_image_only_text_scope'],'Actual PDF page hash/chars/lines/empty exact',{'document':p,'page':page['page']},checks)
   ck(any(x['kind']=='PDF_TEXT_LAYER_ONLY_NO_LAYOUT_OR_OCR_REVIEW' for x in meta['limitations']),'PDF text/OCR/layout limit explicit',p,checks)
 spans=collections.defaultdict(list);recordids=[];mappedkeys=set()
 for row in m['literal_occurrences']+m['unresolved_legal_and_standard_markers']:
  ident=row.get('occurrence_id',row.get('marker_id'));p=row['document'];h=row['file_sha256'];lk=author_key(row);u=indexes[h].get(lk);ck(u is not None,'Actual independent native locator exists',{'sku':sku,'id':ident,'locator':lk},checks)
  if u is None:continue
  txt=u['text'];l=row['location'];lo,hi=row['span'];ql,qh=row['quote_span'];literal=row.get('literal',row.get('marker'));ck(row['sku']==sku and p in mine and h==mine[p]['sha256'],'Every occurrence/marker separateSKU/path/sourcehash',ident,checks)
  ck(0<=lo<hi<=len(txt) and txt[lo:hi]==literal,'Actual source literal/marker span exact',ident,checks);ck(0<=ql<qh<=len(txt) and txt[ql:qh]==row['short_quote'],'Actual source quotation Unicode span exact',ident,checks)
  ck(row['registry_norm_id'] is None and row['normative_verdict']=='NOT_VERIFIED','No fabricated normative ID/acceptance',ident,checks)
  uid=row['unit_id'];ck(uid==sku+':'+p+':'+str(row['native_unit_index']) and uid in compactbyid and compactbyid[uid]['text']==txt and compactbyid[uid]['document']==p and compactbyid[uid]['sku']==sku and compactbyid[uid]['file_sha256']==h,'Compact native unit/context index binding',ident,checks)
  if l['kind']=='docx_xml_paragraph':
   ck(l['global_paragraph_ordinal_including_empty']==u['location']['global_paragraph_ordinal_including_empty'] and l['nonempty_paragraph_ordinal']==u['location']['nonempty_paragraph_ordinal'],'Native DOCX actual XPath and paragraph ordinals',ident,checks)
  elif l['kind'] in ['xlsx_cell','xlsx_cell_cache']:
   ck(l['part']==u['location']['part'] and l['xml_path']==u['location']['xml_path'],'Native XLSX actual sheet/cell/XML XPath',ident,checks)
  elif l['kind']=='pdf_pdftotext_page':
   ck(l['text_sha256']==u['text_sha256'] and l['page_character_span']==row['span'] and l['physical_line_start']==txt.count('\n',0,lo)+1 and l['physical_line_end']==txt.count('\n',0,hi-1)+1,'PDF exact physical page/span/line numbering',ident,checks)
  spans[(p,lk)].append((lo,hi,ident));mappedkeys.add((p,lk));recordids.append(ident)
  if 'occurrence_id' in row:
   lc={canonical[x.casefold()] for x in coderx.findall(literal)};context=txt
   if l['kind']=='pdf_pdftotext_page':
    first=txt.rfind('\n',0,lo)+1;last=txt.find('\n',hi);last=len(txt) if last<0 else last;context=txt[first:last] if '\n' not in literal else ''
   tc={canonical[x.casefold()] for x in coderx.findall(context)};code=row['code'];binding=row['code_binding']
   ok=(binding=='explicit_literal' and bool(lc) and code in lc) or (binding in ['one_explicit_code_in_same_native_text_unit','one_explicit_code_in_same_pdf_physical_line'] and not lc and tc=={code}) or (binding=='UNRESOLVED_NO_OR_MULTIPLE_EXPLICIT_CODE' and code is None and not lc and len(tc)!=1)
   ck(ok,'Observed abbreviation code binding only; PDF physical line only',ident,checks)
   numberpart=re.split(r'(?:ст\.|стать(?:я|и|ю|е|ей|ями))',literal,maxsplit=1,flags=re.I)[-1];numberpart=coderx.split(numberpart,maxsplit=1)[0];nums=re.findall(r'\d+(?:\.\d+)?',numberpart)
   ck(nums==row['articles_as_written'],'Article/list/range numbers as written, no normative expansion',ident,checks)
   ck(code is not None or 'UNRESOLVED_CODE_BINDING' in row['ranges_or_variants'],'Unresolved code explicit',ident,checks)
  else:ck(row['classification'].startswith('UNRESOLVED') and 'not' in row['reason'].lower(),'Marker explicitly raw unresolved not defect/norm',ident,checks)
 ck(len(recordids)==len(set(recordids)),'Module-specific IDs unique across all paths',sku,checks)
 ids=[o['occurrence_id'] for o in m['literal_occurrences']];groupids=[i for g in m['deduplicated_groups'] for i in g['occurrence_ids']];ck(collections.Counter(ids)==collections.Counter(groupids),'Every occurrence dedup retained exactlyonce',sku,checks)
 for g in m['deduplicated_groups']:
  group=[o for o in m['literal_occurrences'] if o['occurrence_id'] in g['occurrence_ids']]
  ck(g['registry_norm_id'] is None and g['group_is_not_norm'] is True and all(' '.join(o['literal'].split()).casefold()==g['literal_normalized'].casefold() and o['code']==g['code'] and o['articles_as_written']==g['articles_as_written'] for o in group),'Groups lexical only and exact observed members',g['group_id'],checks)
 coverage=[];signalunits=0;signaltokens=0;extra_scope=[]
 for p,b in mine.items():
  for u in own[b['sha256']]:
   if not u['broad_tokens']:continue
   lk=key(u);tokens=[];signalunits+=1
   for token in u['broad_tokens']:
    lo,hi=token['span'];covered=[ident for a,z,ident in spans.get((p,lk),[]) if max(a,lo)<min(z,hi)]
    ck(bool(covered),'Independent broad law/standard/№ token represented by actual span',{'sku':sku,'document':p,'native_locator':lk,'token':token['token'],'span':token['span']},checks)
    tokens.append({**token,'overlapping_records':covered});signaltokens+=1
   coverage.append({'document':p,'file_sha256':b['sha256'],'native_locator':lk,'text':u['text'],'tokens':tokens})
  for x in idx[b['sha256']].get('extra_native_signals',[]):extra_scope.append({'document':p,**x})
 ck(not extra_scope,'No unrepresented native nonvisible text signal outside corpus scope',extra_scope,checks)
 ck(len(ids)==advertised['article_literals'] and len(m['deduplicated_groups'])==advertised['groups_not_norms'] and len(m['unresolved_legal_and_standard_markers'])==advertised['raw_markers_not_defects'],'Frozen READY count binding exact',sku,checks)
 moduleerrors=errors[beforeerrors:];summary={'sku':sku,'status':'ACCEPT_FACTUAL_BASELINE_SOURCE_INVENTORY' if not moduleerrors else 'CHANGES_REQUESTED_FACTUAL_BASELINE','source_sha':plan['source_sha'],'map_sha256':advertised['map_sha256'],'source_bindings':len(mine),'article_literals':len(ids),'lexical_groups_not_norms':len(m['deduplicated_groups']),'raw_unresolved_markers_not_defects':len(m['unresolved_legal_and_standard_markers']),'independent_broad_signal_units':signalunits,'independent_broad_signal_tokens':signaltokens,'checks':len(checks),'errors':moduleerrors,'scope':'Cached dry-eligible source baseline only; not accepted PHP delivery/current repackaging/legal completeness/currentness/human/release approval.','source_currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','normative_verdict':'NOT_VERIFIED'}
 (D/'independent-review-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(D/'independent-check-details.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));(D/'independent-broad-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2));results.append(summary);allcoverage.extend(coverage)
for p in pins:ck(sha(Path(p['path']).read_bytes())==p['sha256'],'Frozen author artifact unchanged after review',p['path'])
summary={'status':'ACCEPT_REMAINING14_FACTUAL_BASELINE_SOURCE_INVENTORIES' if not errors else 'CHANGES_REQUESTED_BASELINE_INVENTORIES','source_sha':plan['source_sha'],'modules':results,'source_bindings':len(bs),'unique_inputs':len(idx),'unique_native_text_units':sum(len(x) for x in own.values()),'PDF_unique_inputs':8,'PDF_physical_pages':14,'article_literals':sum(x['article_literals'] for x in results),'lexical_groups_not_norms':sum(x['lexical_groups_not_norms'] for x in results),'raw_markers_not_defects':sum(x['raw_unresolved_markers_not_defects'] for x in results),'checks':len(globalchecks)+sum(x['checks'] for x in results),'errors':errors,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unknown_scope':'Cached baseline only. Actual PHP delivery membership, current approved repackaging, product/OOXML layout/formula behavior/financial/legal applicability/official editions/currentness/human acceptance/release/other modules not established. Generic raw signals are not defects or identified norms.','models':0,'USD':0,'new_PDF_extracts_during_review':0,'author_parser_calls':0,'source_currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','normative_verdict':'NOT_VERIFIED'}
(R/'author-artifact-pins-before-after-review.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2));(R/'aggregate-review-checks.json').write_text(json.dumps(globalchecks,ensure_ascii=False,indent=2));(R/'independent-review-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(R/'independent-review-report.md').write_text('# Independent remaining14 cached-baseline factual citation QA\n\n'+json.dumps({k:v for k,v in summary.items() if k not in ['modules','errors']},ensure_ascii=False,indent=2)+'\n\n'+json.dumps([{'sku':x['sku'],'status':x['status'],'checks':x['checks'],'errors':len(x['errors'])} for x in results],ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='modules'},ensure_ascii=False));print('MODULES',json.dumps([{'sku':x['sku'],'status':x['status'],'checks':x['checks'],'errors':len(x['errors'])} for x in results],ensure_ascii=False))
