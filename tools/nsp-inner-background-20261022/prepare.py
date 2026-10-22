"""Build a bounded static release; never change page content or the homepage."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(data): return hashlib.sha256(data).hexdigest()
def prepare():
    directory=ROOT/'tools/nsp-inner-background-20261022'
    if (directory/'build.json').exists():
        manifest=json.loads((ROOT/'tools/nsp-final/manifest.json').read_text())
        assert len(manifest)==89
        for row in manifest: assert sha((ROOT/row['path']).read_bytes())==row['after'],row['path']
        print('INNER_BACKGROUND_ALREADY_PREPARED=87');return
    baseline=json.loads((ROOT/'tools/nsp-final/static-before.json').read_text())
    # The previously verified release's candidate is now the production baseline.
    previous=json.loads((ROOT/'tools/nsp-final/manifest.json').read_text())
    for row in baseline:
        for changed in previous:
            if row['path']==changed['path']:
                row['sha256']=changed['after'];row['size']=(ROOT/row['path']).stat().st_size
    for row in baseline: assert sha((ROOT/row['path']).read_bytes())==row['sha256'],row['path']
    home=(ROOT/'index.html').read_bytes();css=ROOT/'brand-approved-2026.css'
    old_css=css.read_bytes();assert old_css==(directory/'before.css').read_bytes()
    css.write_bytes(old_css+(directory/'background.css').read_bytes())
    version=sha(css.read_bytes())[:8];pages=[]
    for row in baseline:
        name=row['path']
        if not name.endswith('.html') or name=='index.html':continue
        p=ROOT/name;text=p.read_text()
        updated,n=re.subn(r'(brand-approved-2026\.css\?v=)[a-f0-9]+',lambda m:m[1]+version,text)
        if n:
            assert n==1 and 'class="rebrand-approved' in text,name
            p.write_text(updated);pages.append(name)
    image=ROOT/'assets/nsp-background-documents.webp';assert 0<image.stat().st_size<=150*1024
    assert home==(ROOT/'index.html').read_bytes() and len(pages)==87
    baseline.append({'path':'assets/nsp-background-documents.webp','sha256':None,'size':0})
    manifest=[]
    for row in baseline:
        after=sha((ROOT/row['path']).read_bytes())
        if after!=row['sha256']:manifest.append({'path':row['path'],'before':row['sha256'],'after':after})
    assert len(manifest)==89
    (ROOT/'tools/nsp-final/static-before.json').write_text(json.dumps(baseline,indent=2)+'\n')
    (ROOT/'tools/nsp-final/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (directory/'pages.json').write_text(json.dumps(pages,indent=2)+'\n')
    (directory/'build.json').write_text(json.dumps({'status':'PASS','pages':len(pages),'public_files':len(manifest),'image_bytes':image.stat().st_size,'css_version':version,'homepage_sha256':sha(home),'homepage':'BYTE_IDENTICAL'},indent=2)+'\n')
    print('INNER_BACKGROUND_PREPARED='+str(len(pages)))
if __name__=='__main__':prepare()
