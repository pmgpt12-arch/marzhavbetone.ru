from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,hashlib
Q=Path(__file__).resolve().parents[1];R=Q.parents[1]
files=sorted((Q/'candidates').rglob('*.docx'))
def one(p):
 out=Q/'rendered'/p.stem;out.mkdir(parents=True,exist_ok=True)
 run=subprocess.run([str(R/'.render-venv/bin/python'),str(R/'render_docx.py'),str(p),'--output_dir',str(out),'--emit_pdf','--dpi','120'],capture_output=True,text=True,timeout=45)
 (out/'render.log').write_text(run.stdout+'\n'+run.stderr);assert run.returncode==0,(p,run.stderr)
 pdf=next(out.glob('*.pdf'));pages=sorted(out.glob('page-*.png'))
 return {'path':str(p.relative_to(Q/'candidates')),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pdf':str(pdf),'pages':[str(f)for f in pages],'page_count':len(pages),'native_office':False,'visual_review':'PENDING'}
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(one,files))
(Q/'docx-render-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False),flush=True)
