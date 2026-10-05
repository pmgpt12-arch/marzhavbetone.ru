from pathlib import Path
import json,hashlib,subprocess,re,datetime
R=Path(__file__).resolve().parent;F=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261005/parallel-final-gates-20261005/freeze-20261005-1715');SITE='/home/denis/projects/marzhavbetone.ru'
load=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest();checks=[];errors=[];pins=[];data={}
def ck(ok,label,detail=None):
 item={'check':label,'pass':bool(ok),'detail':detail};checks.append(item)
 if not ok:errors.append(item)
known={'completion-gates-matrix.json':'8989b013c7de250c7964b8a3fdbf4b939817397b2fd44d1e646b02ab4714687d','completion-gates-matrix.md':'2590b064687d99f3488de8be07559fbb19e837a0f9153dbfa3349d902f206388','input-manifest.json':'76ca7543f4150ffd6b8ccccc9f7247f54004b7c10e44c0f60ffe5db846ad55e5'}
for n,h in known.items():ck(sha((F/n).read_bytes())==h,'Frozen collector hash',n)
for n,h in load(F/'SHA256SUMS.json').items():ck(sha((F/n).read_bytes())==h,'Frozen complete artifact checksum',n)
matrix=load(F/'completion-gates-matrix.json');manifest=load(F/'input-manifest.json');rows=manifest['inputs']
ck(len(rows)==37 and len({x['id'] for x in rows})==37,'All37 unique input IDs')
for item in rows:
 ident=item['id']
 if item.get('exact_snapshot'):b=Path(item['exact_snapshot']).read_bytes()
 elif item.get('git_source_sha'):b=subprocess.run(['git','show',item['git_source_sha']+':'+item['path']],cwd=SITE,capture_output=True,check=True).stdout
 else:b=Path(item['path']).read_bytes()
 ck(sha(b)==item['sha256'],'Exact referenced input bytehash',ident)
 if 'bytes' in item:ck(len(b)==item['bytes'],'Exact input length',ident)
 pins.append({'id':ident,'source_path':item['path'],'snapshot':item.get('exact_snapshot'),'sha256':sha(b),'bytes':len(b)})
 data[ident]=json.loads(b) if item['path'].endswith('.json') or 'exact_snapshot' in item else b.decode()
def inprefs(node):
 if isinstance(node,dict):
  for k,v in node.items():
   if k in ['input','receipt'] and isinstance(v,str):ck(v in data,'Claim reference resolves',v)
   elif k=='inputs' and isinstance(v,list):
    for ident in v:ck(ident in data,'Claim reference resolves',ident)
   else:inprefs(v)
 elif isinstance(node,list):
  for x in node:inprefs(x)
inprefs(matrix)
mods={x['module']:x for x in matrix['modules']};ck(set(mods)=={'S1','P2','P3','P5'},'Exactly four modules only')
ck(matrix['remaining_scope_unknown_for_other_products'] is True,'Other catalog readiness explicitly unknown')
ck(all(v==0 for v in matrix['collector_calls'].values()),'No new tests/models/builds/normative source checks/merges claimed')
for name,row in mods.items():
 ck(bool(re.fullmatch('[0-9a-f]{40}',row['working_head'])) and bool(re.fullmatch('[0-9a-f]{40}',row['buyer_snapshot_sha'])),'Full40 source and working heads',name)
 gates={g['gate']:g for g in row['remaining_gates']}
 ck(gates['official_normative_currentness']['status']=='NOT_VERIFIED' and gates['human_legal_acceptance']['status']=='NOT_PERFORMED','Legal currentness/human gates remain open',name)
 ck(gates['release_owner_main_deploy_live_price_SKU_payment']['status']=='OPEN_NOT_AUTHORIZED_BY_TECHNICAL_ACCEPTANCE','Release owner gate remains open',name)
