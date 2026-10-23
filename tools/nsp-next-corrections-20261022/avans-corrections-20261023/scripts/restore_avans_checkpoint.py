from pathlib import Path,PurePosixPath
import base64,hashlib,tarfile,io,json,shutil,subprocess,xml.etree.ElementTree as E,datetime
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo';N=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
S=Q/'avans-corrections-20261023';assert not S.exists()
raw=base64.b64decode((Q/'avans-upload-8d7961b909b3.b64').read_bytes(),validate=True);assert len(raw)==2428645 and hashlib.sha256(raw).hexdigest()=='8d7961b909b3580b1edbc0343a4af575d3cd700e5446d63981e08140ffac2975'
S.mkdir()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as t:
 for m in t.getmembers():
  path=PurePosixPath(m.name);assert m.isfile()and not path.is_absolute()and '..'not in path.parts
  dst=S.joinpath(*path.parts);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(t.extractfile(m).read())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inv=json.loads((S/'ARTIFACTS_SHA256.json').read_text())
for row in inv:assert (S/row['path']).stat().st_size==row['bytes']and sha(S/row['path'])==row['sha256']
assert len(inv)+1==99
from zipfile import ZipFile
old=Q.parent/'remaining-audit-20261022/free-sources/downloads/avans.zip'
source=json.loads((S/'SOURCE_MEMBERS.json').read_text())
with ZipFile(old)as z:
 assert z.testzip()is None and sorted(z.namelist())==sorted(r['file']for r in source)
 for r in source:assert hashlib.sha256(z.read(r['file'])).hexdigest()==r['sha256']
blob=subprocess.check_output(['git','-C',str(R),'hash-object',str(old)],text=True).strip();assert blob=='09b441a0861fb9dca2a15eed9a82ee40472cabd8'
tree=subprocess.check_output(['git','-C',str(R),'ls-tree','HEAD','downloads/avans.zip'],text=True);assert tree.split()[2]==blob
package=json.loads((S/'PACKAGE_GATE.json').read_text());assert sha(S/'avans-QA-candidate.zip')==package['zip_sha256']
with ZipFile(S/'avans-QA-candidate.zip')as z:
 assert z.testzip()is None and len(z.namelist())==5
 for r in package['members']:assert hashlib.sha256(z.read(r['file'])).hexdigest()==r['sha256']
for j in (S/'deferred-office-jobs').iterdir():
 root=E.parse(j/'job.xml').getroot();assert root.get('id')==j.name;ch='native'if'xlsx'in j.name else'word';assert not (N/ch/j.name).exists(),'Immutable job id already used'
 for f in root.findall('file'):assert sha(j/f.get('name'))==f.get('sha256')
status={}
for ch in ['native','word']:
 j=E.parse(N/ch/'current.xml').getroot().get('id');p=N/'results'/ch/j/'report.xml';r=E.parse(p).getroot()if p.exists()else None
 status[ch]={'current_job':j,'status':r.get('status')if r is not None else'PENDING','report_sha256':sha(p)if p.exists()else None,'agent_status':json.loads((N/'results'/(ch+'-laptop-status.json')).read_text())}
log=subprocess.run(['journalctl','_PID=1606','-n','10','--no-pager','-o','cat'],capture_output=True,text=True,timeout=10);assert log.returncode==0
(S/'CURRENT_TRANSPORT.log.txt').write_text(log.stdout)
(S/'CURRENT_OFFICE_STATE.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'channels':status,'new_jobs_submitted':False,'network_online_not_office_recovery':True},ensure_ascii=False,indent=2)+'\n')
p=subprocess.run(['python3',str(Q/'scripts/verify_recovery_preservation_v2.py')],capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr;gate=json.loads(p.stdout);assert gate['status']=='PASS';(S/'PRESERVATION_GATE.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n')
(S/'SERVER_TRANSFER_GATE.json').write_text(json.dumps({'status':'PASS','transfer_sha256':hashlib.sha256(raw).hexdigest(),'inventory_files':99,'all_sha_exact':True,'original_avans_git_blob':blob,'source_members_exact':5,'qa_members_verified':5,'candidate_changed_members':4,'public_switch':False},ensure_ascii=False,indent=2)+'\n')
shutil.copy2(Path(__file__),S/'scripts'/Path(__file__).name)
print('RESTORED_AND_VERIFIED',str(S),'FILE_COUNT',len([p for p in S.rglob('*')if p.is_file()]),flush=True)
print('OFFICE_STATE',json.dumps(status,ensure_ascii=False),flush=True)
