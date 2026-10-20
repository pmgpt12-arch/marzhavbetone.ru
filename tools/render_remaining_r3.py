#!/usr/bin/env python3
"""Bounded full-page review renders for every final editable Word file."""
from pathlib import Path
import subprocess,json,sys,time,hashlib,xml.etree.ElementTree as E,shutil
ROOT=Path('/tmp/mb-r3/work');OUT=Path('/tmp/mb-r3/render');OUT.mkdir(exist_ok=True)
RENDER=Path('/root/.codex/skills/builtins/documents/render_docx.py')
if not RENDER.exists():RENDER=Path('/root/.codex/skills/builtins/documents/scripts/render_docx.py')
results=[]
cached=json.loads((OUT/'word-render-status.json').read_text()) if (OUT/'word-render-status.json').exists() else []
cache={(r['sku'],r['file']):r for r in cached}
prior={}
for job in (Path(__file__).resolve().parents[1]/"tools/candidates/remaining-batch-r3-20261018/evidence/word-native").glob("*/job.xml"):
 for e in E.parse(job).getroot():prior[(job.parent.name.split("-word-")[1].split("-")[0].upper(),e.get("name"))]=e.get("sha256")
for f in sorted(ROOT.rglob('*.docx')):
    if prior.get((f.parent.name,f.name))==hashlib.sha256(f.read_bytes()).hexdigest():continue
    sha=hashlib.sha256(f.read_bytes()).hexdigest()
    old=cache.get((f.parent.name,f.name))
    if old and old.get('source_sha256')==sha and all(Path(p).exists() for p in old['pdfs']):
        results.append(old);continue
    d=OUT/f.parent.name/f.stem
    if d.exists():shutil.rmtree(d)
    t=time.monotonic()
    p=subprocess.run([sys.executable,str(RENDER),str(f),'--output_dir',str(d),'--emit_pdf'],capture_output=True,text=True,timeout=90)
    pngs=sorted(d.glob('page-*.png'));pdfs=list(d.glob('*.pdf'))
    row={'sku':f.parent.name,'file':f.name,'source_sha256':sha,'returncode':p.returncode,'pages':len(pngs),'pdfs':[str(x) for x in pdfs],'seconds':round(time.monotonic()-t,2)}
    if p.returncode or not pngs:row['error']=p.stdout[-1500:]+p.stderr[-1500:]
    results.append(row)
    (OUT/'word-render-status.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(row,flush=True)
    if p.returncode or not pngs:raise SystemExit(1)
