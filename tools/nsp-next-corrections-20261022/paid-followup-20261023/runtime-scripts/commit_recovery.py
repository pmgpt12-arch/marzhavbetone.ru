from pathlib import Path
import subprocess,json,hashlib,os,signal
R=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/integration-20261022/repo');rel='tools/nsp-next-corrections-20261022/native-recovery-20261022';D=R/rel
def run(args,t=55):
 p=subprocess.Popen(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,text=True)
 try:o,e=p.communicate(timeout=t)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(args,o,e)
 return o
assert run(['git','rev-parse','HEAD']).strip()=='637a22fe1b34ded1db64a929a363f0fad14d466e'
assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
for r in json.loads((D/'ARTIFACTS_SHA256.json').read_text()):
 p=D/r['path'];assert p.stat().st_size==r['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
run(['git','add','--sparse','--',rel])
names=run(['git','diff','--cached','--name-only']).splitlines();assert len(names)==311 and all(p.startswith(rel+'/')for p in names),(len(names),names[:3])
assert not run(['git','diff','--name-only']).strip()
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check'])
print('STAGED',len(names),'files',flush=True)
print(run(['git','commit','-m','Verify native Office recovery and assemble corrected free QA bundles [skip deploy]']),flush=True)
print('COMMIT',run(['git','rev-parse','HEAD']).strip(),flush=True)
print(run(['git','push','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021']),flush=True)
print('REMOTE',run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).strip(),flush=True)