import pathlib,subprocess,json,hashlib,datetime,collections
S='/home/denis/projects/marzhavbetone.ru';R=pathlib.Path(__file__).parent;PIN='264d75a06d59de82602dc1bcef347913c44cc648'
def git(*a):return subprocess.check_output(['git','-C',S,*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,v):(R/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
catalog=json.loads((R/'configured-catalog.json').read_text()); config=(R/'products-config.php').read_bytes()
assert git('show',PIN+':products-config.php')==config
configtext=config.decode();assert "$service = ['.htaccess', '00-PISMO-POSLE-POKUPKI.txt', 'MANIFEST.md'];" in configtext
allfiles=[p for p in git('ls-tree','-r','--name-only','-z',PIN,'products-storage').decode().split('\0') if p]
dirs=sorted({p.split('/')[1] for p in allfiles if len(p.split('/'))>2})
rows=[]
for sku,cat in catalog.items():
 prefix='products-storage/'+cat['dir']+'/'
 paths=[p for p in allfiles if p.startswith(prefix)]
 assert paths,(sku,prefix)
 payload=[];service=[]
 for p in paths:
  raw=git('show',PIN+':'+p);row={'path':p,'relative_name':p[len(prefix):],'git_blob':git('rev-parse',PIN+':'+p).decode().strip(),'sha256':sha(raw),'size':len(raw),'source_sha':PIN}
  (service if pathlib.Path(p).name in {'.htaccess','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md'} else payload).append(row)
 rows.append({'sku':sku,'name':cat['name'],'dir':cat['dir'],'zip_name':cat['zip'],'configured_source_sha':PIN,'role':'core_paid' if sku.startswith('p') else 'entry_paid' if sku.startswith('t') else 'test','main_payload_candidate_count':len(payload),'members':payload,'excluded_service':service,'membership_status':'SOURCE_ELIGIBLE_DRY_INVENTORY_BY_UNCHANGED_PHP_POLICY_NOT_ACTUAL_ZIP','acceptance_status':'UNKNOWN_NOT_INFERRED_FROM_MAIN_OR_FILENAMES'})
write('module-input-hashes.json',{'source_sha':PIN,'config_sha256':sha(config),'modules':rows,'storage_directories':dirs,'storage_dir_count':len(dirs),'configured_p_keys':[x['sku'] for x in rows if x['role']=='core_paid'],'configured_t_keys':[x['sku'] for x in rows if x['role']=='entry_paid'],'test_keys':[x['sku'] for x in rows if x['role']=='test'],'commented_p6_configured':False})
Q4=pathlib.Path('/home/denis/.local/state/claude-dispatcher/recovery-20261004')
pointers=[]
for local in [Q4/'p7-header-20261005/merge-409-receipt.json',Q4/'buyer-p7-20261005/merge-400-receipt.json',Q4/'buyer-p10-p12-20261005/merge-408-receipt.json']:
 data=json.loads(local.read_text());pointers.append({'path':str(local),'sha256':sha(local.read_bytes()),'source':data['after'],'decision_observed':data['decision'],'scope':'Existing exact narrow merge proof; does not mean module legal/release readiness'})
for name in json.loads((R/'main-candidate-pointers.json').read_text()):
 raw=git('show',PIN+':'+name);pointers.append({'path':name,'source_sha':PIN,'sha256':sha(raw),'git_blob':git('rev-parse',PIN+':'+name).decode().strip(),'scope':'Existing report text observed, source/acceptance/currentness not inherited'})
write('existing-evidence-pointers.json',pointers)
existing_four={'p1':'S1 working1d44… owner/sourceexact proof maintained byroot; main listing is superseded baseline','p2':'P2 workingd5cef… documentaryincrementpending; no reruns','p3':'P3 working7cdf… PR481 pending; no reruns','p5':'P5 exact7123d44353b9a3d21c29851b10e9addc6080360d, packaging/native/factualinventory accepted only'}
selected=['p4','p8','p9','p11']
tasks=[]
for sku in selected:
 module=next(x for x in rows if x['sku']==sku)
 task={'task_id':'readonly-ooxml-'+sku+'-264d75','execution_pattern':'one_shot','primary_result':'Exact '+sku+' buyer-source OOXML integrity/schema factual inventory','feedback_loop_required':False,'checkpoint_policy':'verified_only','source_sha':PIN,'module_dir':module['dir'],'required_inputs':module['members'],'contracts':json.loads((R/'canonical-inputs.json').read_text()),'executor':'Python/CLI only, no model; proposed isolated pool max4','scope':'Read-only native DOCX/XLSX ZIP CRC/duplicate parts/internal relationships/content-types/cell-formula schema inventory; all member before/after hash proof; signal numeric #{2,} only, not rendered clipping verdict','duplicate_gate':'Before execution reuse any existing exact samehash/scope receipt; located P4 composition/render reports are historical and must not trigger repeated tests/render/ZIP','output_dir':'/home/denis/.local/state/claude-dispatcher/recovery-20261005/'+sku+'-readonly-ooxml-264d75','acceptance':'Exact manifest membership/inputhash; source bytes unchanged; evidence every file including nonOOXML applicability; deterministic structural observations independently reviewable','not_claimed':['accepted repackaging source','actual PHP ZIP proof','formula correctness','layout/readability','legal/financial/currentness/human acceptance','sale readiness'],'stop':'Missing exact input or mismatch/duplicate proof; preserve factual evidence, do not repair products','api_usd':0,'status':'PROPOSED_READY_INPUTS_PENDING_ROOT_REVIEW_AND_DUPLICATE_GATE'}
 tasks.append(task)
write('next-atomic-passports.json',{'selected_parallel_pool':selected,'tasks':tasks,'remaining_next':['p13 same readonly scope after capacity or independent root dispatch','p7 current narrow receipts already exist; use exacta47f... source after declared accepted-fix mapping, do not rerun header acceptance','p10/p12 shared-document boundary already reviewed2aef...; use existing exact paired source proof before new citation-only task','t1-t6 remain separately configured entries, not reclassified as completed core products'],'known_four_no_repeat':existing_four,'expert_routes':'Legal/financial semantics and statutorycurrentness require separate exact expert/official/human gate; free models can draft only checkable passports or triage after exact inputs/catalog, never acceptance'})
lines=['# Factual configured catalog and next bounded tasks','','Cached source '+PIN+'; configuration read through unchanged actual PHP mvb_products(). No price strategy or acceptance inferred.','','12 core p-keys +6 entry t-keys +1 test key; p6 commented, not configured. Storage directories: '+str(len(dirs))+'; these are not live SKU counts or ready products. Source-eligible membership follows exact existing PHP exclusions; no archive built.','','| SKU | Actual dir | Source-eligible buyer files | Status |','|---|---|---|---|']
for row in rows:lines.append('| '+row['sku']+' | '+row['dir']+' | '+str(len(row['members']))+' | '+('Existing newer working evidence; no rerun' if row['sku'] in existing_four else 'Factual baseline; acceptance unknown')+' |')
lines.extend(['','Next proposed isolated Python pool: '+', '.join(selected)+'. Exact input manifests/passports are complete; root review and duplicate gate precede dispatch. Read-only OOXML package/schema observations only; no formula correctness, rendering or legal verdict.','','P4 existing3mainreports are pinned as historical observations. P7 current narrow merge409a47f868... and P10/P12 boundary merge4082aef70... were found; avoid repeating their tested buyer scenarios. No other exact candidate proof was inferred from a filename.','','Capacity snapshot in capacity.json:20 logical CPUs, availablememory26.786GB at observation; absent PATH model tools/GPU utility do not prove no GPU. CLI work needs no local model or API spend.','','No source/product/Git mutation, release, deployment, official-source lookup or model invocation occurred.'])
(R/'catalog-next-queue.md').write_text('\n'.join(lines)+'\n')
receipt={'status':'FACTUAL_CATALOG_AND_INPUT_READY_SHORTLIST_PENDING_ROOT_REVIEW','source_sha':PIN,'configured_entries':len(rows),'core_paid_keys':12,'entry_paid_keys':6,'test_keys':1,'storage_dirs':len(dirs),'proposed_pool':selected,'per_pool_ooxml_candidates':{x['sku']:sum(pathlib.Path(y['path']).suffix in {'.docx','.xlsx'} for y in x['members']) for x in rows if x['sku'] in selected},'config_hash_unchanged':sha(git('show',PIN+':products-config.php'))==sha(config),'no_product_or_git_mutation':True,'model_calls':0,'api_usd':0,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'limits':'Sourceeligible membership only, no live/accepted source readiness inferred'}
write('verification-receipt.json',receipt)
write('artifact-sha256.json',{p.name:sha(p.read_bytes()) for p in sorted(R.iterdir()) if p.is_file() and p.name!='artifact-sha256.json'})
print(json.dumps(receipt));print('manifest_sha256',sha((R/'module-input-hashes.json').read_bytes()));print('passports_sha256',sha((R/'next-atomic-passports.json').read_bytes()))