s1=mods['S1'];full=data['s1-full6077'];comp=data['s1-composition-a774'];narrow=data['s1-narrow-header'];visual=data['s1-header-visual'];tech=s1['technical']
ck(tech['full105_and_two_complete_builds_source_sha']==full['actual_working_head']==comp['base_full105_source']=='6077a5d6cdba42cbef6f2452b799b5c118f8c5d2','105 tests bind only6077')
ck(full['tests']['passed']==105 and len([x for x in full['runs'] if x['name'].startswith('build-') and x['exit_code']==0])==2,'105 and two full build receipts actual')
ck(tech['full_suite_on_current_head'] is False and comp['full_suite_rerun'] is False and comp['full105_applies_to6077_only'] is True,'No105 acceptance upgraded to a774')
ck(s1['buyer_snapshot_sha']==comp['actual_working_head']=='a77422195c2c68281a7797ad99f9f6b70426d740','Current S1 buyer composition a774')
ck(tech['new_paragraph_checks']==narrow['tests'] and tech['new_doc03_sha256']==narrow['source_doc03_sha256']==comp['doc03_sha256']==visual['source_doc03_sha256'],'New03 narrow2checks/bytebinding exact')
ck(tech['composition_unchanged_paths']==len(comp['unchanged6077_bytes'])==162 and all(x['byte_exact_against6077'] for x in comp['unchanged6077_bytes']),'162 unchanged composition receipt')
ck(tech['header_visual_changed_pages']==visual['changed_pages_root_seen']==[8,9,10,11] and visual['readable_reflow'] is True and visual['manual_excel_gui_pass'] is False,'Changed03visual scope without Excel manual upgrade')
lineage=data['s1-excel-lineage-record']
for row in s1['excel_lineage']:
 old=lineage[row['file']]
 ck(row['original_owner_sha256']==old['owner_sha256'] and row['reviewed_correction_sha256']==old['correction_sha256'] and row['review_report_sha256']==old['review_report_sha256'],'S1 oldowner vs newcorrection exact lineage',row['file'])
 ck(row['independent_exact_correction_review']==old['independent_review']=='ACCEPT' and row['owner_approval_of_new_text']==old['owner_approval_of_new_text'] is False and old['native_excel_acceptance_of_new_text'] is False,'Independent correction review distinct from owner/manual pending',row['file'])
native04=next(x for x in full['all_output_checks'] if x['file']=='04-uchet-raschetov-i-otpravok.xlsx')
ck(native04['sha256']=='f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9' and native04['owner_native_exact'] is True and narrow['native04_changed'] is False,'S1 native04 preserved without original/manual print PASS')
ck(any(g['gate']=='owner_excel_acceptance_of_new02_08_text' and g['status']=='PENDING' for g in s1['remaining_gates']),'S1 changed02/08 owner acceptance pending')
# Citation review fields are linked to independently accepted exact receipts, not filename or author READY alone.
reviewids={'S1':'s1-citation-review','P2':'p2-citation-independent','P3':'p3-citation-current-independent','P5':'p5-citation-independent'}
for name,ident in reviewids.items():
 c=mods[name]['citation'];proof=data[ident]
 ck(proof['status']=='ACCEPT_FACTUAL_INVENTORY' and not proof['errors'] and c['inventory_sha256']==proof['inventory_sha256'] and c['source_sha']==proof['source_sha'],'Citation factual ACCEPT/hash/source exact independent receipt',name)
 ck(proof['source_currentness']=='NOT_VERIFIED' and proof['human_legal']=='NOT_PERFORMED','Citation review not legal currentness/human approval',name)
 if name in ['S1','P5']:ck(c['checks']==proof['checks'] and c['occurrences']==proof['literal_occurrences_checked'] and c['groups_not_norms']==proof['dedup_groups_checked'] and c['unresolved_markers_not_defects']==proof['unresolved_markers_checked'],'Citation counts exact',name)
 elif name=='P3':ck(c['independent_checks']==proof['checks']==396 and c['literal_occurrences']==proof['literal_occurrences_checked']==15 and c['unresolved_markers_not_defects']==proof['unresolved_markers_checked']==34,'P3 corrected counts exact')
 else:ck(c['checks_base']==proof['checks']==137 and c['checks_supplemental']==proof['supplemental_checks']==18 and c['checks_total']==155 and c['native_text_units']==proof['total_independent_native_text_units']==450 and len(proof['pdfs'])==c['PDFs']==3 and sum(x['physical_pages'] for x in proof['pdfs'])==c['PDF_physical_pages']==6,'P2 actual137+18/450/3PDF6pages exact')
# Accepted existing PHP/composition receipts establish packaging only.
for name,ident in [('P2','p2-actual-php'),('P3','p3-actual-php'),('P5','p5-actual-php')]:
 t=mods[name]['technical'];p=data[ident];ck(t['status']==p['status'],'Technical packaging status exact receipt',name)
 if name=='P2':ck(t['PHP_members']==p['count']==15 and t['zip_sha256']==p['archive_sha256'] and t['CRC_failure_member']==p['crc_failure_member'] is None,'P2 PHP15/ZIP/CRC exact')
 elif name=='P3':ck(t['PHP_members']==p['zip']['members']==11 and t['zip_sha256']==p['zip']['sha256'] and t['zip_bytes']==p['zip']['bytes'],'P3 PHP11/ZIP exact')
 else:ck(t['PHP_members']==p['member_count']==11 and t['zip_sha256']==p['zip_sha256'] and t['zip_bytes']==p['zip_bytes'] and t['native04_05_exact']==p['native04_05_exact'] is True,'P5 PHP11/native/ZIP exact')
