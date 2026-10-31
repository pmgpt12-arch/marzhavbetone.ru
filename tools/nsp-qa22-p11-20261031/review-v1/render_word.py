from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,os,json
R=Path(__file__).resolve().parent
py=os.environ['CODEX_PRIMARY_RUNTIME_PYTHON']
def run(f):
 out=R/'render-word'/f.stem;out.mkdir(parents=True,exist_ok=True)
 for old in out.glob('page-*.png'):old.unlink()
 r=subprocess.run([py,'/root/.codex/skills/builtins/documents/render_docx.py',str(f),'--output_dir',str(out),'--emit_pdf'],capture_output=True,text=True,timeout=90)
 (out/'render.log').write_text(r.stdout+r.stderr)
 return {'name':f.name,'exit':r.returncode,'png':len(list(out.glob('page-*.png')))}
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(run,sorted((R/'candidate').glob('*.docx'))))
 (R/'internal/WORD_RENDER_RECEIPT.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
