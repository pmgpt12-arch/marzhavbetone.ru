from pathlib import Path
import json,re,hashlib,shutil,subprocess,importlib.util
from datetime import datetime, timezone
WT=Path('/home/denis/projects/marzhavbetone.ru/.worktrees/codex-s1-legal-inputs-20261005'); OUT=WT/'tools/candidates/evidence/S1_LEGAL_INPUTS_20261005'; SRC=OUT/'sources'
prior=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261004/legal-primary-preflight-20261005')
idx=json.loads((OUT/'buyer-claims-index.json').read_text()); now=datetime.now(timezone.utc).isoformat()
source_rows=[]
for bundle in ['web-secondary-gk-four-articles.txt','web-secondary-gk-four-articles-b.txt']:
 raw=(SRC/bundle).read_text()
 for chunk in raw.split('\n--------------------------------------------------------------------------------\n'):
  url=re.search(r'\((https://www\.consultant\.ru/document/[^)]+)\)',chunk); article=re.search(r'ГК РФ Статья ([0-9.]+)\. ',chunk)
  if not(url and article): continue
  article=article.group(1).rstrip('.')
  lines=[s for s in chunk.splitlines() if re.match(r'^L\d+:',s)]
  title=next((i for i,s in enumerate(lines) if 'ГК РФ Статья '+article+'.' in s),None)
  end=next((i for i,s in enumerate(lines) if i>(title or 0) and ('Комментарии к статье' in s or '[Button: Открыть полный текст документа]' in s)),len(lines))
  body='\n'.join(lines[title:end])+'\n'
  target=SRC/('secondary-gk-'+article.replace('.','-')+'.txt'); target.write_text(body)
  code='ГК РФ'; key='gk-'+article.replace('.','-')
  source_rows.append({'source_id':key,'code':code,'article':article,'url':url.group(1),'source_class':'secondary','retrieval':'web_tool_direct_open_text_extract; not raw publisher HTML','retrieved_at':now,'edition_as_displayed':'ГК1 red. 10.06.2026' if 'LAW_5142' in url.group(1) else 'header in capture; legal effective-currentness not verified','path':target.relative_to(WT).as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'capture_path':(SRC/bundle).relative_to(WT).as_posix(),'capture_sha256':hashlib.sha256((SRC/bundle).read_bytes()).hexdigest(),'quote_obtained':True,'currentness':'NOT_VERIFIED','legal_acceptance':'NOT_PERFORMED'})
for num,name in [(6,'vsrf-plenum-6-official.pdf'),(7,'vsrf-plenum-7-official.pdf'),(43,'vsrf-plenum-43-official-0.pdf')]:
 receipt=prior/('source-'+str(num)+'-official-receipt.json'); data=json.loads(receipt.read_text()); pdf=prior/name
 actual=hashlib.sha256(pdf.read_bytes()).hexdigest(); expected=data['downloaded'][0]['sha256'] if num==43 else data['sha256']; assert actual==expected,(num,actual,expected)
 shutil.copyfile(pdf,SRC/name); shutil.copyfile(receipt,SRC/receipt.name)
 text=SRC/(pdf.stem+'.txt'); subprocess.run(['pdftotext','-layout',str(SRC/name),str(text)],check=True,timeout=10)
 source_rows.append({'source_id':'vsrf-plenum-'+str(num),'source_class':'official','source_origin':'prior successful retrieved PDF reused; no network repeat','retrieved_at':data.get('observed'),'url':data['downloaded'][0]['url'] if num==43 else data['pdf_url'],'official_page':data.get('official_page',data.get('primary_page')),'path':(SRC/name).relative_to(WT).as_posix(),'sha256':actual,'text_path':text.relative_to(WT).as_posix(),'text_sha256':hashlib.sha256(text.read_bytes()).hexdigest(),'quote_obtained':True,'currentness':'NOT_VERIFIED','legal_acceptance':'NOT_PERFORMED','document_mapping':'candidate contextual source, not an inferred normative acceptance'})
for n in ['gk1-official-probe-probe.json','gk2-official-probe-probe.json','continuation-fetch-block-20261005-1545.json','source-route-correction-20261005-1628.json']:
 shutil.copyfile(prior/n,SRC/n)
