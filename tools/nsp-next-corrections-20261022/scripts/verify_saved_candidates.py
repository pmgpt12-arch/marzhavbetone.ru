"""Read-only integrity gate for quarantined candidates. This is not Office or release QA."""
from pathlib import Path
from zipfile import ZipFile
import json,hashlib,io,xml.etree.ElementTree as E
H=Path(__file__).resolve().parents[1];R=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(n):return json.loads((H/n).read_text())
def check_ooxml(b):
 with ZipFile(io.BytesIO(b))as z:
  assert z.testzip()is None
  for n in z.namelist():
   if n.endswith(('.xml','.rels')):E.fromstring(z.read(n))
protected=load('PROTECTED_ACCEPTED_MANIFEST.json')['files'];assert len(protected)==13
for f in protected:assert sha((R/f['path']).read_bytes())==f['accepted_sha256'],('PROTECTED_CHANGED',f['path'])
registry=load('CANDIDATE_ARTIFACT_REGISTRY.json');assert len(registry['candidates'])==19
for f in registry['candidates']:
 p=H/'candidates'/f['path'];b=p.read_bytes();assert sha(b)==f['sha256'],('CANDIDATE_CHANGED',f['path'])
 if p.suffix in ['.xlsx','.docx']:check_ooxml(b)
held=load('HELD_SIX.json');assert len(held)==6
for f in held:
 b=(H/'held-six'/f['path']).read_bytes();assert sha(b)==f['sha256'];assert not f['included_in_buyer_archives'];check_ooxml(b)
archives=load('CANDIDATE_ARCHIVES.json');assert len(archives['archives'])==13
count=changed=accepted=0
for f in archives['archives']:
 p=H/'candidate-archives'/f['zip'];assert sha(p.read_bytes())==f['sha256']
 with ZipFile(p)as z:
  assert z.testzip()is None;assert len(z.namelist())==len(set(z.namelist()))==f['member_count'];assert set(z.namelist())=={m['name']for m in f['members']}
  for m in f['members']:
   b=z.read(m['name']);assert sha(b)==m['sha256'];count+=1;changed+=m['changed_candidate'];accepted+=m['accepted_unchanged']
   assert sha(b)not in {x['sha256']for x in held},('UNACCEPTED_HELD_FILE_INCLUDED',f['sku'],m['name'])
assert (count,changed,accepted)==(172,17,13)
results=load('lo-regression-results.json');after=[x for x in results if x['phase']=='after'];before=[x for x in results if x['phase']=='before'];assert len(after)==39 and all(x['expectations_pass']for x in after);assert len(before)==9 and all(not x['expectations_pass']for x in before)
import sys
sys.path.insert(0,str(R/'tools'))
from check_xlsx_print_contract import snapshot,compare
for f in load('PRINT_CONTRACTS.json'):
 original=snapshot(R/f['path']);candidate=snapshot(H/'candidates'/f['path']);assert not compare(original,candidate),('PRINT_CONTRACT_CHANGED',f['path']);assert f['native_print']=='BLOCKED'
 if '/22-reestr-garantiynyh-uderzhaniy.xlsx' in f['path']:
  assert f['print_metadata']=='EXISTING_PRESERVED_ADDED_SCOPED_PRINT_AREAS'
  assert not original['print_names']
  assert candidate['print_names']=={'_xlnm.Print_Area:'+str(i):r['area']for i,r in enumerate(load('HELPER_PRINT_SCOPE.json')['P5_added_print_areas'])}
 else:
  assert f['print_metadata']=='UNCHANGED';assert original['print_names']==candidate['print_names']
for p in (H/'prepared-office').glob('*/*/job.xml'):
 root=E.parse(p).getroot();assert 1<=len(root.findall('file'))<=4;assert p.stat().st_size<=65536
 for f in root.findall('file'):assert sha((p.parent/f.get('name')).read_bytes())==f.get('sha256');assert f.get('sha256')not in {x['accepted_sha256']for x in protected}
assert sha((R/'products-storage/ARTIFACT-INVENTORY.json').read_bytes())=='f9ea9acb1c39826599787ebdc9372765863a48b8f812eb14c41a39d12627da5f'
print('PASS: 19 quarantined candidates; six held exact; 13 full ZIP/172 members/17 changed/13 protected; 39 LO cases; 9 old defects reproduced. NOT NATIVE OFFICE OR PUBLIC RELEASE.')
