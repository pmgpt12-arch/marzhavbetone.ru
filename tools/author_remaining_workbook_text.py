#!/usr/bin/env python3
"""Run each scoped Artifact Tool edit with an individual execution bound."""
from pathlib import Path
import subprocess,os,json,shutil,argparse
p=argparse.ArgumentParser();p.add_argument('--only');args=p.parse_args()
R=Path(__file__).resolve().parents[1]
runtime=Path('/tmp/mb-r3/runtime')
shutil.copyfile(R/'tools/edit_remaining_workbooks_r3.mjs',runtime/'edit.mjs')
out=Path('/tmp/mb-r3/authored');out.mkdir(exist_ok=True)
result=[]
base=R/'tools/candidates/remaining-batch-r3-20261018'
layouts=json.loads((base/'layout-edits.json').read_text())
formulas=json.loads((base/'formula-text-edits.json').read_text())
plans=Path('/tmp/mb-r3/layout-patches');plans.mkdir(exist_ok=True)
for patch in sorted(Path('/tmp/mb-r3/patches').rglob('*.json')):
    edits=json.loads(patch.read_text());sku=patch.parent.name
    key=sku+'/'+patch.stem+'.xlsx';layout=layouts.get(key,{'sheets':{}})
    if args.only and key!=args.only:continue
    formula=[f for f in formulas if f['sku']==sku and f['file']==patch.stem+'.xlsx']
    if not edits and not layout['sheets'] and not formula:continue
    lp=plans/(sku+'-'+patch.stem+'-layout.json');lp.write_text(json.dumps(layout,ensure_ascii=False))
    fp=plans/(sku+'-'+patch.stem+'-formula.json');fp.write_text(json.dumps(formula,ensure_ascii=False))
    d=out/sku;d.mkdir(exist_ok=True)
    source=Path('/tmp/mb-r3/input')/sku/(patch.stem+'.xlsx')
    p=subprocess.run([os.environ['CODEX_PRIMARY_RUNTIME_NODE'],str(runtime/'edit.mjs'),str(source),str(d/source.name),str(patch),str(lp),str(fp)],capture_output=True,text=True,timeout=90)
    row={'sku':sku,'file':source.name,'edits':len(edits),'returncode':p.returncode}
    if p.returncode:row['error']=p.stderr[-1500:]
    result.append(row);(out/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(row,flush=True)
    if p.returncode:raise SystemExit(1)
