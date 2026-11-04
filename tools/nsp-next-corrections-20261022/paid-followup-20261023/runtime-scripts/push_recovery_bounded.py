from pathlib import Path
import subprocess,os,signal,time
R=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/integration-20261022/repo');Q=Path(__file__).resolve().parents[1]
# Previous attempt had a bounded 55s limit; ls-remote confirms reachability and no remote change.
# 22MB of native proofs require packing and upload; emit progress, cap total duration at 240s.
log=Q/'push-recovery-progress.log'
with log.open('w')as f:
 p=subprocess.Popen(['git','-c','pack.threads=2','-c','core.compression=1','push','--progress','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,stdout=f,stderr=f,start_new_session=True)
 try:rc=p.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  raise
 assert rc==0,('PUSH_FAILED',rc,str(log))
print('PUSH_EXIT_0',flush=True)
p=subprocess.run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,text=True,capture_output=True,timeout=30)
assert p.returncode==0 and p.stdout.startswith('b19b947487fd6d2e0c2c676df22a957caadf77be')
print('REMOTE_VERIFIED',p.stdout.strip(),flush=True)