(SRC/'retrieval-errors.json').write_text(json.dumps({'observed_at':now,'remote_secondary_route':{'urls':['https://www.consultant.ru/document/cons_doc_LAW_5142/','https://www.consultant.ru/document/cons_doc_LAW_9027/'],'budget':'1 attempt per URL; 8 second socket timeout','outcome':'no output HTML files; exact urllib errors lost after script control-flow failure','classification':'SOURCE_ROUTE_NETWORK plus SCRIPT_LIST_MUTATION','script_error':'KeyError gk1-165-1 because results list was appended during its own iteration','recovery':'no remote network retry; use web direct article URLs and save captured text','gate':'collect fetch receipts before adaptive iteration; iterate snapshot/list copy, never append to live iterable'},'web_click_batch':{'classification':'TOOL_ARGUMENT_RESOLUTION','capture':'web-gk-article-extracts.txt','outcome':'12 invalid click calls; no article evidence','recovery':'resolved real article URLs with search then direct open; no click retry'}},ensure_ascii=False,indent=2)+'\n')
by={s['source_id']:s for s in source_rows}
refs=[]
for row in idx['documents']:
 row['literal_claims']=[c for c in row['reference_candidates'] if c['literal_references']]
 for c in row['literal_claims']:
  for literal in c['literal_references']:
   numbers=literal.split('ст.')[-1] if 'ст.' in literal else re.split(r'статья|статьи|статью|статей',literal,flags=re.I)[-1]
   nums=re.findall(r'\d+(?:\.\d+)?',numbers)
   tail=c['text'][c['text'].find(literal)+len(literal):]
   code_match=re.search(r'(ГК|АПК|НК|ГПК)|Гражданского',literal+' '+tail,re.I)
   code=(code_match.group(1) or 'ГК').upper() if code_match else ('ФЗ-229' if '229-ФЗ' in c['text'] else 'UNRESOLVED')
   for number in nums:
    key={"ГК":"gk","АПК":"apk","НК":"nk","ГПК":"gpk","ФЗ-229":"fz-229"}.get(code,"unresolved")+'-'+number.replace('.','-'); src=by.get(key)
    refs.append({'document':row['path'],'document_hash':row['semantic_hash'],'file_sha256':row['file_sha256'],'location':c['location'],'literal':literal,'proposed_norm_key':key,'code':code,'article':number,'mapping_class':'literal reference normalization; registry norm_id NOT_VERIFIED','source_id':key if src else None,'source_status':'SECONDARY_TEXT_OBTAINED_NOT_ACCEPTED' if src else 'NOT_VERIFIED_SOURCE_NOT_OBTAINED','normative_verdict':'NOT_VERIFIED'})
 idxrow=[]
 for c in row['reference_candidates']:
  # Keep human text candidates separate from repeat XLSX formulas, available in full extraction.
  if row['path'].endswith('.xlsx') and re.match(r'^[A-Z]+\d+=',c['text']) and not c['literal_references']: continue
  idxrow.append(c)
 row['reference_candidates']=idxrow
 row['source_status_by_literal_reference']=[r for r in refs if r['document']==row['path']]
idx['source_sha_history']={'initial':'b3e1eb8acc5f791da0143a8c782fd28337a64562','final':'a610c1524711f2179ba42c12f00692e4db7373a4','delta':'only buyer 10 changed; all other 10 byte-identical; freeze updated before final bundle'}
for row in idx['documents']:
 old=subprocess.check_output(['git','-C',str(WT),'show','b3e1eb8acc5f791da0143a8c782fd28337a64562:'+row['path']]); oldsha=hashlib.sha256(old).hexdigest()
 row['previous_file_sha256']=oldsha; row['byte_changed_from_initial']=oldsha!=row['file_sha256']
assert sum(r['byte_changed_from_initial'] for r in idx['documents'])==1
assert next(r for r in idx['documents'] if r['path'].endswith('/10-obrashchenie-v-sud.docx'))['file_sha256']=='aed923faff74c692794a380bc7ffd42530f5112d70ecb3b6acc7695e11bf7296'
idx['execution_pattern']='one_shot'; idx['primary_result']='S1_normative_input_bundle'; idx['feedback_loop_required']=False; idx['checkpoint_policy']='verified_only'; idx['preparation_status']='VERIFIED_INPUT_BUNDLE'; idx['legal_acceptance']='NOT_PERFORMED'
(OUT/'buyer-claims-index.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n')
(SRC/'source-index.json').write_text(json.dumps({'observed_at':now,'source_count':len(source_rows),'sources':source_rows,'no_PASS_policy':'secondary alone never passes; official PDF retrieval does not confirm current edition/effective amendments'},ensure_ascii=False,indent=2)+'\n')
(OUT/'literal-reference-map.json').write_text(json.dumps({'observed_at':now,'references':refs,'distinct_norm_candidates':sorted(set(r['proposed_norm_key'] for r in refs))},ensure_ascii=False,indent=2)+'\n')
concise=['# Literal references only','',f"Pinned buyer source `{idx['source_sha']}`; no expert legal acceptance.",'']
for row in idx['documents']:
 concise.extend(['## '+row['path'].split('/')[-1],'',f"Semantic hash: `{row['semantic_hash']}`; byte SHA `{row['file_sha256']}`.",''])
 concise.extend('- '+c['location']+': '+c['text'] for c in row['literal_claims']); concise.append('')
(OUT/'literal-claims.md').write_text('\n'.join(concise)+'\n')
print(json.dumps({'source_sha':idx['source_sha'],'buyer_documents':len(idx['documents']),'sources':len(source_rows),'secondary':sum(s['source_class']=='secondary' for s in source_rows),'official_prior_reused':sum(s['source_class']=='official' for s in source_rows),'distinct_literal_norm_candidates':sorted(set(r['proposed_norm_key'] for r in refs))},ensure_ascii=False))
