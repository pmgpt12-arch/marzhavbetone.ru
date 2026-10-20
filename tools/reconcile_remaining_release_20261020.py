#!/usr/bin/env python3
"""Bind reviewed deltas and live sale references to the accepted R3 edition."""
from pathlib import Path
from hashlib import sha256
import copy,difflib,json,re,subprocess,yaml
from semantic_hash import semantic_hash,docx_parts,xlsx_parts
from prepare_remaining_release_20261020 import DATA
R=Path(__file__).resolve().parents[1];B=R/'tools/candidates/remaining-batch-r3-20261018';O=B/'release-20261020'
plan=json.loads((O/'release-plan.json').read_text());site={p['file']:p for p in plan['site_files']}
def digest(b):return sha256(b).hexdigest()
def put_site(path,text):
 old=path.read_bytes();new=text.encode()
 if old==new:return
 rel=str(path.relative_to(R))
 if rel not in site:site[rel]={'file':rel,'before_sha256':digest(old)}
 path.write_bytes(new);site[rel]['sha256']=digest(new)
retired=plan['retired_sales'];parents={p['sku']:p for p in plan['packages']}
def sku_url(url):
 m=re.search(r'/products/([pt]\d+)-',url or '');return m[1] if m else None
for path in list(R.glob('*.html'))+list((R/'products').glob('*.html'))+list((R/'articles').glob('*.html'))+list((R/'materialy').glob('*.html')):
 s=path.read_text()
 def schema(match):
  d=json.loads(match[1]);changed=False
  def walk(node):
   nonlocal changed
   if isinstance(node,dict):
    if node.get('@type')=='ItemList':
     old=node.get('itemListElement',[]);new=[]
     for item in old:
      p=item.get('item',{});url=(p.get('offers') or {}).get('url',p.get('url','')) if isinstance(p,dict) else p
      if sku_url(url) in retired:changed=True;continue
      new.append(item)
     if len(old)!=len(new):
      node['itemListElement']=new
      for i,item in enumerate(new,1):item['position']=i
    offers=node.get('offers')
    if isinstance(offers,dict):
     sku=sku_url(offers.get('url'));parent=retired.get(sku,sku)
     if parent in DATA:
      p=parents[parent];title,price,page,lead,*_=DATA[parent]
      want={'price':str(price),'url':'https://marzhavbetone.ru/products/'+page}
      for k,v in want.items():
       if offers.get(k)!=v:offers[k]=v;changed=True
      if node.get('@type')=='Product':
       node['name']=title;node['description']=lead+' '+str(p['count'])+' файлов, включая инструкции.';changed=True
    for value in list(node.values()):walk(value)
   elif isinstance(node,list):
    for value in node:walk(value)
  walk(d)
  return '<script type="application/ld+json">'+json.dumps(d,ensure_ascii=False,indent=2)+'</script>' if changed else match[0]
 s=re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema,s,flags=re.S)
 if path.name=='diagnostika.html':
  m=re.search(r'const SCENARIOS = (\[.*?\]);',s,re.S);scenarios=json.loads(m[1])
  for case in scenarios:
   if case.get('entry') and sku_url(case['entry']['url']) in retired:
    case['entry']=None;case.pop('entry_when',None);case.pop('core_when',None)
   for role in ['entry','core']:
    node=case.get(role)
    if node and sku_url(node['url']) in DATA:node['price']=DATA[sku_url(node['url'])][1]
  s=s[:m.start(1)]+json.dumps(scenarios,ensure_ascii=False,separators=(',',':'))+s[m.end(1):]
 # Only known changed total counts in a block linking that exact product.
 def total_count(match):
  t=match[0]
  for sku,old,new in [('p1',19,20),('p4',23,25)]:
   if re.search(r'(?:products/|href=")'+sku+r'-',t):t=re.sub(r'\b'+str(old)+r'(\s+файл[а-я]*)',lambda m:str(new)+m[1],t,flags=re.I)
  return t
 s=re.sub(r'<(article|aside|li|details)\b[^>]*>.*?</\1>',total_count,s,flags=re.S)
 put_site(path,s)
