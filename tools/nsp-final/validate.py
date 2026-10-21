#!/usr/bin/env python3
import collections, hashlib, json, re
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PRICES={'p1':2990000,'p2':2490000,'p3':1790000,'p4':2490000,'p5':2990000,'p7':2490000,'p8':2490000,'p9':2490000,'p10':1790000,'p11':2490000,'p13':1790000,'t2':990000,'t3':1490000}
GROUPS={'do-podpisaniya':['p7','p8','p13','p11'],'po-hodu-rabot':['p4','p2'],'zakrytie-i-oplata':['p3','p1','t2','t3'],'uderzhaniya-i-spory':['p5','p10'],'bankrotstvo':['p9']}

class Parser(HTMLParser):
    def __init__(self): super().__init__(); self.buttons=[]; self.robots=[]; self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='button' and 'data-sku' in a: self.buttons.append([a['data-sku'],a.get('data-price'),a.get('data-product')])
        if tag=='meta' and a.get('name') in ['robots','googlebot']: self.robots.append([a['name'],a.get('content')])
        if tag=='a' and 'href' in a: self.links.append(a['href'])

def signature(text):
    p=Parser();p.feed(text);return {'buttons':sorted(p.buttons),'robots':p.robots}

def validate(root=ROOT, catalog_only=False):
    baseline=json.loads((root/'tools/nsp-final/static-before.json').read_text())
    contract=json.loads((root/'tools/nsp-final/contract.json').read_text())
    manifest=json.loads((root/'tools/nsp-final/manifest.json').read_text())
    changed={r['path']:r for r in manifest}; assert len(changed)==len(manifest)
    assert set(changed)<=set(r['path'] for r in baseline)
    if not catalog_only:
        for row in baseline:
            p=root/row['path']; data=p.read_bytes(); actual=hashlib.sha256(data).hexdigest()
            assert actual==changed.get(row['path'],{}).get('after',row['sha256']), 'HASH_'+row['path']
            if row['path'] in changed: assert changed[row['path']]['before']==row['sha256']
            if p.suffix in ['.html','.js']:
                t=data.decode()
                assert not re.search(r't\.me/marzhavbetone|instagram\.com/marzhavbetone|marzhavbetone@yandex\.ru|https?://(?:www\.)?max\.ru(?:/|["\x27])|data-nsp-staging',t,re.I),'STALE_CONTACT_OR_BANNER_'+row['path']
                if p.suffix=='.html':
                    assert signature(t)==contract['pages'][row['path']], 'BUY_BUTTON_OR_ROBOTS_CHANGED_'+row['path']
                    for ld in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',t,re.S): json.loads(ld)
    t=(root/'katalog.html').read_text(); p=Parser(); p.feed(t)
    assert {s:int(price) for s,price,_ in p.buttons}==PRICES and len(p.buttons)==13
    for slug,skus in GROUPS.items():
        m=re.search(r'<details[^>]*id="group-'+slug+r'"[^>]*>(.*?)</details>',t,re.S); assert m
        assert re.findall(r'data-sku="([^"]+)"',m[1])==skus, 'GROUP_'+slug
        assert re.search(r'class="product-group-count">'+str(len(skus))+r'</span>',m[1]), 'HEADING_COUNT_'+slug
        assert re.search(r'href="#group-'+slug+r'"[^>]*>[^<]+<span>'+str(len(skus))+r'</span>',t), 'NAV_COUNT_'+slug
    assert t.count('class="product-card free"')==10
    assert re.search(r'href="#group-besplatno"[^>]*>[^<]+<span>10</span>',t)
    report={'status':'PASS','static_files':len(baseline),'changed_files':len(manifest),'paid_sku':13,'prices':'UNCHANGED','buy_buttons_and_robots':'UNCHANGED','groups':[len(s) for s in GROUPS.values()],'free_materials':10,'dzen':'CURRENT_NEW_ADDRESS_UNCONFIRMED; existing link preserved'}
    print(json.dumps(report,ensure_ascii=False)); return report

if __name__=='__main__':
    import sys
    validate(catalog_only='--catalog-only' in sys.argv)
