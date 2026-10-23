from pathlib import Path
import json,hashlib,subprocess,os,signal,shutil
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo';rel='tools/nsp-next-corrections-20261022/office-control-20261022-233620';D=R/rel
def run(args,t=45):
 p=subprocess.Popen(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:a,b=p.communicate(timeout=t)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(args,a,b)
 return a
base='bec8a82b25b033ab52c6c99aea38dbf04dadccb3'
assert run(['git','rev-parse','HEAD']).strip()==base
assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(base)
shutil.copy2(Path(__file__),D/Path(__file__).name)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inv=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(D.rglob('*'))if p.is_file()and p.name!='ARTIFACTS_SHA256.json']
(D/'ARTIFACTS_SHA256.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
run(['git','add','--sparse','-f','--',rel]);names=run(['git','diff','--cached','--name-only']).splitlines()
assert len(names)==len(inv)+1 and all(n.startswith(rel+'/')for n in names)
excluded=[':(exclude)'+rel+'/controller.log.txt']
for r in json.loads((D/'RESULTS.json').read_text()):
 rp=D/'evidence'/r['channel']/r['job']/'report.xml';assert sha(rp)==r['receipt_sha256'];excluded.append(':(exclude)'+str(rp.relative_to(R)))
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--',rel]+excluded)
assert not run(['git','diff','--name-only']).strip()
for x in inv:assert sha(D/x['path'])==x['sha256']
run(['git','commit','-m','Check Word and Excel with known-good single-file controls [skip deploy]'])
head=run(['git','rev-parse','HEAD']).strip();print('COMMIT',head,flush=True)
with (Q/'push-office-control.log').open('w')as log:
 p=subprocess.Popen(['git','-c','pack.threads=2','-c','core.compression=1','push','--progress','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,stdout=log,stderr=log,start_new_session=True)
 try:rc=p.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  raise
 assert rc==0,('PUSH_FAILED',rc)
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(head)
assert not run(['git','status','--short']).strip();print('REMOTE_VERIFIED',head,'FILES',len(inv)+1,flush=True)
