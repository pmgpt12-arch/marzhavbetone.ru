from pathlib import Path
import concurrent.futures,subprocess,hashlib,json,tarfile,io,zipfile,datetime,os
R=Path(__file__).resolve().parent
SITE='/home/denis/projects/marzhavbetone.ru'
SOURCE='264d75a06d59de82602dc1bcef347913c44cc648'
B=Path('/home/denis/.local/state/claude-dispatcher/recovery-20261005/catalog-next-queue-20261005-recovery/documentary-bundle')
MANIFEST_SHA='7ef66ed269183a671269c033d80b4c85f06eff53a452b4e4cd3a3a15b8b4e08e'
CONFIG_SHA='7f7cca1e7344a3ad69041049b926e2a9766de1ba93d9de3de70641875261f7fb'
LANES=[['p4','t2','t3'],['p7','p8','p11'],['p9','p10','p12'],['p13','t1','t4','t5','t6']]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def file_hashes(root):return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
def lane(index,skus,modules,config):
 out=R/'actual'/('lane-'+str(index));out.mkdir(parents=True,exist_ok=False)
 src=out/'sources';src.mkdir()
 dirs=['products-storage/'+modules[k]['dir'] for k in skus]
 archive=subprocess.check_output(['git','-C',SITE,'archive',SOURCE,*dirs],timeout=30)
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:
  for member in t.getmembers():
   target=src/member.name
   assert target.resolve().is_relative_to(src.resolve()) and not member.issym() and not member.islnk(),'UNSAFE_ARCHIVE_MEMBER'
   if member.isdir():target.mkdir(parents=True,exist_ok=True)
   elif member.isfile():
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(t.extractfile(member).read());target.chmod(0o444)
   else:raise AssertionError('UNEXPECTED_GIT_ARCHIVE_TYPE')
 (out/'products-config.php').write_bytes(config);(out/'products-config.php').chmod(0o444)
 for name in ['orders','delivery']:(out/name).mkdir()
 before=file_hashes(src);write(out/'source-before.json',before)
 results=[]
 for sku in skus:
  m=modules[sku];expected={v['relative_name']:v for v in m['members']}
  assert len(expected)==m['main_payload_candidate_count']
  for name,v in expected.items():assert sha((src/'products-storage'/m['dir']/name).read_bytes())==v['sha256']
  c=subprocess.run(['php',str(R/'build-one.php'),str(out),sku],capture_output=True,text=True,timeout=60)
  write(out/(sku+'-execution.json'),{'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr})
  assert c.returncode==0,(sku,c.stderr)
  actual=json.loads(c.stdout);p=Path(actual['path']);assert p.resolve().is_relative_to((out/'delivery').resolve())
  assert actual['dir']==m['dir'] and actual['zip_name']==m['zip_name'] and p.name==m['zip_name']
  with zipfile.ZipFile(p) as z:
   names=z.namelist();assert len(names)==len(set(names)) and set(names)==set(expected),'ZIP_MEMBERSHIP'
   assert z.testzip() is None,'ZIP_CRC'
   members=[]
   for name in names:
    v=expected[name];raw=z.read(name);info=z.getinfo(name);assert sha(raw)==v['sha256'] and len(raw)==v['size'],(sku,name,'MEMBER_BYTES')
    members.append({'name':name,'sha256':sha(raw),'bytes':len(raw),'crc32':format(info.CRC,'08x'),'source_git_blob':v['git_blob']})
  receipt={'status':'PASS_ISOLATED_BASELINE_PHP_ZIP_BYTES','source_sha':SOURCE,'sku':sku,'actual_php':actual,'zip_sha256':sha(p.read_bytes()),'zip_bytes':p.stat().st_size,'members':members,'count':len(members),'source_originals_preserved':True,'CRC_failure_member':None,'approved_delivery':False,'sale_ready':False}
  write(out/(sku+'-receipt.json'),receipt);results.append(receipt)
 after=file_hashes(src);write(out/'source-after.json',after);assert before==after and sha((out/'products-config.php').read_bytes())==CONFIG_SHA
 write(out/'lane-receipt.json',{'status':'PASS_BASELINE_LANE','skus':skus,'all_source_copies_before_after_exact':True,'copied_source_file_count':len(before),'receipts':[k+'-receipt.json' for k in skus]})
 return results
if __name__=='__main__':
 assert (R/'ROOT_AUTHORIZATION.json').is_file(),'ROOT_SCOPE_AUTHORIZATION_REQUIRED'
 assert not (R/'actual').exists(),'NO_REPEAT_BUILD_OR_OVERWRITE'
 raw=(B/'module-input-hashes.json').read_bytes();assert sha(raw)==MANIFEST_SHA
 frozen=json.loads(raw);assert frozen['source_sha']==SOURCE
 selected={k for items in LANES for k in items};assert len(selected)==14
 modules={m['sku']:m for m in frozen['modules'] if m['sku'] in selected};assert set(modules)==selected and sum(len(m['members']) for m in modules.values())==135
 config=(B/'products-config.php').read_bytes();assert sha(config)==CONFIG_SHA
 assert subprocess.check_output(['git','-C',SITE,'rev-parse',SOURCE+'^{commit}'],text=True).strip()==SOURCE
 assert subprocess.check_output(['git','-C',SITE,'show',SOURCE+':products-config.php'])==config
 (R/'actual').mkdir();write(R/'actual/selected-input-manifest.json',{'source_sha':SOURCE,'parent_manifest_sha256':MANIFEST_SHA,'config_sha256':CONFIG_SHA,'modules':list(modules.values())})
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(lane,i+1,skus,modules,config) for i,skus in enumerate(LANES)]
  results=[future.result() for future in futures]
 assert sum(len(x) for x in results)==14 and sum(y['count'] for x in results for y in x)==135
 write(R/'actual/READY.json',{'status':'ACTUAL_BASELINE_PHP_ZIPS_READY_PENDING_INDEPENDENT_REVIEW','source_sha':SOURCE,'lanes':4,'archives':14,'member_bindings':135,'model_calls':0,'api_usd':0,'qualification':'Cached baseline isolated archive membership only; not approved repackaging/live delivery/legal/formula/layout/manual Excel/release/sale acceptance','independent_review_required':True})
 print('ACTUAL_ZIP_READY',R/'actual/READY.json',flush=True)
