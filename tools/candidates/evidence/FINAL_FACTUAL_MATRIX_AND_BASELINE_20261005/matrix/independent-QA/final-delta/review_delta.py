from pathlib import Path
import json,hashlib,copy,datetime
R=Path(__file__).resolve().parent;P=R.parent;BASE=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261005/parallel-final-gates-20261005');OLD=BASE/'freeze-20261005-1715';NEW=BASE/'freeze-20261005-1725'
load=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();checks=[];errors=[]
def ck(ok,label,detail=None):
 x={'check':label,'pass':bool(ok),'detail':detail};checks.append(x)
 if not ok:errors.append(x)
pins={'completion-gates-matrix.json':'b257d043b54cf4f9611c049e4f677cb1cd9b9d8eaebc49427c88b4c023632cd4','completion-gates-matrix.md':'6668e104d69a0efe3278a10fed1724d71760476e865d51788715dafe73147800','input-manifest.json':'584b2c4a2fb19f604d00c406ab4f408934de39576581d2d81f2078fdc8751c2e','event-delta-receipt.json':'66ab9731ef4cc8f6cd8e4dcf61f66a5846d291ece2aeafca36e0d9659b3c49c7'}
for name,h in pins.items():ck(sha((NEW/name).read_bytes())==h,'Frozen final artifact exact',name)
priorreceipt=load(P/'independent-review-receipt.json');ck(priorreceipt['status']=='ACCEPT_FACTUAL_FOUR_MODULE_SNAPSHOT' and priorreceipt['matrix_sha256']==sha((OLD/'completion-gates-matrix.json').read_bytes()),'Historical1715 independent acceptance preserved')
for name,h in load(NEW/'SHA256SUMS.json').items():ck(sha((NEW/name).read_bytes())==h,'Complete final checksum manifest',name)
old=load(OLD/'completion-gates-matrix.json');new=load(NEW/'completion-gates-matrix.json');om={x['id']:x for x in load(OLD/'input-manifest.json')['inputs']};nm={x['id']:x for x in load(NEW/'input-manifest.json')['inputs']}
added=set(nm)-set(om);expected_added={'p3-citation-composition481','p2-citation-composition482','p2-citation-merge482'}
ck(len(om)==37 and len(nm)==40 and set(om)<=set(nm) and added==expected_added,'Exactly three explicit added receipt IDs, prior37 retained')
oldpins=load(P/'review-input-pins.json');previouspins={x['id']:x for x in oldpins}
for ident,x in om.items():
 y=nm[ident];ck(y==x,'Prior input metadata/snapshot/path/hash exact unchanged',ident)
 if x.get('exact_snapshot'):ck(sha(Path(x['exact_snapshot']).read_bytes())==x['sha256'],'Prior frozen input bytes still exact',ident)
 ck(y['sha256']==previouspins[ident]['sha256'],'Prior pin bound to accepted independent review',ident)
fresh={}
for ident in sorted(added):
 x=nm[ident];b=Path(x['exact_snapshot']).read_bytes();ck(sha(b)==x['sha256'] and len(b)==x['bytes'],'New receipt snapshot exact hash/length',ident)
 ck(Path(x['path']).read_bytes()==b,'New snapshot exact original receipt',ident);fresh[ident]=json.loads(b)
p3=fresh['p3-citation-composition481'];p2=fresh['p2-citation-composition482'];p2merge=fresh['p2-citation-merge482']['actual']['structuredContent']
ck(p3['status']=='VERIFIED_ACTUAL_MERGED_FACTUAL_INVENTORY_COMPOSITION' and p3['pr']==481 and p3['actual_working_head']=='f7dee1009923f4dc0cc5bc277fe3d5253cc2f7a1','Actual P3f7dee/PR481 merged composition')
ck(p3['accepted_buyer_source_snapshot']==old['modules'][2]['buyer_snapshot_sha'] or p3['accepted_buyer_source_snapshot']==old['modules'][2]['citation']['source_sha'],'P3 accepted citation buyer input unchanged')
ck(p3['documentary_source_head']==old['modules'][2]['citation']['draft_head_sha'] and p3['accepted_map_sha256']==old['modules'][2]['citation']['inventory_sha256'],'P3 accepted exact draft/map preserved')
ck(len(p3['all11_buyer_input_blobs_exact'])==11 and len(p3['all15_original_PHP_input_blobs_exact'])==15 and len(p3['all46_documentary_paths_exact_source_commit'])==46 and p3['persisted_manifest_all_hashes_exact'] is True and p3['all14_independent_compact_files_exact'] is True,'P3 11buyers/15PHPinputs/46proofs manifest/QA exact receipt')
ck(p2['status']=='PASS_ACTUAL_WORKING_COMPOSITION' and p2['pr']==482 and p2['actual_merged_sha']=='522edf4ff37c60138c02623f8227968ec4052687','Actual P2 full522edf/PR482 composition')
ck(p2merge['merged'] is True and p2merge['state']=='closed' and p2merge['number']==482 and p2merge['merge_commit_sha']==p2['actual_merged_sha'] and p2merge['head_sha']==p2['accepted_output_sha'] and p2merge['base_sha']==p2['accepted_input_sha'],'P2 actual connector merge readback exact composition/head/base')
ck(p2['accepted_input_sha']==old['modules'][1]['citation']['source_sha'] and p2['original_buyer_sha']==old['modules'][1]['buyer_snapshot_sha'] and p2['actual_preserved_PHP_archive_sha256']==old['modules'][1]['technical']['zip_sha256'],'P2 accepted input/buyer/PHP archive unchanged')
ck(p2['buyer_files_verified']==15 and p2['proof_files_verified']==50 and p2['SHA256SUMS_entries_verified']==48 and p2['all15_buyerbytes_unchanged'] is True and p2['all50_documentary_blobs_exact_accepted'] is True,'P2 15buyers/50proofs/48manifest actual bytefidelity receipt')
for ident,r in [('P2',p2),('P3',p3)]:
 ck(r['source_currentness']=='NOT_VERIFIED' and r['human_legal']=='NOT_PERFORMED','New merge receipt no legal/currentness upgrade',ident)
