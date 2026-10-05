"""Independent inspection of EXISTING baseline PHP archives; never executes PHP/build/parsers."""
from pathlib import Path,PurePosixPath
import json,hashlib,zipfile,binascii,collections,subprocess,stat,time,datetime,sys,traceback
O=Path(__file__).resolve().parent
A=O.parent/'next-baseline-delivery-queue-20261005'
SITE='/home/denis/projects/marzhavbetone.ru'
PIN='264d75a06d59de82602dc1bcef347913c44cc648'
LANES=[['p4','t2','t3'],['p7','p8','p11'],['p9','p10','p12'],['p13','t1','t4','t5','t6']]
start=time.monotonic();checks=[];errors=[];archives=[];members=[];sources=[];lane_facts=[];runtime=set()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check(ok,label,**detail):
 checks.append(label)
 if not ok:errors.append(dict(check=label,**detail))
def save(name,v):(O/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def gitraw(path):return subprocess.check_output(['git','-C',SITE,'show',PIN+':'+path],timeout=15)
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
passport=json.loads((O/'passport.json').read_text())
def main():
 for p,h in passport['input_files'].items():check(sha(Path(p).read_bytes())==h,'frozen_authorized_input_hash',path=p)
 ready=json.loads((A/'actual/READY.json').read_text());m=json.loads((A/'actual/selected-input-manifest.json').read_text());sums=json.loads((A/'SHA256SUMS.json').read_text())
 check(ready['source_sha']==m['source_sha']==PIN and ready['archives']==14 and ready['member_bindings']==135,'actual_READY_exact_baseline_scope')
 full=json.loads(Path(next(p for p in passport['input_files'] if p.endswith('module-input-hashes.json'))).read_text())
 selected={k for lane in LANES for k in lane};modules={x['sku']:x for x in m['modules']};accepted={x['sku']:x for x in full['modules'] if x['sku'] in selected}
 check(modules==accepted and set(modules)==selected and sum(len(x['members']) for x in modules.values())==135,'selected_manifest_exact_original_eligible135')
 check(m['parent_manifest_sha256']==passport['input_files'][next(p for p in passport['input_files'] if p.endswith('module-input-hashes.json'))],'parent_manifest_pin')
 for rel,h in sums.items():
  p=A/rel;check(p.resolve().is_relative_to(A.resolve()) and p.is_file() and sha(p.read_bytes())==h,'frozen_original_execution_file_hash',path=rel)
 process=json.loads((A/'execution-receipt.json').read_text());auth=json.loads((A/'ROOT_AUTHORIZATION.json').read_text())
 check(process['exit_code']==0 and process['status']=='COMPLETED_SUCCESS' and process['runner_pid']==1980739 and process['native_parent_pid']==1980738,'actual_once_runner_exit_receipt')
 check(process['log_sha256']==sha((A/'execution.log').read_bytes()),'actual_runner_log_hash')
 for name,h in auth['pins'].items():check(sha((A/name).read_bytes())==h,'root_authorized_dependency_hash',path=name)
 config=gitraw('products-config.php');check(sha(config)==m['config_sha256']=='7f7cca1e7344a3ad69041049b926e2a9766de1ba93d9de3de70641875261f7fb','exact_unmodified_config_source_bytes')
 for index,skus in enumerate(LANES,1):
  L=A/'actual'/('lane-'+str(index));before=json.loads((L/'source-before.json').read_text());after=json.loads((L/'source-after.json').read_text());lr=json.loads((L/'lane-receipt.json').read_text())
  check(before==after and lr['skus']==skus and lr['all_source_copies_before_after_exact'] is True,'lane_source_before_after_identity',lane=index)
  copied={str(p.relative_to(L/'sources')):sha(p.read_bytes()) for p in (L/'sources').rglob('*') if p.is_file()}
  check(copied==before and len(copied)==lr['copied_source_file_count'],'all_copied_source_paths_hashes_exact',lane=index)
  check((L/'products-config.php').read_bytes()==config,'each_lane_raw_config_exact',lane=index)
  for path,h in before.items():
   raw=gitraw(path);check(sha(raw)==h and (L/'sources'/path).read_bytes()==raw,'all_copied_source_blobs_immutable_baseline',lane=index,path=path)
   sources.append({'lane':index,'path':path,'sha256':h,'git_blob':blob(raw)})
  lane_archives=[]
  for sku in skus:
   module=modules[sku];p=L/'delivery'/module['zip_name'];r=json.loads((L/(sku+'-receipt.json')).read_text());ex=json.loads((L/(sku+'-execution.json')).read_text())
   actual=json.loads(ex['stdout']);runtime.add((actual['php_version'],actual['zip_extension']))
   check(ex['returncode']==0 and ex['stderr']=='' and actual==r['actual_php'],'actual_PHP_exit_stdout_receipt',sku=sku)
   check(r['source_sha']==PIN and r['sku']==actual['sku']==sku and actual['dir']==module['dir'] and actual['zip_name']==module['zip_name'] and Path(actual['path'])==p,'configured_actual_archive_identity',sku=sku)
   check(r['approved_delivery'] is False and r['sale_ready'] is False,'baseline_acceptance_qualification_preserved',sku=sku)
   archive_hash=sha(p.read_bytes());check(archive_hash==r['zip_sha256']==sums[str(p.relative_to(A))] and p.stat().st_size==r['zip_bytes'],'actual_archive_hash_size',sku=sku)
   expected={x['relative_name']:x for x in module['members']};reported={x['name']:x for x in r['members']}
   check(len(expected)==len(module['members'])==module['main_payload_candidate_count']==r['count'] and set(reported)==set(expected),'exact_configured_expected_member_count',sku=sku)
   member_records=[]
   with zipfile.ZipFile(p) as z:
    infos=z.infolist();names=[x.filename for x in infos]
    check(len(names)==len(set(names))==len(expected) and set(names)==set(expected),'archive_central_directory_exact_unique_membership',sku=sku)
    for info in infos:
     name=info.filename;q=PurePosixPath(name);mode=(info.external_attr>>16)&0xffff
     safe=bool(name) and not name.startswith(('/','\\')) and '\\' not in name and '\0' not in name and ':' not in name and all(x not in ('..','.') for x in name.split('/')) and not q.is_absolute() and not info.is_dir() and not info.flag_bits&1 and stat.S_IFMT(mode) in (0,stat.S_IFREG)
     check(safe,'safe_regular_readable_member_name',sku=sku,name=name)
     raw=z.read(info);crc=binascii.crc32(raw)&0xffffffff;h=sha(raw);item=expected[name];observed=reported[name]
     check(crc==info.CRC and format(crc,'08x')==observed['crc32'],'raw_member_CRC_central_directory',sku=sku,name=name)
     check(h==item['sha256']==observed['sha256'] and len(raw)==item['size']==info.file_size==observed['bytes'],'raw_member_exact_frozen_source_hash_size',sku=sku,name=name)
     check(blob(raw)==item['git_blob']==observed['source_git_blob'] and before[item['path']]==h,'raw_member_Gitblob_and_copied_source_binding',sku=sku,name=name)
     record={'sku':sku,'archive':str(p),'name':name,'source_path':item['path'],'sha256':h,'bytes':len(raw),'crc32':format(crc,'08x'),'source_git_blob':item['git_blob']}
     member_records.append(record);members.append(record)
    check(r['CRC_failure_member'] is None,'author_CRC_receipt_matches_actual',sku=sku)
   check(sha(p.read_bytes())==archive_hash,'archive_unchanged_after_inspection',sku=sku)
   archive={'lane':index,'sku':sku,'path':str(p),'archive_name':p.name,'sha256':archive_hash,'bytes':p.stat().st_size,'member_count':len(member_records),'all_member_CRC_hashes_exact':True}
   archives.append(archive);lane_archives.append(p.name)
  check(set(lane_archives)=={p.name for p in (L/'delivery').glob('*.zip')},'all_actual_delivery_archives_exact_lane_scope',lane=index)
  post={str(p.relative_to(L/'sources')):sha(p.read_bytes()) for p in (L/'sources').rglob('*') if p.is_file()}
  check(post==before==after and (L/'products-config.php').read_bytes()==config,'postreview_source_config_bytes_unchanged',lane=index)
  lane_facts.append({'lane':index,'skus':skus,'copied_source_file_count':len(before),'eligible_archive_members':sum(len(modules[k]['members']) for k in skus)})
 check(len(archives)==14 and len(members)==135,'actual_total14archives135bindings')
 check(len(runtime)==1,'actual_PHP_runtime_receipts_consistent')
try:main()
except Exception as exc:
 errors.append({'check':'runtime_exception','exception':type(exc).__name__,'message':str(exc)})
 (O/'exception.log').write_text(traceback.format_exc())
save('actual-archive-facts.json',archives);save('actual-member-facts.json',members);save('source-copy-facts.json',sources)
result={'status':'ACCEPT_ISOLATED_BASELINE_ACTUAL_PHP_ZIP_BYTES' if not errors else 'REVISE_REQUIRED','execution_pattern':'one_shot','source_sha':PIN,'command':passport['actual_command'],'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'checks':len(checks),'error_count':len(errors),'errors':errors,'actual_archives':len(archives),'actual_member_bindings':len(members),'copied_source_files_including_excluded_metadata':len(sources),'lanes':lane_facts,'captured_runtime_receipts':[{'PHP':p,'ZipArchive_extension':z} for p,z in sorted(runtime)],'runtime_binary_SHA':'NOT_CAPTURED_NOT_CLAIMED','author_runner_executed_by_QA':False,'PHP_calls_by_QA':0,'OOXML_or_citation_parser_calls_by_QA':0,'model_calls':0,'api_usd':0,'script_sha256':sha(Path(__file__).read_bytes()),'archive_facts_sha256':sha((O/'actual-archive-facts.json').read_bytes()),'member_facts_sha256':sha((O/'actual-member-facts.json').read_bytes()),'source_copy_facts_sha256':sha((O/'source-copy-facts.json').read_bytes()),'qualification':'Frozen cached baseline264d75 actual archives and exact bytes only; not approved current repackaging/live delivery/legal/formula/layout/manualExcel/release/SaleReady','not_claimed':passport['not_claimed']}
save('independent-review-receipt.json',result)
(O/'report.md').write_text('# Independent actual baseline ZIP inspection\n\n'+result['status']+' at '+PIN+'.\n\n'+str(len(checks))+' assertions, '+str(len(errors))+' errors. Four lanes,14 existing PHP archives,135 eligible member bindings. Native ZIP central directories/unique safe regular names/readability/raw CRC/SHA256/size/Gitblob checked against exact frozen selected original manifest. All copied source/config bytes before/after and frozen original execution dependencies/hash manifest verified; no builder run by QA.\n\nRuntime PHP/Zip extension versions are actual perSKU receipt observations; binary SHA not captured or claimed. Excluded MANIFEST metadata is source-preservation-only, never silently added to delivery membership.\n\nBaseline isolated archive bytes only, no current repackaging approval/live delivery/OOXML semantic/calculation/layout/legal/currentness/human/release/SaleReady verdict. No repeated structural/citation checks, render, Calc, general tests, PHPbuild or models.\n')
save('READY.json',{'status':result['status'],'receipt_sha256':sha((O/'independent-review-receipt.json').read_bytes()),'report_sha256':sha((O/'report.md').read_bytes()),'script_sha256':result['script_sha256']})
print(json.dumps(result,ensure_ascii=False));sys.exit(bool(errors))
