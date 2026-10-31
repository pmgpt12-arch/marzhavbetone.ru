from pathlib import Path
import base64,hashlib,json,zipfile,sys,os
R=Path('/home/denis/projects/nsp-qa22-p11-20261031');b=base64.b64decode((R/'recovery.b64').read_text());assert hashlib.sha256(b).hexdigest()=='c8057f7a82af41a4f070703d7159e04eac77697b89da1335e38bdc589423534e'
(R/'recovery.zip').write_bytes(b);D=R/'review-v1';assert not D.exists();D.mkdir()
with zipfile.ZipFile(R/'recovery.zip')as z:
 assert all(not x.startswith('/')and'..'not in Path(x).parts for x in z.namelist());z.extractall(D)
m=json.loads((D/'internal/REVIEW_MANIFEST.json').read_text());lib=json.loads((D/'internal/LIBRARY_IDENTITIES.json').read_text())
for k in ['archive','preview']:assert hashlib.sha256((D/'output'/m[k]['name']).read_bytes()).hexdigest()==m[k]['sha256']
with zipfile.ZipFile(D/'output'/m['archive']['name'])as z:
 assert z.testzip()is None and len(z.namelist())==10
 assert {n:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()}=={x['name']:x['sha256']for x in m['files']}
print('Recovery SHA and exact ten-file package verified',flush=True)
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024');import prepare_p1_publication_20261030 as c
base=c.api('GET','git/ref/heads/'+c.BR)['object']['sha'];qa='qa/nsp-qa22-p11-20261031';c.api('POST','git/refs',{'ref':'refs/heads/'+qa,'sha':base});c.BR=qa
prefix='tools/nsp-qa22-p11-20261031/review-v1';files={prefix+'/'+str(f.relative_to(D)):f.read_bytes()for f in D.rglob('*')if f.is_file()};files[prefix+'/save_remote.py']=Path(__file__).read_bytes()
sha=c.commit(files,'NSP P11 review: real estate settlement card, reconciled economics and legal prerequisites',base)
print('Review evidence commit '+sha,flush=True)
s=Path('/home/denis/.local/share/ai-business-os/office-vm/STATE.json');before=s.read_bytes();state=json.loads(before);old=json.loads(before)
assert state['qa21_current_owner_review']['archive_sha256']=='90f9b78ba53e1fb59d751e0972594f4e7135e599946935a3c32d00b3fa9d2594'
review={'status':'READY_FOR_OWNER_REVIEW','sku':'p11','edition':'P11-review-v1','title':m['title'],'title_owner_approved':True,'archive_sha256':m['archive']['sha256'],'file_count':10,'preview_pages':23,'evidence_branch':qa,'evidence_commit':sha,'evidence_prefix':prefix,'server_review_dir':str(D),'library_archive_id':lib['archive']['library_file_id'],'library_preview_id':lib['preview']['library_file_id'],'checks':m['checks'],'calculation':'manual editable Word52 and57; no automated calculator','release_allowed':False,'production_changed':False,'owner_edition_approval_pending':True,'next_action':'Owner review of exact P11-review-v1; publish only after acceptance'}
state['qa22_current_owner_review']=review;state['qa22_current_checkpoint']=review
assert s.read_bytes()==before,'Concurrent STATE update'
tmp=s.with_name('STATE.json.qa22.tmp');tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,s);actual=json.loads(s.read_text())
assert actual['qa22_current_owner_review']==review
assert all(actual[k]==v for k,v in old.items()if k not in ['qa22_current_owner_review','qa22_current_checkpoint'])
receipt={'status':'P11_REVIEW_EVIDENCE_COMMITTED_AND_EXISTING_STATE_READBACK_PASS','evidence_commit':sha,'branch':qa,'archive_sha256':m['archive']['sha256'],'state_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'production_changed':False,'release_allowed':False}
(R/'SAVE_RECEIPT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
