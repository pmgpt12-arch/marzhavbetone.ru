from pathlib import Path
import os,subprocess,json
q=Path(__file__).resolve().parents[1];out=[]
for p in sorted((q/'plans').glob('*.json')):
 with (q/'proof'/(p.stem+'-author.log')).open('w')as f:
  try:r=subprocess.run([os.environ['CODEX_PRIMARY_RUNTIME_NODE'],'/tmp/nsp-next-runtime/edit.mjs',str(p)],stdout=f,stderr=subprocess.STDOUT,timeout=65);code=r.returncode
  except subprocess.TimeoutExpired:code=124
 out.append({'plan':p.name,'code':code});(q/'author-results.json').write_text(json.dumps(out,indent=2));print(out[-1],flush=True)
 if code:print('BLOCKED_AUTHORED_FILE',p,flush=True)
