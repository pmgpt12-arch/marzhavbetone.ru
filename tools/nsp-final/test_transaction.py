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
    (release/'manifest.json').write_text(json.dumps([{'path':'index.html','before':sha(before),'after':sha(after)}]))
    script=Path(__file__).with_name('transaction.php')
    def run(mode,ok=True):
        p=subprocess.run(['php',str(script),mode,str(site),str(release)],capture_output=True,timeout=15)
        assert (p.returncode==0)==ok,(mode,p.stdout,p.stderr)
    run('dry-run'); assert (site/'index.html').read_bytes()==before and not (release/'original').exists()
    (site/'index.html').write_bytes(b'concurrent'); run('apply',False); assert (site/'index.html').read_bytes()==b'concurrent'
    (site/'index.html').write_bytes(before); run('apply'); assert (site/'index.html').read_bytes()==after
    run('verify'); run('rollback'); assert (site/'index.html').read_bytes()==before
    assert (release/'original/index.html').read_bytes()==before
print('STATIC_TRANSACTION_CONCURRENT_EDIT_AND_ROLLBACK=PASS')
