#!/usr/bin/env python3
"""Exercise successful rollback and reject a concurrent edit before writing."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from validate import PRICES

with tempfile.TemporaryDirectory() as tmp:
    home=Path(tmp); site=home/'nastoronepodryadchika.ru'; site.mkdir(); masters=home/'masters'; masters.mkdir()
    for n in range(172): (masters/str(n)).write_text('fixture')
    orders=home/'orders'; orders.mkdir(); (orders/'delivery').mkdir()
    (site/'config.php').write_text("<?php define('ORDERS_DIR',"+repr(str(orders))+"); define('PRODUCTS_DIR',"+repr(str(masters))+"); define('DELIVERY_DIR',ORDERS_DIR.'/delivery'); define('DELIVERY_TTL_SECONDS',3600);")
    prices=','.join(repr(k)+'=>'+str(v) for k,v in PRICES.items())
    (site/'products-config.php').write_text("<?php function mvb_resolve_product(array $i): ?array { $p=["+prices+"]; return isset($p[$i['sku']]) ? ['price'=>$p[$i['sku']]] : null; }")
    release=home/'private'; release.mkdir(); (release/'candidate').mkdir()
    before=b'old'; after=b'new'; (site/'index.html').write_bytes(before); (release/'candidate/index.html').write_bytes(after)
    sha=lambda b:hashlib.sha256(b).hexdigest()
    (site/'brand-approved-2026.css').write_bytes(before); (release/'candidate/brand-approved-2026.css').write_bytes(after)
    (release/'manifest.json').write_text(json.dumps([{'path':name,'before':sha(before),'after':sha(after)} for name in ['index.html','brand-approved-2026.css']]))
    script=Path(__file__).with_name('transaction.php')
    def run(mode,ok=True):
        p=subprocess.run(['php',str(script),mode,str(site),str(release)],capture_output=True,timeout=15)
        assert (p.returncode==0)==ok,(mode,p.stdout,p.stderr)
    run('dry-run'); assert (site/'index.html').read_bytes()==before and not (release/'original').exists()
    (site/'index.html').write_bytes(b'concurrent'); run('apply',False); assert (site/'index.html').read_bytes()==b'concurrent'
    (site/'index.html').write_bytes(before); run('apply'); assert (site/'index.html').read_bytes()==after
    run('verify'); run('rollback'); assert (site/'index.html').read_bytes()==before
    assert (release/'original/index.html').read_bytes()==before
    assert (site/'brand-approved-2026.css').read_bytes()==before and (release/'original/brand-approved-2026.css').read_bytes()==before
print('STATIC_TRANSACTION_CONCURRENT_EDIT_AND_ROLLBACK=PASS')

# Exactly one public PDF may be created; absence is an explicit before-state.
with tempfile.TemporaryDirectory() as tmp:
    home=Path(tmp);site=home/'nastoronepodryadchika.ru';site.mkdir();masters=home/'masters';masters.mkdir()
    for n in range(172):(masters/str(n)).write_text('fixture')
    orders=home/'orders';orders.mkdir();(orders/'delivery').mkdir()
    (site/'config.php').write_text("<?php define('ORDERS_DIR',"+repr(str(orders))+"); define('PRODUCTS_DIR',"+repr(str(masters))+"); define('DELIVERY_DIR',ORDERS_DIR.'/delivery'); define('DELIVERY_TTL_SECONDS',3600);")
    prices=','.join(repr(k)+'=>'+str(v) for k,v in PRICES.items())
    (site/'products-config.php').write_text("<?php function mvb_resolve_product(array $i): ?array { $p=["+prices+"]; return isset($p[$i['sku']]) ? ['price'=>$p[$i['sku']]] : null; }")
    filename='downloads/checklist-zakrytiya-rabot.pdf';target=site/filename;payload=b'%PDF-isolated-fixture'
    def stage(name,path=filename):
        d=home/name;(d/'candidate'/Path(path).parent).mkdir(parents=True);(d/'candidate'/path).write_bytes(payload)
        (d/'manifest.json').write_text(json.dumps([{'path':path,'before':None,'after':hashlib.sha256(payload).hexdigest()}]));return d
    script=Path(__file__).with_name('transaction.php')
    def run(stage,mode,ok=True):
        p=subprocess.run(['php',str(script),mode,str(site),str(stage)],capture_output=True,timeout=15)
        assert (p.returncode==0)==ok,(mode,p.stdout,p.stderr)
    d=stage('create');run(d,'dry-run');assert not target.parent.exists()
    target.parent.mkdir();target.write_bytes(b'concurrent');run(d,'apply',False);assert target.read_bytes()==b'concurrent'
    target.unlink();target.parent.rmdir();run(d,'apply');run(d,'verify');assert target.read_bytes()==payload
    assert target.stat().st_mode&0o777==0o644 and target.parent.stat().st_mode&0o777==0o755
    run(d,'rollback');assert not target.parent.exists();run(d,'rollback')
    target.parent.mkdir();(target.parent/'unrelated.txt').write_text('keep')
    d=stage('existing-dir');run(d,'apply');run(d,'rollback');assert (target.parent/'unrelated.txt').read_text()=='keep'
    (target.parent/'unrelated.txt').unlink();target.parent.rmdir()
    outside=home/'outside';outside.mkdir();(outside/'canary').write_text('keep');target.parent.symlink_to(outside,target_is_directory=True)
    run(stage('symlink'),'dry-run',False);assert (outside/'canary').read_text()=='keep';target.parent.unlink()
    d=stage('zip','downloads/dengi.zip');run(d,'apply');run(d,'verify');run(d,'rollback');assert not target.parent.exists()
    assets=site/'assets';assets.mkdir()
    d=stage('asset','assets/nsp-hero-desktop.webp');run(d,'apply');run(d,'verify');run(d,'rollback');assert not (assets/'nsp-hero-desktop.webp').exists();assert not (site/'downloads').exists()
    d=stage('font','assets/nsp-plex-sans-semibold.woff2');run(d,'apply');run(d,'verify');run(d,'rollback');assert not (assets/'nsp-plex-sans-semibold.woff2').exists()
    assets.rmdir()
    run(stage('unsafe','downloads/other.pdf'),'dry-run',False);assert not target.parent.exists()
print('PUBLIC_PDF_CREATE_ABSENCE_CONCURRENT_EDIT_SYMLINK_AND_ROLLBACK=PASS')