# Compose only the authorised expected factual delta from accepted old matrix + actual new receipts.
expected=copy.deepcopy(old);expected['observed_utc']=new['observed_utc'];e2=expected['modules'][1];e3=expected['modules'][2]
e2['working_head']=p2['actual_merged_sha'];c=e2['citation'];c['status']='ACCEPTED_FACTUAL_INVENTORY_MERGED';c['working_merge_sha']=p2['actual_merged_sha'];c['output_sha']=p2['accepted_output_sha'];c['pr']=482;c['documentary_files_exact']=p2['proof_files_verified'];c['manifest_entries_exact']=p2['SHA256SUMS_entries_verified'];c['inputs']+=['p2-citation-composition482','p2-citation-merge482']
e3['working_head']=p3['actual_working_head'];c=e3['citation'];c['status']='ACCEPTED_FACTUAL_INVENTORY_MERGED';c['actual_merge_status']='MERGED_VERIFIED';c['working_merge_sha']=p3['actual_working_head'];c['documentary_inputs_exact']=len(p3['all46_documentary_paths_exact_source_commit']);c['inputs']+=['p3-citation-composition481']
for row in [e2,e3]:row['remaining_gates']=[x for x in row['remaining_gates'] if x['gate']!='accepted_factual_inventory_documentary_persistence']
ck(expected==new,'Whole final JSON equals only exact authorized receipt-derived delta')
for i,name in enumerate(['S1','P2','P3','P5']):
 oldg=[g for g in old['modules'][i]['remaining_gates'] if g['gate']!='accepted_factual_inventory_documentary_persistence'];newg=new['modules'][i]['remaining_gates']
 ck(oldg==newg,'All substantive owner/STOP/legal/currentness/human/release gates unchanged',name)
 if name in ['S1','P5']:ck(old['modules'][i]==new['modules'][i],'Existing merged module whole row unchanged',name)
 else:ck(old['modules'][i]['technical']==new['modules'][i]['technical'] and old['modules'][i]['buyer_snapshot_sha']==new['modules'][i]['buyer_snapshot_sha'],'Existing technical/buyer snapshot unchanged',name)
delta=load(NEW/'event-delta-receipt.json');ck(delta['prior37_hashes_preserved'] is True and set(delta['added_input_ids'])==added and delta['previous_freeze']=='freeze-20261005-1715','Collector explicit delta receipt matches independent observation')
md=(NEW/'completion-gates-matrix.md').read_text()
for s in ['только база 6077','Новый текст 02/08 ещё не принят','STOP форм 02/04/05','SALE_READY не заявлен','remaining_scope_unknown_for_other_products=true']:ck(s in md,'MD substantive qualification unchanged',s)
ck('481 слит' in md and '482 слит' in md and 'f7dee1009923f4dc0cc5bc277fe3d5253cc2f7a1' in md and '522edf4ff37c60138c02623f8227968ec4052687' in md,'MD exact new merged states and fullheads')
for n,h in pins.items():ck(sha((NEW/n).read_bytes())==h,'Final collector remains frozen after delta review',n)
summary={'status':'ACCEPT_FINAL_FACTUAL_FOUR_MODULE_DELTA' if not errors else 'CHANGES_REQUESTED_FINAL_DELTA','baseline_review_receipt_sha256':sha((P/'independent-review-receipt.json').read_bytes()),'historical_baseline_matrix_sha256':priorreceipt['matrix_sha256'],'final_matrix_sha256':pins['completion-gates-matrix.json'],'final_md_sha256':pins['completion-gates-matrix.md'],'final_input_manifest_sha256':pins['input-manifest.json'],'final_snapshot_utc':new['observed_utc'],'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior37_input_pins_unchanged':True,'added_receipt_ids':sorted(added),'working_citation_merges':{x['module']:x['working_head'] for x in new['modules']},'checks':len(checks),'errors':errors,'qualified_scope':'Only four-module factual evidence persistence update. All substantive open owner/STOP/normative-currentness/human/legal/release gates unchanged. Historical1715 acceptance retained. No approval by filename or allcatalog/sale/manualExcel/legalPASS.','calls':{'models':0,'tests':0,'CI':0,'extraction':0,'builds':0,'product_or_source_mutations':0,'network':0}}
(R/'delta-check-details.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));(R/'new-receipt-pins.json').write_text(json.dumps([nm[x] for x in sorted(added)],ensure_ascii=False,indent=2));(R/'independent-review-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(R/'independent-review-report.md').write_text('# Independent final four-module factual delta QA\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
