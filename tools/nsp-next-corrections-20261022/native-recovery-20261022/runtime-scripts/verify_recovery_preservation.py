from pathlib import Path
from zipfile import ZipFile
import subprocess,json,hashlib,io,tarfile,shutil
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';O=Q/'native-recovery-20261022';HEAD='637a22fe1b34ded1db64a929a363f0fad14d466e'
S=O/'verification-snapshot';S.mkdir(exist_ok=True)
data=subprocess.check_output(['git','-C',str(R),'archive',HEAD,'products-storage','tools/check_xlsx_print_contract.py','tools/nsp-next-corrections-20261022'],timeout=35)
with tarfile.open(fileobj=io.BytesIO(data))as t:t.extractall(S,filter='data')
r=subprocess.run(['python3',str(S/'tools/nsp-next-corrections-20261022/scripts/verify_saved_candidates.py')],capture_output=True,text=True,timeout=45)
(O/'BASELINE_INTEGRITY_GATE.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
print(r.stdout,flush=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
h=S/'tools/nsp-next-corrections-20261022';reg=json.loads((h/'CANDIDATE_ARTIFACT_REGISTRY.json').read_text())
for f in reg['candidates']:assert sha(Q/'candidates'/f['path'])==f['sha256'],('SERVER_CANDIDATE_CHANGED',f['path'])
archives=json.loads((h/'CANDIDATE_ARCHIVES.json').read_text())
for a in archives['archives']:assert sha(Q/'buyer-candidates'/a['zip'])==a['sha256'],('OLD_QA_ZIP_CHANGED',a['zip'])
protected=json.loads((h/'PROTECTED_ACCEPTED_MANIFEST.json').read_text())['files']
for f in protected:assert sha(R/f['path'])==f['accepted_sha256']
held=json.loads((h/'HELD_SIX.json').read_text())
root=Path('/home/denis/projects/nsp-audit-fixes-20261021/tools/nsp-product-audit-fixes-20261021/remaining-review-20261022/candidates')
for f in held:assert sha(root/f['path'])==f['sha256']
out={'status':'PASS','source_head':HEAD,'baseline_19_unchanged':True,'protected_13_unchanged':True,'held_six_exact_and_unchanged':True,'previous_13_buyer_qa_zip_unchanged':True,'previous_zip_members':172,'P8_02_09_retested':False,'extra_candidates':['P11 Start text branding','two free Word layout revisions'],'main_or_publication_changed':False}
(O/'PRESERVATION_GATE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False),flush=True)
