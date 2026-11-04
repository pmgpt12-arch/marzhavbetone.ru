from pathlib import Path
import json,hashlib,shutil,zipfile,io,re,subprocess,os,signal
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';O=Q/'native-recovery-20261022';R=Q.parent/'integration-20261022/repo';rel='tools/nsp-next-corrections-20261022/paid-followup-20261023';D=R/rel
assert not D.exists();D.mkdir(parents=True)
dirs=['p11-remaining-sources','p11-layout-v2','p11-layout-v3','p11-final-letter-tests','paid-print-v2','paid-print-v3','paid-print-v4','candidate-archives','evidence','frozen-inputs','deferred-office-jobs','visual-p11-remaining','visual-p11-layout-v3','rendered-p11-final54','rendered-p11-layout-v3','rendered-paid-print-v2','rendered-paid-print-v3','rendered-paid-print-v4']
for n in dirs:shutil.copytree(P/n,D/n)
for p in P.iterdir():
 if p.is_file()and p.suffix in('.json','.md','.txt','.zip','.png','.log'):shutil.copy2(p,D/(p.name+'.txt'if p.suffix=='.log'else p.name))
V=D/'visual-paid-preliminary';V.mkdir()
for name in ['b1-1.png','b2-1.png','b3-2.png']:shutil.copy2(P/'visual-paid-print-lo'/name,V/name)
shutil.copy2(O/'PRESERVATION_GATE.json',D/'PRESERVATION_GATE.json')
scripts=['prepare_p11_remaining.py','native_p11_remaining.py','fix_p11_letter_layout.py','native_p11_layout_v2.py','refine_p11_layout_guide.py','native_p11_layout_v3.py','prepare_p11_final_letters.py','native_p11_final_letters.py','fix_paid_print_v2.py','native_paid_print_v2.py','render_paid_print_v2.py','inspect_paid_print_lo.py','refine_paid_29_print.py','refine_paid_29_print_v4.py','freeze_followup.py','retry_office_after_owner.py','push_recovery_bounded.py','commit_recovery.py','snapshot_followup.py']
S=D/'runtime-scripts';S.mkdir()
for name in scripts:
 p=Q/'scripts'/name;compile(p.read_text(),str(p),'exec');shutil.copy2(p,S/name)
# Scan actual text, including inner DOCX/XLSX parts in full QA ZIPs.
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'(?i)(?:Authorization:\s*Bearer|api[_-]?key\s*[:=])\s*["\x27]?[A-Za-z0-9_-]{30,}'];hits=[]
def scan(b,name,depth=0):
 if any(re.search(p,b)for p in patterns):hits.append(name)
 if b.startswith(b'PK\x03\x04')and depth<2:
  with zipfile.ZipFile(io.BytesIO(b))as z:
   assert z.testzip()is None
   for n in z.namelist():
    if n.endswith(('.xml','.rels','.txt','.md','.json','.py','.ps1','.docx','.xlsx')):scan(z.read(n),name+'!'+n,depth+1)
for p in D.rglob('*'):
 if p.is_file():scan(p.read_bytes(),str(p.relative_to(D)))
assert not hits,hits
gate={'status':'PARTIAL_PROGRESS_OFFICE_RUNTIME_BLOCKER','new_P11_53_native_and_3_page_visual':'PASS_V3_SHA_CB278003','new_P11_54_native':'TIMEOUT_NOT_ACCEPTED','new_P5_print_candidates_native':'NOT_RUN_COM_ACTIVATION_FAILED','P5_29_v2_v3':'REJECTED_FOR_LAYOUT; final prepared v4 only','P5_29_v4':'PENDING_FULL_VISUAL_AND_NATIVE','new_full_QA_archives':{'P5':30,'P11':8},'public_or_canonical_changes':False,'old_19_and_protected_13_and_held_6_and_old_archives':'PASS_UNCHANGED','secret_pattern_scan':'PASS','queue_or_services_changed_after_failures':False,'deferred_jobs_submitted':False,'owner_action_required':'Normal manual startup of Excel and Word; no installer or security change'}
(D/'FINAL_SCOPE_GATE.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2))
inv=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(D.rglob('*'))if p.is_file()]
(D/'ARTIFACTS_SHA256.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2));print('SNAPSHOT',len(inv)+1,'files',sum(x['bytes']for x in inv),'bytes',flush=True)
def run(args,t=45):
 p=subprocess.Popen(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,text=True)
 try:a,b=p.communicate(timeout=t)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(args,a,b)
 return a
base='b19b947487fd6d2e0c2c676df22a957caadf77be'
assert run(['git','rev-parse','HEAD']).strip()==base
assert run(['git','branch','--show-current']).strip()=='fix/nsp-product-guides-norms-20261021'
assert run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).startswith(base)
run(['git','add','--sparse','-f','--',rel]);names=run(['git','diff','--cached','--name-only']).splitlines();assert len(names)==len(inv)+1 and all(x.startswith(rel+'/')for x in names)
run(['git','-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--',rel,':(exclude)'+rel+'/evidence/native/nsp-p5-print-v2-20261023/report.xml'])
assert not run(['git','diff','--name-only']).strip()
run(['git','commit','-m','Prepare P11 letter layouts and P5 print candidates; record Office runtime blocker [skip deploy]'])
head=run(['git','rev-parse','HEAD']).strip();print('COMMIT',head,flush=True)
with (Q/'push-followup-progress.log').open('w')as log:
 p=subprocess.Popen(['git','-c','pack.threads=2','-c','core.compression=1','push','--progress','origin','HEAD:refs/heads/fix/nsp-product-guides-norms-20261021'],cwd=R,stdout=log,stderr=log,start_new_session=True)
 try:rc=p.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  raise
 assert rc==0,('PUSH_FAILED',rc)
remote=run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']);assert remote.startswith(head)
print('REMOTE_VERIFIED',head,flush=True);assert not run(['git','status','--short']).strip()
