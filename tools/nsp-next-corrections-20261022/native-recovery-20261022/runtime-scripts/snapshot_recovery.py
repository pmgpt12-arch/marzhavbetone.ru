from pathlib import Path
import shutil,json,hashlib,re,zipfile,io,subprocess,os,signal
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';R=Q.parent/'integration-20261022/repo';D=R/'tools/nsp-next-corrections-20261022/native-recovery-20261022'
assert not D.exists();D.mkdir(parents=True)
dirs=['additional-candidates','buyer-candidates','scoped-paid-candidates','complete-free-candidates','free-content-v2','free-print-v2','evidence','frozen-inputs','visual-free-content-v2','visual-free-print-v2','visual-free-v2','visual-print','visual-free-99']
for n in dirs:shutil.copytree(O/n,D/n)
for p in O.iterdir():
 if p.is_file()and p.suffix in ('.json','.md','.log')and p.name!='free-print-v2-transfer.json':shutil.copy2(p,D/p.name)
shutil.copytree(Q/'scripts',D/'runtime-scripts',ignore=shutil.ignore_patterns('__pycache__'))
V=D/'visual-core-word';V.mkdir()
for tag in ('w3','w4','w5','w6','w7','w8'):
 files=list((Q/'native-resume-20261022/visual').glob(tag+'-*.png'));assert files,(tag,files)
 for p in files:shutil.copy2(p,V/p.name)
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'(?i)(?:Authorization:\s*Bearer|api[_-]?key\s*[:=])\s*["\x27]?[A-Za-z0-9_-]{30,}']
hits=[]
def scan(name,b):
 for pattern in patterns:
  if re.search(pattern,b):hits.append(name)
for p in D.rglob('*'):
 if not p.is_file():continue
 data=p.read_bytes();scan(str(p.relative_to(D)),data)
 if p.suffix in ('.zip','.docx','.xlsx'):
  with zipfile.ZipFile(io.BytesIO(data))as z:
   assert z.testzip()is None
   for n in z.namelist():
    if n.endswith(('.xml','.rels','.txt','.md','.json','.php','.py','.ps1')):scan(str(p.relative_to(D))+'!'+n,z.read(n))
assert not hits,hits
gate={'scope':'new isolated recovery directory only','secret_pattern_scan':'PASS_NO_MATCH','source_19_protected_13_held_6_old_13_archives':json.loads((O/'PRESERVATION_GATE.json').read_text())['status'],'canonical_or_public_files_changed':False,'new_free_archive_count':2,'free_native_word_final_docs':6,'free_native_word_pages_visually_reviewed':14,'free_native_excel_scenarios':16,'print_and_reopen':'PASS_FINAL_2_FREE_SHAS','paid_native_calc':'11_FINAL_BOOKS_57_SCENARIOS_131_CHECKS_INCLUDING_2_FREE','paid_print':'OPEN_9_PAID_BOOKS','read_only_locale':'NOT_PROVEN','public_delivery':'NOT_RUN','publication':'NOT_AUTHORIZED_NOT_PERFORMED'}
(D/'FINAL_SCOPE_GATE.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2))
inventory=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(D.rglob('*'))if p.is_file()]
(D/'ARTIFACTS_SHA256.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2))
print('SNAPSHOT',len(inventory),'files',sum(x['bytes']for x in inventory),'bytes')
def run(args,timeout=45):
 p=subprocess.Popen(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,text=True)
 try:o,e=p.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.communicate()
  raise
 assert p.returncode==0,(args,o,e)
 return o
print('HEAD',run(['git','rev-parse','HEAD']).strip())
print('REMOTE',run(['git','ls-remote','origin','refs/heads/fix/nsp-product-guides-norms-20261021']).strip())
print(run(['git','status','--short']))
