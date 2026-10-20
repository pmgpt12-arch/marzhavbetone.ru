#!/usr/bin/env python3
"""Local browser gate of exact migration candidate: current 13 SKUs, no payment."""
from __future__ import annotations
import functools,hashlib,http.server,json,re,shutil,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'
C=json.loads((D/'contract.json').read_text())
M=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
class Static(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path.split('?')[0]=='/app-script.php':self.path='/app.js'
        super().do_GET()
def main():
    plan=json.loads((OUT/'prepared-site-plan.json').read_text())
    for item in plan['shipping_files']:
        p=ROOT/item['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'SHIPPING_SHA_DRIFT_'+item['file']
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Static,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
            context=browser.new_context()
            external=[]
            def route(req):
                if req.request.url.startswith(base):req.continue_()
                else:external.append(req.request.url.split('?')[0]);req.abort()
            context.route('**/*',route)
            page=context.new_page();page.set_default_timeout(10000)
            page.goto(base+'/katalog.html',wait_until='domcontentloaded')
            cards=page.locator('.product-card button[data-sku]').evaluate_all('(xs)=>xs.map(x=>({sku:x.dataset.sku,price:Number(x.dataset.price),name:x.dataset.product,href:x.closest(".product-card")?.querySelector("a[href*=products]")?.getAttribute("href")}))')
            assert len(cards)==13 and {x['sku'] for x in cards}==set(M),'CATALOG_NOT_13_CURRENT_SKUS'
            for x in cards:assert x['price']==M[x['sku']]['price'],'PRICE_'+x['sku']
            routes={}
            for file in (ROOT/'products').glob('*.html'):
                text=file.read_text()
                for sku in M:
                    if f'data-sku="{sku}"' in text and re.search(r'<button[^>]*class="[^"]*add-to-cart',text):
                        routes.setdefault(sku,[]).append(file.relative_to(ROOT).as_posix())
            selected={}
            for sku in M:
                preferred=[x for x in routes.get(sku,[]) if Path(x).name.startswith(sku+'-')]
                assert len(preferred)==1,('AMBIGUOUS_CURRENT_PRODUCT_PAGE',sku,preferred)
                selected[sku]=preferred[0]
            samples=['index.html','katalog.html','articles/index.html',*selected.values()]
            for width in (390,1360):
                page.set_viewport_size({'width':width,'height':900})
                for rel in samples:
                    page.goto(base+'/'+rel,wait_until='domcontentloaded')
                    page.wait_for_timeout(400)
                    if width==390:page.locator('.nav-toggle').wait_for(state='visible')
                    met=page.evaluate('''() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,brand:document.querySelector('.brand')?.textContent,nav:[...document.querySelectorAll('.topbar nav a')].find(x=>x.getAttribute('href')==='/articles/')?.textContent,canonical:document.querySelector('link[rel="canonical"]')?.href,h1:document.querySelector('h1')?.textContent})''')
                    assert met['scroll']<=width+1,('OVERFLOW',rel,width,met)
                    assert 'на стороне подрядчика' in (met['brand'] or '').lower(),('BRAND',rel)
                    assert met['nav']=='Практика и судебные решения',('NAV',rel)
                    assert (met['canonical'] or '').startswith('https://nastoronepodryadchika.ru/'),('CANONICAL',rel)
                    if width==390:
                        toggle=page.locator('.nav-toggle');toggle.click();assert toggle.get_attribute('aria-expanded')=='true';toggle.click();assert toggle.get_attribute('aria-expanded')=='false'
                    sku=next((s for s,r in selected.items() if r==rel),None)
                    if sku:
                        btn=page.locator('button.add-to-cart[data-sku="'+sku+'"]').first
                        assert int(btn.get_attribute('data-price'))==M[sku]['price'],('PRODUCT_PRICE',sku)
                        page.evaluate('localStorage.removeItem("marzhavbetone-cart")')
                        page.reload(wait_until='domcontentloaded');page.wait_for_timeout(350)
                        btn=page.locator('button.add-to-cart[data-sku="'+sku+'"]').first
                        btn.click()
                        assert page.locator('#cart-count').inner_text()=='1',('CART_COUNT',sku)
                        saved=page.evaluate('JSON.parse(localStorage.getItem("marzhavbetone-cart"))')
                        assert len(saved)==1 and saved[0]['sku']==sku and saved[0]['price']==M[sku]['price'],('CART_PRICE',sku)
                        page.locator('#cart-close').click()
                    results.append({'page':rel,'width':width,'sku':sku,'pass':True})
            browser.close()
        report={'status':'PASS_RESPONSIVE_CURRENT_13SKU_PRICES_CART_AND_NAV','screens':results,'sku_pages':selected,'catalog':cards,'payment_submitted':False,'external_requests_blocked':len(external),'buyer_files_not_modified':True}
        (OUT/'browser-candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('PASS_BROWSER_CANDIDATE',len(results),'SCREENS',len(selected),'CURRENT_SKUS')
    finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
