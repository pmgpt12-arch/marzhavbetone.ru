"""Narrow integrity gates without lazy-fetching an entire repository snapshot."""
from pathlib import Path
from zipfile import ZipFile
import subprocess,json,hashlib,os,signal,xml.etree.ElementTree as E
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';O=Q/'native-recovery-20261022';HEAD='637a22fe1b34ded1db64a929a363f0fad14d466e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bounded(cmd,budget=12):
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:o,e=p.communicate(timeout=budget)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(cmd,e.decode(errors='replace'));return o
def load(n):return json.loads(bounded(['git','-C',str(R),'show',HEAD+':tools/nsp-next-corrections-20261022/'+n]))
reg=load('CANDIDATE_ARTIFACT_REGISTRY.json');assert len(reg['candidates'])==19
for f in reg['candidates']:
 p=Q/'candidates'/f['path'];assert sha(p)==f['sha256'],('CANDIDATE_CHANGED',f['path'])
 if p.suffix in ['.xlsx','.docx']:
  with ZipFile(p)as z:
   assert z.testzip()is None
   for n in z.namelist():
    if n.endswith(('.xml','.rels')):E.fromstring(z.read(n))
archives=load('CANDIDATE_ARCHIVES.json');assert len(archives['archives'])==13
count=0
for a in archives['archives']:
 p=Q/'buyer-candidates'/a['zip'];assert sha(p)==a['sha256']
 with ZipFile(p)as z:
  assert z.testzip()is None and len(z.namelist())==a['member_count']
  for f in a['members']:assert hashlib.sha256(z.read(f['name'])).hexdigest()==f['sha256'];count+=1
assert count==172
protected=load('PROTECTED_ACCEPTED_MANIFEST.json')['files'];assert len(protected)==13
for f in protected:assert sha(R/f['path'])==f['accepted_sha256']
held=load('HELD_SIX.json');assert len(held)==6
root=Path('/home/denis/projects/nsp-audit-fixes-20261021/tools/nsp-product-audit-fixes-20261021/remaining-review-20261022/candidates')
for f in held:assert sha(root/f['path'])==f['sha256']
assert sha(R/'products-storage/ARTIFACT-INVENTORY.json')=='f9ea9acb1c39826599787ebdc9372765863a48b8f812eb14c41a39d12627da5f'
out={'status':'PASS','source_head':HEAD,'baseline_19_unchanged':True,'protected_13_unchanged':True,'held_six_exact_and_unchanged':True,'previous_13_buyer_qa_zip_unchanged':True,'previous_zip_members':172,'P8_02_09_retested':False,'historical_inventory_unchanged':True,'extra_candidates':['P11 Start text branding','two free Word layout revisions'],'main_or_publication_changed':False,'recovery_rule':'Read exact small manifests and verify local bytes; broad lazy archive fetch was stopped; subprocess timeouts terminate owned process groups'}
(O/'PRESERVATION_GATE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False),flush=True)
