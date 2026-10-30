from pathlib import Path
import sys,json,hashlib,base64,zipfile,subprocess,datetime,os
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024');import prepare_p1_publication_20261030 as c
D=Path('/home/denis/projects/nsp-qa18-p7-20261030');H=lambda b:hashlib.sha256(b).hexdigest();assert not (D/'FINAL_CHECKPOINT.json').exists()
b=base64.b64decode((D/'FINAL_TRANSFER.b64').read_text());assert H(b)=='84d8f9d7389a60ea05353fbe7a786794ff689b4fbfc95c24235d2cf8e2515d64';(D/'FINAL_TRANSFER.zip').write_bytes(b)
with zipfile.ZipFile(D/'FINAL_TRANSFER.zip')as z:
 assert z.testzip()is None and all(not n.startswith('/')and'..'not in Path(n).parts for n in z.namelist());z.extractall(D/'review-v1')
T=D/'review-v1';m=json.loads((T/'internal/REVIEW_MANIFEST.json').read_text());out=T/m['archive']['name'];assert H(out.read_bytes())==m['archive']['sha256'];assert m['status']=='READY_FOR_OWNER_REVIEW'and m['file_count']==11 and m['rendered_pages']==27
with zipfile.ZipFile(out)as z:
 assert z.testzip()is None and len(z.namelist())==11 and all(H(z.read(x['name']))==x['sha256']for x in m['files'])
status={k:m[k]for k in ['sku','edition','status','file_count','formats','rendered_pages','new_native_office_test_performed','render_engine','owner_approval','release_allowed','production_changed','full_qa_pass','artifact_refs']};status.update(archive_sha256=m['archive']['sha256'],preview_sha256=m['preview']['sha256'],next_action='Owner review exact 11-file P7 edition. No publication permission.')
(T/'CURRENT_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
def api(method,path,payload=None):
 a=['gh','api','--method',method,c.R+'/'+path];data=None
 if payload is not None:a+=['--input','-'];data=json.dumps(payload,ensure_ascii=False).encode()
 return json.loads(subprocess.run(a,input=data,capture_output=True,check=True,timeout=60 if method=='POST'and path=='git/blobs'else 20).stdout)
c.api=api;c.BR='qa/nsp-qa18-p7-20261030';base=m['source_commit'];refs=api('GET','git/matching-refs/heads/'+c.BR);assert refs==[];api('POST','git/refs',{'ref':'refs/heads/'+c.BR,'sha':base})
P='tools/nsp-qa18-p7-20261030';files={P+'/'+out.name:out.read_bytes(),P+'/CURRENT_STATUS.json':(T/'CURRENT_STATUS.json').read_bytes()}
for p in (T/'internal').glob('*.json'):files[P+'/internal/'+p.name]=p.read_bytes()
p=T/'BUILD_SCRIPTS_FINAL.zip'
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED)as z:
 for f in (T/'scripts').iterdir():z.write(f,f.name)
files[P+'/'+p.name]=p.read_bytes();files[P+'/save_checkpoint.py']=Path(__file__).read_bytes();print('11 member hashes and transfer verified; saving QA branch',flush=True)
sha=c.commit(files,'QA18 P7: 11-file owner review, single PDF guide, clear manual schedules [skip deploy]',base)
assert c.fetch(P+'/internal/REVIEW_MANIFEST.json',sha)==(T/'internal/REVIEW_MANIFEST.json').read_bytes();a=api('GET','contents/'+P+'/'+out.name+'?ref='+sha);actual=base64.b64decode(api('GET','git/blobs/'+a['sha'])['content']);assert H(actual)==m['archive']['sha256']
S=Path('/home/denis/.local/share/ai-business-os/office-vm/STATE.json');before=S.read_bytes();s=json.loads(before);assert 'qa18_current_owner_review'not in s;(D/'STATE_BEFORE_QA18.json').write_bytes(before)
entry={**status,'git_branch':c.BR,'evidence_commit':sha,'manifest_path':str(T/'internal/REVIEW_MANIFEST.json'),'manifest_sha256':H((T/'internal/REVIEW_MANIFEST.json').read_bytes()),'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};s['qa18_current_owner_review']=entry;s['qa18_current_checkpoint']=entry;s['qa18_owner_roadmap']=json.loads((T/'internal/OWNER_ROADMAP.json').read_text())
tmp=S.with_name('STATE.qa18.tmp');assert not tmp.exists();tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');assert S.read_bytes()==before;os.replace(tmp,S);assert json.loads(S.read_text())['qa18_current_owner_review']==entry
receipt={'status':'QA18_P7_REVIEW_CHECKPOINT_AND_GIT_READBACK_PASS','evidence_commit':sha,'branch':c.BR,'archive_sha256':m['archive']['sha256'],'file_count':11,'rendered_pages':27,'owner_approval':'PENDING','production_changed':False,'full_qa_pass':False,'new_native_office_test_performed':False,'artifact_refs':m['artifact_refs'],'state_sha256':H(S.read_bytes())};(D/'FINAL_CHECKPOINT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False,indent=2))