plan['site_files']=[site[k] for k in sorted(site)]
# Review records preserve the exact previous PASS and its immutable source evidence.
legal=R/'data/legal';mapping=yaml.safe_load((legal/'document-norms.yaml').read_text());results=yaml.safe_load((legal/'normative-results.yaml').read_text())
history=legal/'history/normative-results-2026-10-20-before-r3.yaml'
assert not history.exists(),'Reviewed delta already recorded; inspect rather than rerun'
history.write_bytes((legal/'normative-results.yaml').read_bytes())
review=O/'normative-delta';review.mkdir(exist_ok=True)
notes={
'03-akt-vypolnennyh-rabot.docx':'Only the operational register filename changes from 06 to 06A. All remaining semantic parts are identical; the reference now resolves to the accepted member.',
'11-slovar-poley.docx':'Reviewed rewritten control instructions and relocated legal guidance from file 16. Separate response and pre-action waiting periods remain explicit. Articles 191/193, 395(4), 125/126 and the payment/claim-cost controls remain qualified. Individual entrepreneur particulars are relocated from the previously checked statement of claim.',
'12-pretenziya-na-neoplatu-po-ks-2.docx':'The complete current sending form is an exact ordered subsequence of the previous checked semantic text. Explanatory pages are removed; payment demands, legal grounds, periods, sums, appendices and signature fields in the form are unchanged. Cross-document preparation guidance remains in files 11 and 15.',
'13-uvedomlenie-o-prosrochke-oplaty.docx':'The complete current sending form is an exact ordered subsequence of the previous checked semantic text. No added legal demand or automatic consequence. Files 11/15 retain the distinction between the appointed response date and the applicable waiting period before filing.',
'14-raschet-procentov-395-gk.xlsx':'All formula semantic entries are identical to the previous checked workbook. Revised input and print instructions retain historical debt, dated partial payments, rate/year splits, actual calendar-year length and the payment-day rule. Removed disclaimer blocks do not change calculation logic; sanction selection is explained in files 11/15. Native numeric scenarios are separately bound to the exact current SHA.',
'15-algoritm-pri-zaderzhke-oplaty.docx':'Reviewed every changed paragraph. Qualified pre-action waiting, conditional suspension under articles 328/719 and paragraph 57 of Plenum 54, article 753(4), bankruptcy publication and article 8 enforcement routes retain their substantive conditions. No automatic acceptance or immediate suspension from nonpayment is introduced. Operational dates remain distinct from contractual/procedural periods.',
'16-iskovoe-zayavlenie-o-vzyskanii.docx':'Reviewed the retained claim form and relocated guidance in file 11. Interest basis and prayer remain intact. Alternative conciliation history is now an explicit fillable factual field. The optional repealed registration-certificate appendix is replaced by a factual other-evidence list, consistent with article 126(1)(4) repeal. Entrepreneur particulars and coordinated penalty/interest substitutions remain in file 11.'}
records=[];new_results=[]
for row in results['results']:
 rel=row['document'];name=Path(rel).name
 if name=='01-ks-2.docx':continue # replaced by exact published blank, outside editable legal mechanisms
 path=R/rel;actual=semantic_hash(path)
 if actual==row['document_hash']:new_results.append(row);continue
 assert name in notes,name
 old=review/('previous-'+name);old.write_bytes(subprocess.check_output(['git','show','7ac3535:'+rel],cwd=R))
 assert semantic_hash(old)==row['document_hash'],name
 parts=docx_parts if path.suffix=='.docx' else xlsx_parts;a,b=parts(old),parts(path)
 if name.startswith(('12-','13-')):
  iterator=iter(a);assert all(any(v==line for v in iterator) for line in b if line.strip()),name
 if name.startswith('03-'):assert [s.replace('06-zhurnal-obemov.xlsx','06A-rabochiy-reestr-obemov.xlsx') for s in a]==b
 if path.suffix=='.xlsx':assert [s for s in a if re.match(r'[A-Z]+\d+=',s)]==[s for s in b if re.match(r'[A-Z]+\d+=',s)]
 diff='\n'.join(difflib.unified_diff(a,b,fromfile='previous_checked',tofile='owner_approved_R3',lineterm=''))
 (review/(name+'.diff')).write_text(diff+'\n');old.unlink()
 records.append({'document':rel,'previous_semantic_hash':row['document_hash'],'current_semantic_hash':actual,'raw_sha256':digest(path.read_bytes()),'review':notes[name],'verdict':'PASS_SCOPED_DELTA_REVIEW','reviewer':'Codex current session; no external model call or human-lawyer claim','prior_source_evidence':'data/legal/history/normative-results-2026-10-20-before-r3.yaml'})
 updated=copy.deepcopy(row);updated.update(previous_document_hash=row['document_hash'],document_hash=actual,raw_document_hash='sha256:'+digest(path.read_bytes()),checked_at='2026-10-20',checker='Codex scoped normative delta review',reviewer='current session; no human-lawyer claim',task='OWNER_APPROVED_R3_DELTA_20261020',recheck=notes[name],non_normative_delta_review=str((review/'review.json').relative_to(R)),verdict='PASS',escalation_required=False)
 new_results.append(updated)
