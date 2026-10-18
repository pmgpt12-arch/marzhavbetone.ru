#!/usr/bin/env python3
"""Read-only, bounded print rendering; no Microsoft Office equivalence claim."""
from pathlib import Path
import subprocess,hashlib,json,time
IN=Path('/tmp/mb-r3/work');OUT=Path('/tmp/mb-r3/excel-print');OUT.mkdir(exist_ok=True)
rows=[];deadline=time.monotonic()+1200
previous=json.loads((OUT/'summary.json').read_text()) if (OUT/'summary.json').exists() else []
cache={(r['sku'],r['file']):r for r in previous}
for f in sorted(p for p in IN.rglob('*') if p.suffix in {'.xlsx','.xls'}):
 d=OUT/f.parent.name;d.mkdir(exist_ok=True);sha=hashlib.sha256(f.read_bytes()).hexdigest()
 prior=cache.get((f.parent.name,f.name))
 if prior and prior['source_sha256']==sha and Path(prior['pdf']).exists():
  assert hashlib.sha256(Path(prior['pdf']).read_bytes()).hexdigest()==prior['pdf_sha256']
  rows.append(prior);continue
 p=subprocess.run(['soffice','-env:UserInstallation=file:///tmp/lo-r3-print-'+f.parent.name+'-'+f.stem,'--headless','--convert-to','pdf','--outdir',str(d),str(f)],capture_output=True,text=True,timeout=65)
 out=d/(f.stem+'.pdf');assert p.returncode==0 and out.exists(),(f,p.stderr,p.stdout)
 assert hashlib.sha256(f.read_bytes()).hexdigest()==sha,('Input mutated',f)
 import fitz
 pdf=fitz.open(out)
 rows.append({'sku':f.parent.name,'file':f.name,'source_sha256':sha,'pdf':str(out),'pdf_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'pages':len(pdf),'status':'RENDERED_NOT_NATIVE_VERIFIED'})
 (OUT/'summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(f.parent.name,f.name,len(pdf),flush=True)
 if time.monotonic()>deadline:raise SystemExit('Bounded total stop')
