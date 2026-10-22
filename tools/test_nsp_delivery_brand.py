#!/usr/bin/env python3
"""Render every buyer email branch with synthetic links; never call mail()."""
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'products-config.php').read_text()
assert source.count("$subject = 'Ваши материалы «На стороне подрядчика» — заказ оплачен';") == 1
skus = sorted(set(re.findall(r'data-sku="([^"]+)"', (ROOT / 'katalog.html').read_text())))
assert len(skus) == 13
cases = [[{'sku':sku, 'name':'Synthetic '+sku, 'url':'https://nastoronepodryadchika.ru/download.php?synthetic='+sku}] for sku in skus]
cases.append(cases[0]+cases[-1])
with tempfile.TemporaryDirectory() as directory:
    # Match the normal protected directory setup before rendering a template.
    for target in [Path(directory), Path(directory)/'delivery']:
        target.mkdir(exist_ok=True)
        (target/'.htaccess').write_text('Deny from all\n')
    before={str(p.relative_to(directory)):p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
    php = '''define('ORDERS_DIR',$argv[1]); define('ADMIN_EMAIL','nastoronepodryadchika@yandex.ru');
    define('DELIVERY_TTL_SECONDS',3600); require $argv[2];
    $out=[]; foreach(json_decode($argv[3],true) as $links){$out[]=mvb_delivery_email(['id'=>'SYNTHETIC'],$links);}
    echo json_encode($out,JSON_UNESCAPED_UNICODE);'''
    result = subprocess.run(['php','-r',php,directory,str(ROOT/'products-config.php'),json.dumps(cases)],capture_output=True,text=True,timeout=15)
    assert result.returncode == 0, result.stderr
    bodies = json.loads(result.stdout)
    assert len(bodies) == len(cases)
    for body, links in zip(bodies,cases):
        assert 'Маржа в бетоне' not in body and 'marzhavbetone' not in body
        assert 'На стороне подрядчика' in body and 'nastoronepodryadchika@yandex.ru' in body
        assert '1 час' in body
        for link in links:
            assert link['url'] in body
    after={str(p.relative_to(directory)):p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
    assert after == before, 'Rendering templates wrote an order or log'
print(json.dumps({'status':'PASS','buyer_email_cases':len(cases),'real_messages_sent':0,'orders_created':0}))