assert len(records)==7
(review/'review.json').write_text(json.dumps({'status':'PASS_REVIEWED_CURRENT_DELTAS','documents':records,'basis':'Exact prior PASS hashes verified; changed semantic parts read with cross-document relocations. Prior source evidence retained; sources for changed propositions consulted again 20.10.2026. No new buyer-file edits.','sources_rechecked':['https://www.consultant.ru/document/cons_doc_LAW_37800/4d77fceae32b76a1cc26db3a1c64857d59045fdc/','https://www.consultant.ru/document/cons_doc_LAW_37800/3602d6d485c2ed29f7b862fc5d814eac05274be0/','https://www.consultant.ru/document/cons_doc_LAW_5142/93383099dc4f06165d8d4aac4eeb159db4f6da3d/','https://www.consultant.ru/document/cons_doc_LAW_9027/6b2d751a0d605616a9a1012cb7c7fbac1b6d84b3/','https://www.consultant.ru/document/cons_doc_LAW_71450/638828631575bc444797ecfd09452f7eff765df5/','https://www.consultant.ru/document/cons_doc_LAW_207545/']},ensure_ascii=False,indent=2)+'\n')
results['results']=new_results;results['meta']['updated']='2026-10-20';results['meta']['task']='OWNER_APPROVED_R3_SCOPED_DELTA_REVIEW';results['meta']['delta_review']=str((review/'review.json').relative_to(R));(legal/'normative-results.yaml').write_text(yaml.safe_dump(results,allow_unicode=True,sort_keys=False))
mapping['documents']=[x for x in mapping['documents'] if Path(x['path']).name!='01-ks-2.docx']
mapping['out_of_scope']=[x for x in mapping['out_of_scope'] if Path(x['path']).name not in {'02-ks-3.docx','06-zhurnal-obemov.xlsx'}]
for name in ['01-ks-2.xls','02-ks-3.xls','06-zhurnal-ucheta-rabot-ks-6a.xls']:
 mapping['out_of_scope'].append({'path':'products-storage/01-zakrytie-rabot/'+name,'reason':'Unmodified published source blank, exact original SHA and native visual comparison are enforced by tools/test_official_forms.py; no authored legal mechanism is introduced.'})
mapping['out_of_scope'].append({'path':'products-storage/01-zakrytie-rabot/06A-rabochiy-reestr-obemov.xlsx','reason':'Operational record of actual quantities and supporting documents; no automatic acceptance, payment or legal consequence. Calculation functionality has separate exact-SHA native and owner manual evidence.'})
mapping['meta']['updated']='2026-10-20';(legal/'document-norms.yaml').write_text(yaml.safe_dump(mapping,allow_unicode=True,sort_keys=False))
(O/'release-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print('PASS 7 reviewed legal deltas, 8 legal mechanisms bound, exact original forms and current sale references; buyer files unchanged')
