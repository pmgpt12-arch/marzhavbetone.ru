from pathlib import Path
from zipfile import ZipFile
import json,hashlib,shutil,subprocess,xml.etree.ElementTree as E
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';ROOT=Q.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(n):return json.loads((Q/n).read_text())
def save(n,d):(Q/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
protected=json.loads((Q.parent/'integration-20261022/MANIFEST_VERIFIED_FILES.json').read_text())['files'];new=load('PAID_CANDIDATE_MANIFEST.json');mapping=load('product-map.json');source={r['path']:r for r in load('SOURCE_INVENTORY.json')};changed={r['path']:r for r in new}
assert len(protected)==13 and len(changed)==17
for f in protected:
 assert sha((R/f['path']).read_bytes())==f['accepted_sha256']
 assert f['path']not in changed
archives=[];total=0;different=0
for a in load('builder-receipt.json')['archives']:
 path=Path(a['path']);assert sha(path.read_bytes())==a['sha256'];root=Q/'package-sources/products-storage'/a['dir'];expected={str(p.relative_to(root)):p for p in root.rglob('*')if p.is_file()and p.name not in {'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'}};members=[]
 with ZipFile(path)as z:
  assert z.testzip()is None;assert len(z.namelist())==len(set(z.namelist()));assert set(z.namelist())==set(expected)
  for name in sorted(z.namelist()):
   assert not any(x in name.lower()for x in ['-filled','manual-check','qa-report','native-case']);b=z.read(name);assert b==expected[name].read_bytes();rel='products-storage/'+a['dir']+'/'+name;is_changed=rel in changed
   if is_changed:assert sha(b)==changed[rel]['sha256'];different+=1
   else:assert sha(b)==source[rel]['sha256']
   if name.endswith(('.xlsx','.docx')):
    import io
    with ZipFile(io.BytesIO(b))as o:
     assert o.testzip()is None
     for n in o.namelist():
      if n.endswith(('.xml','.rels')):E.fromstring(o.read(n))
   members.append({'name':name,'sha256':sha(b),'bytes':len(b),'changed_candidate':is_changed,'accepted_unchanged':any(x['path']==rel for x in protected)})
  total+=len(members)
 archives.append({**a,'member_count':len(members),'members':members,'technical_status':'PACKAGE_VERIFIED','product_status':'FULL_PRODUCT_QA_CANDIDATE'if a['sku']=='P8'else'RELEASE_BLOCKED','public_source_changed':False})
assert len(archives)==13 and total==172 and different==17
save('CANDIDATE_ARCHIVES.json',{'builder':'mvb_build_product_zip','archives':archives,'files':total,'new_paid_versions':different,'unchanged_paid_versions':total-different,'protected_accepted':13,'native_office_new_versions':'BLOCKED','publication':False})
seed=ROOT/'tools/nsp-product-audit-fixes-20261021/remaining-review-20261022';seed_manifest=json.loads((seed/'docx-candidate-manifest.json').read_text());free_seed=json.loads((seed/'free-candidate-manifest.json').read_text());held=[]
for f in seed_manifest:
 p=seed/'candidates'/f['path'];assert sha(p.read_bytes())==f['candidate_sha256'];held.append({'path':f['path'],'sha256':f['candidate_sha256'],'status':'RELEASE_BLOCKED','reason':'Native Word 2016 receipt absent','included_in_buyer_archives':False})
for f in free_seed:
 p=seed/f['candidate_relative_path'];assert sha(p.read_bytes())==f['candidate_sha256'];held.append({'path':str(p.relative_to(seed/'candidates')),'sha256':f['candidate_sha256'],'status':'RELEASE_BLOCKED','reason':'Native Excel 2016 save/reopen/print absent','included_in_buyer_archives':False})
assert len(held)==6;save('HELD_SIX.json',held)
free_inventory=[]
for ref in load('FREE_SOURCE_ARCHIVES.json'):
 p=R/ref['path'];assert sha(p.read_bytes())==ref['sha256']
 if p.suffix=='.zip':
  with ZipFile(p)as z:
   assert z.testzip()is None
   for n in z.namelist():
    if not n.endswith('/'):free_inventory.append({'giveaway':p.name,'member':n,'sha256':sha(z.read(n))})
 else:free_inventory.append({'giveaway':p.name,'member':p.name,'sha256':sha(p.read_bytes())})
assert len(free_inventory)==48;save('FREE_SOURCE_MEMBERS.json',free_inventory)
cases=load('lo-regression-results.json');after=[x for x in cases if x['phase']=='after'];before=[x for x in cases if x['phase']=='before'];assert len(after)==39 and all(x['expectations_pass']for x in after);assert len(before)==9 and all(not x['expectations_pass']for x in before)
ledger=[]
for f in protected:ledger.append({'id':'accepted-'+f['sku']+'-'+f['filename'],'sku':f['sku'],'file':f['path'],'base_sha256':f['accepted_sha256'],'new_sha256':f['accepted_sha256'],'status':'CLOSED_PREVIOUS_ACCEPTANCE_REUSED','release_blocking':False,'test':f['acceptance'],'reason':'Exact accepted bytes unchanged; no repeat manual P8 checks'})
for pp in sorted((Q/'plans').glob('*.json')):
 p=json.loads(pp.read_text());f=next(x for x in new if x['path']=='products-storage/'+p['path']);tests=[x for x in after if x['issue']==p['issue']];old=next(x for x in before if x['issue']==p['issue'])
 ledger.append({'id':p['issue'],'sku':p['sku'],'file':f['path'],'cells':[e['sheet']+'!'+e['cell']for e in p['edits']],'base_sha256':f['source_sha256'],'new_sha256':f['sha256'],'priority':'A'if p['sku']in ['P5','P9']else'B','reproduction':{'scenario':old['case'],'previous_actual':old['checks']},'proposed_result':p['issue'],'test':{'engine':'LibreOffice full workbook recalculation','scenarios':len(tests),'pass':True},'status':'CANDIDATE_REGRESSION_PASS_OFFICE_BLOCKED','release_blocking':True,'legal_basis':'127-ФЗ ст. 5 п. 1–2; не автоматическая квалификация долга'if p['sku']=='P9'else'Operational completeness/control; legal applicability remains in instructions'})
for f in load('content-manifest.json'):
 ledger.append({'id':'content-'+Path(f['path']).stem,'sku':next(k for k,v in mapping.items()if '/'+v+'/'in f['path']),'file':f['path'],'base_sha256':f['base_sha256'],'new_sha256':f['sha256'],'status':'CONTENT_QA_CANDIDATE'if f['path'].endswith('.txt')else'CONTENT_RENDER_CANDIDATE_OFFICE_BLOCKED'if f['path'].endswith('.docx')else'PDF_CONTENT_RENDER_CANDIDATE','release_blocking':not '/10-avans-'in f['path'],'legal_basis':'ГК РФ ст. 395 п. 4 / 409 / 410; 214-ФЗ ст. 11, 15.4, 15.5 ч. 4; 743 п. 3–4 as applicable','test':'Targeted text/links/examples and PDF/Word layout review; native Word pending for changed DOCX'})
for f in load('free-docx-manifest.json'):
 assert sha((Q/'candidates'/f['path']).read_bytes())==f['sha256']
 ledger.append({'id':'free-ks-'+f['member'],'sku':'FREE-vozvrat-ks','file':f['archive']+'!'+f['member'],'base_sha256':f['base_sha256'],'new_sha256':f['sha256'],'reproduction':'Wrong OKUD/KS-6 designation and unconditional accountant-signature statement in original text','test':'13 targeted replacements across two DOCX; assertion forbids obsolete accountant-signature claim; render pending native Word','legal_basis':'402-ФЗ ст. 9 ч. 2,4; Постановление Госкомстата №100: КС-2/КС-3/КС-6а','status':'CONTENT_RENDER_CANDIDATE_OFFICE_BLOCKED','release_blocking':True})
coverage=json.loads((seed/'COVERAGE.json').read_text())
for row in coverage['paid']:
 if row['sku']!='P8':ledger.append({'id':'full-product-'+row['sku'],'sku':row['sku'],'file':'products-storage/'+mapping[row['sku']],'status':'RELEASE_BLOCKED','release_blocking':True,'remaining':row['remaining'],'note':'Candidate fixes above address selected issues only; full buyer/legal/native acceptance is not inferred from ZIP assembly.'})
ledger.append({'id':'P8-complete-walkthrough','sku':'P8','file':'products-storage/'+mapping['P8'],'status':'FULL_PRODUCT_QA_CANDIDATE','release_blocking':False,'test':'5 old DOCX native SHA proofs reused + 3 accepted DOCX + 2 owner-accepted XLSX; Start updated with applicability/example/support/links; 11-member full ZIP verified','publication':False})
for f in held:ledger.append({'id':'held-'+f['path'],'sku':'P7/T2/FREE','file':f['path'],'new_sha256':f['sha256'],'status':f['status'],'release_blocking':True,'remaining':f['reason']})
for row in coverage.get('free',[]):ledger.append({'id':'free-product-'+str(row.get('material',row.get('archive',len(ledger)))),'sku':'FREE','file':'downloads/'+row['material']+(''if row['material'].endswith('.pdf')else'.zip'),'status':'RELEASE_BLOCKED','release_blocking':True,'remaining':row})
save('ISSUE_LEDGER.json',{'source_head':'203b39a390c09157adcd6760aa04318df332bedc','scope':'Partial substantive corrections, exact-byte reuse, full technical candidate packaging; not product release acceptance','issues':ledger})
save('CANDIDATE_ARTIFACT_REGISTRY.json',{'role':'nominated_candidate','canonical_registry_unchanged':True,'canonical_registry_check':'PASS; proof/registry-check.log','historical_inventory_unchanged':True,'candidates':new+load('free-docx-manifest.json'),'held_unaccepted':held,'archives':'CANDIDATE_ARCHIVES.json','native_office_new_versions':'BLOCKED_NO_FRESH_OFFICE_WORKER'})
save('VERIFICATION_RECEIPT.json',{'status':'PARTIAL_CORRECTIONS_VERIFIED_RELEASE_BLOCKED','source_head':'203b39a390c09157adcd6760aa04318df332bedc','protected_files':13,'new_candidates':19,'held_six':6,'archives':13,'archive_members':172,'changed_paid_members':17,'unchanged_paid_members':155,'new_formula_scenarios':39,'new_formula_pass':39,'old_version_reproductions':9,'old_version_reproduced':9,'calculation_engine':'LibreOffice; NOT native Microsoft Excel','registry_check':'PASS','free_source_giveaways':11,'free_source_files':48,'fresh_native_office':'BLOCKED','P8':'FULL_PRODUCT_QA_CANDIDATE','main_writes':0,'public_writes':0,'payment_price_secret_system_writes':0,'source_masters_changed':False})
print('VERIFIED',json.dumps(load('VERIFICATION_RECEIPT.json'),ensure_ascii=False))
