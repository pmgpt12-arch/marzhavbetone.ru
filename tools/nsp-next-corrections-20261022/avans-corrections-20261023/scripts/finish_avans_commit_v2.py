from pathlib import Path
import json,hashlib,shutil,subprocess,os,signal
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo'
rels=['tools/nsp-next-corrections-20261022/avans-corrections-20261023','tools/nsp-next-corrections-20261022/office-recovery-20261023'];base='f69d1dca4df471aaa65c75a18d9be746f003bff9';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
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
assert run(['git','rev-parse','HEAD']).strip()==base;assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(base)
D=R/rels[0];shutil.copy2(Path(__file__),D/'scripts'/Path(__file__).name)
for rel in rels:
 D=R/rel;inv=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(D.rglob('*'))if p.is_file()and p.name!='FINAL_ARTIFACTS_SHA256.json'];(D/'FINAL_ARTIFACTS_SHA256.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
 for x in inv:assert sha(D/x['path'])==x['sha256']
run(['git','add','--sparse','-f','--']+rels);names=[n for n in run(['git','diff','--cached','--name-only','-z']).split('\0')if n]
assert names and all(any(n.startswith(r+'/')for r in rels)for n in names)
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--']+rels)
assert not run(['git','diff','--name-only','-z'])
run(['git','commit','-m','Verify restored Office and corrected advance free bundle [skip deploy]']);head=run(['git','rev-parse','HEAD']).strip();print('COMMIT',head,'FILES',len(names),flush=True)
with (Q/'push-avans-native.log').open('w')as log:
 p=subprocess.Popen(['git','-c','pack.threads=2','-c','core.compression=1','push','--progress','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,stdout=log,stderr=log,start_new_session=True)
 try:rc=p.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  raise
 assert rc==0,('PUSH_FAILED',rc)
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(head);assert not run(['git','status','--short']);print('REMOTE_VERIFIED',head,flush=True)