p2comp=data['p2-composition476'];p2merge=data['p2-merge476'];ck(mods['P2']['working_head']==p2comp['merged_working_sha']==p2merge['merge_commit_sha'] and p2merge['merged'] is True and p2comp['buyer_config_generator_exact_unchanged'] is True,'P2 actual476 merge and bytefidelity')
p3comp=data['p3-composition478'];ck(mods['P3']['working_head']==p3comp['actual_working_head'] and len(p3comp['all15_input_blobs_exact'])==mods['P3']['technical']['all15_input_blobs_exact']==15 and p3comp['all27_documentary_paths_exact'] is True,'P3 actual478 packaging composition')
p5comp=data['p5-citation-composition480'];ck(mods['P5']['working_head']==mods['P5']['citation']['working_merge_sha']==p5comp['actual_merge_sha']=='7123d44353b9a3d21c29851b10e9addc6080360d' and mods['P5']['citation']['output_sha']==p5comp['source_head'] and len(p5comp['unchanged_inputs'])==17 and len(p5comp['documentary_exact_paths'])==30,'P5 actual480 exact merge17inputs30proofs')
s1comp=data['s1-citation-merged-composition'];ck(s1['working_head']==s1['citation']['working_merge_sha']==s1comp['actual_merged_sha'] and s1['citation']['output_sha']==s1comp['accepted_output_sha'] and s1comp['all11_buyerbytes_unchanged'] is True,'S1 actual479 exact merge')
draft=data['p3-citation-draft481'];ck(mods['P3']['citation']['draft_head_sha']==draft['head_sha'] and mods['P3']['citation']['draft_base_sha']==draft['base_sha'] and mods['P3']['citation']['actual_merge_status']=='PENDING','P3 Draft481 snapshot not falsely merged')
ck(mods['P2']['citation']['status'].endswith('_PERSISTENCE_PENDING') and any(g['gate']=='accepted_factual_inventory_documentary_persistence' and g['status']=='PENDING' for g in mods['P2']['remaining_gates']),'P2 acceptance distinct from pending persistence')
stop=data['p2-existing-stop-report']
for g in mods['P2']['remaining_gates']:
 if g['gate'].startswith('STOP-P2'):
  ck(g['gate'] in stop and g['file'] in stop and g['status']=='OPEN','P2 existing STOP gate preserved',g['gate'])
ck(data['handoff']['official_currentness'].startswith('NOT_VERIFIED') and data['handoff']['legal_human']=='NOT_PERFORMED' and data['handoff']['main_deploy_sale_ready'] is False,'Common open legal/release source binding')
md=(F/'completion-gates-matrix.md').read_text()
for needle in ['только база 6077','Новый текст 02/08 ещё не принят','STOP форм 02/04/05','SALE_READY не заявлен','remaining_scope_unknown_for_other_products=true']:
 ck(needle in md,'MD qualification preserved',needle)
for n,h in known.items():ck(sha((F/n).read_bytes())==h,'Collector still frozen after review',n)
summary={'status':'ACCEPT_FACTUAL_FOUR_MODULE_SNAPSHOT' if not errors else 'CHANGES_REQUESTED_FACTUAL_MATRIX','snapshot_utc':matrix['observed_utc'],'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'matrix_sha256':known['completion-gates-matrix.json'],'md_sha256':known['completion-gates-matrix.md'],'input_manifest_sha256':known['input-manifest.json'],'inputs_checked':len(rows),'checks':len(checks),'errors':errors,'scope':['S1','P2','P3','P5'],'currentness':'NOT_VERIFIED','human_legal':'NOT_PERFORMED','release_owner_gate':'OPEN','limitation':'Accepted as exact 17:15 frozen snapshot. P3/P2 citation persistence shown PENDING; later merge/Draft receipts require separate refreshed snapshot, not retroactive update. No all-catalog readiness or approval by filename.','calls':{'models':0,'tests':0,'extraction':0,'builds':0,'product_or_zip_mutations':0,'network':0}}
(R/'review-input-pins.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2));(R/'review-check-details.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));(R/'independent-review-receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(R/'independent-review-report.md').write_text('# Independent four-module factual snapshot QA\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
