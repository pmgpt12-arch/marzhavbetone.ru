#!/usr/bin/env python3
"""Real browser fixtures: accepted product layouts and deliberate regressions."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import tempfile
import test_cart
import check_desktop as desktop

HEIGHT = 768
BASE = '<style>body{margin:0} .lead,p{margin:10px} h2{font-size:24px}</style>'
MODERN = '<main><h1>Система</h1><p class="lead">Работы выполнены, оплата задержана.</p><span class="price">29 900 ₽</span><button class="add-to-cart">Купить</button><h2>Результат</h2><p>Документы и расчёт задолженности.</p></main>'


def main():
    cases = 0
    with sync_playwright() as p:
        near = desktop.chromium_nearby()
        browser = p.chromium.launch(**({'executable_path':str(near)} if near else {}))
        page = browser.new_page(viewport={'width':1366,'height':HEIGHT})
        try:
            for label, html, rel, accepted in [
                ('modern', MODERN, 'products/p1-oplata-po-ks2.html', True),
                ('original', MODERN.replace('<h2>Результат</h2><p>Документы и расчёт задолженности.</p>', '<div class="product-fit">Когда применять и результат</div>'), 'products/t2-peredacha-ispolnitelnoy-dokumentacii.html', True),
                ('missing result', MODERN.replace('<h2>Результат</h2>', '<h2>Другое</h2>'), 'products/p1-oplata-po-ks2.html', False),
                ('hidden result', MODERN.replace('<h2>Результат</h2><p>', '<h2>Результат</h2><p hidden>'), 'products/p1-oplata-po-ks2.html', False),
                ('missing price', MODERN.replace('class="price"','class="other"'), 'products/p1-oplata-po-ks2.html', False),
                ('missing buy', MODERN.replace('class="add-to-cart"','class="other"'), 'products/p1-oplata-po-ks2.html', False),
                ('price below fold', MODERN.replace('<span class="price">','<span class="price" style="display:block;margin-top:900px">'), 'products/p1-oplata-po-ks2.html', False),
                ('archive', '<main><a href="p1-oplata-po-ks2.html">Перейти к системе</a></main>', 'products/t1-pervyy-shag-pri-neoplate.html', True),
                ('archive broken', '<main><a href="p999-missing.html">Перейти</a></main>', 'products/t1-pervyy-shag-pri-neoplate.html', False),
                ('archive wrong path', '<main><a href="/missing/p1-oplata-po-ks2.html">Перейти</a></main>', 'products/t1-pervyy-shag-pri-neoplate.html', False),
                ('archive hidden', '<main><a hidden href="p1-oplata-po-ks2.html">Перейти</a></main>', 'products/t1-pervyy-shag-pri-neoplate.html', False),
                ('retired sale', MODERN.replace('class="add-to-cart"','class="add-to-cart" data-sku="t1"'), 'products/t1-pervyy-shag-pri-neoplate.html', False),
            ]:
                page.set_content(BASE+html)
                errors=desktop.first_screen(page, HEIGHT, rel)
                assert (not errors) == accepted, (label, errors)
                cases+=1
            style='<style>h3{width:500px;font:42px Arial;overflow-wrap:anywhere}</style>'
            page.set_content(style+'<h3>ЗАКРЫТИЕ<br>ВЫПОЛНЕННЫХ<br>РАБОТ</h3>')
            errors = page.evaluate(desktop.WORDBREAK_SCRIPT)
            assert not errors, ('BR joined separate words', errors)
            page.set_content(style+'<h3>ЗАКРЫТИЕВЫПОЛНЕННЫХРАБОТ</h3>')
            assert page.evaluate(desktop.WORDBREAK_SCRIPT), 'real oversized word accepted'
            cases+=2
            # Routes remain independent of whatever SKU was put on the button.
            assert test_cart.purchase_route(test_cart.ROOT/'products/p1-oplata-po-ks2.html') == ('p1', None)
            assert test_cart.purchase_route(test_cart.ROOT/'products/p12-spor-s-summoy.html') == ('p5','/products/p5-shtrafy-uderzhaniya.html')
            assert test_cart.purchase_route(test_cart.ROOT/'products/t1-pervyy-shag-pri-neoplate.html') == (None,None)
            with tempfile.TemporaryDirectory() as directory:
                probe=Path(directory)/'p12-spor-s-summoy.html'
                probe.write_text((test_cart.ROOT/'products/p12-spor-s-summoy.html').read_text().replace('https://nastoronepodryadchika.ru/products/p5-', 'https://foreign.invalid/products/p5-'))
                try:
                    test_cart.purchase_route(probe)
                except ValueError:
                    pass
                else:
                    raise AssertionError('foreign canonical accepted for a retired alias')
            cases+=4
            server, port=desktop.serve()
            base=f'http://127.0.0.1:{port}'
            try:
                for width in [360,390,1366]:
                    mobile=browser.new_page(viewport={'width':width,'height':800})
                    def route(request):
                        url=request.request.url
                        if not url.startswith(base+'/'):
                            request.abort()
                        elif '/app-script.php' in url:
                            request.fulfill(content_type='application/javascript',body=(desktop.ROOT/'app.js').read_text())
                        else:
                            request.continue_()
                    mobile.route('**/*',route)
                    mobile.goto(base+'/index.html',wait_until='networkidle')
                    mobile.evaluate('document.fonts.ready')
                    if width<768:
                        after=mobile.screenshot(full_page=True,animations='disabled')
                        mobile.locator('#checklist-title-fit').evaluate('(e)=>e.remove()')
                        before=mobile.screenshot(full_page=True,animations='disabled')
                        assert after==before, f'mobile pixels changed at {width}'
                    else:
                        size=mobile.locator('.checklist .document h3').evaluate('(e)=>getComputedStyle(e).fontSize')
                        assert size=='38px', size
                        assert not mobile.evaluate(desktop.WORDBREAK_SCRIPT)
                    mobile.close()
                    cases+=1
            finally:
                server.shutdown()
        finally:
            browser.close()
    print(f'Desktop guard contract: {cases} browser cases PASS')


if __name__ == '__main__':
    main()
