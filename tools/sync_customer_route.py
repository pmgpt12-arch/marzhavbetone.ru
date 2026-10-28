"""Sync route presentation from the existing server catalog; never change prices."""
import argparse, json, re
from pathlib import Path
from sync_catalog import paid_products
from check_desktop import retired_skus
ROOT = Path(__file__).resolve().parent.parent

def projection():
    return {sku: {'sku':sku, 'name':name, 'price':rub*100}
            for sku,(name,rub) in paid_products().items() if sku not in retired_skus()}

def render_cart(text):
    data=json.dumps(projection(),ensure_ascii=False,separators=(',',':'))
    return re.sub(r'// route-catalog:begin.*?// route-catalog:end',
        '// route-catalog:begin (tools/sync_customer_route.py; products-config.php)\nconst CART_CATALOG = '+data+';\n// route-catalog:end',text,flags=re.S)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    path=ROOT/'app.js';old=path.read_text();new=render_cart(old)
    assert len(projection())==13, 'Active SKU count changed: review before syncing'
    if args.write:path.write_text(new)
    else:assert old==new, 'Cart projection stale; run tools/sync_customer_route.py --write'
    # Protect both visible copy and FAQ structured data from the same price drift.
    text=(ROOT/'products/t2-peredacha-ispolnitelnoy-dokumentacii.html').read_text()
    name,rub=paid_products()['p4'];assert text.count(f'{rub:,}'.replace(',',' ')+' ₽')>=4
    assert name in text and '2 990' not in text
    print('PASS: 13 catalog SKU, cart snapshot, P4 cross-links and price')
if __name__=='__main__':main()
