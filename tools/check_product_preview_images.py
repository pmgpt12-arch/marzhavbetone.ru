#!/usr/bin/env python3
"""Browser gate for product hero images; detects missing and zero-width images."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_JS = """() => {
  const image=document.querySelector('.product-hero img');
  if (!image) return {ok:false,reason:'HERO_IMAGE_MISSING'};
  const rect=image.getBoundingClientRect(), css=getComputedStyle(image);
  const ok=image.complete && image.naturalWidth>0 && image.naturalHeight>0
    && rect.width>0 && rect.height>0 && css.display!=='none'
    && css.visibility!=='hidden' && Number(css.opacity)>0;
  return {ok,reason:ok?'PASS':'HERO_IMAGE_INVALID',complete:image.complete,
    naturalWidth:image.naturalWidth,naturalHeight:image.naturalHeight,
    renderedWidth:Math.round(rect.width),renderedHeight:Math.round(rect.height),
    display:css.display,visibility:css.visibility,opacity:css.opacity};
}"""

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--screenshots-dir',type=Path)
    ap.add_argument('--only-p1',action='store_true')
    args=ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
        from check_mobile import serve, chromium_nearby
    except ImportError as ex:
        print(f'NOT_RUN missing playwright: {ex}',file=sys.stderr)
        return 2

    pages = ([ROOT/'products/p1-oplata-po-ks2.html'] if args.only_p1
             else sorted((ROOT/'products').glob('*.html')))
    issues=[]; receipts=[]
    if args.screenshots_dir:args.screenshots_dir.mkdir(parents=True,exist_ok=True)
    server,port=serve()
    try:
        with sync_playwright() as browser_api:
            kwargs={'headless':True}
            chrome=chromium_nearby()
            if chrome:kwargs['executable_path']=str(chrome)
            browser=browser_api.chromium.launch(**kwargs)
            try:
                for path in pages:
                    rel=path.relative_to(ROOT).as_posix()
                    viewports=[('desktop',1440,900)]
                    if path.name=='p1-oplata-po-ks2.html':
                        viewports.append(('mobile',390,844))
                    for viewport,width,height in viewports:
                        page=browser.new_page(viewport={'width':width,'height':height},
                                              device_scale_factor=1)
                        try:
                            response=page.goto(f'http://127.0.0.1:{port}/{rel}',
                                               wait_until='domcontentloaded',timeout=12000)
                            if not response or response.status>=400:
                                raise RuntimeError('page HTTP error')
                            image=page.locator('.product-hero img')
                            if image.count()==0:
                                issues.append(f'{rel}@{viewport}: HERO_IMAGE_MISSING')
                                continue
                            image.scroll_into_view_if_needed(timeout=7000)
                            try:
                                page.wait_for_function(
                                    "() => document.querySelector('.product-hero img')?.complete === true",
                                    timeout=5000)
                            except Exception:
                                pass
                            observed=page.evaluate(CHECK_JS)
                            receipts.append({'page':rel,'viewport':viewport,**observed})
                            if not observed['ok']:
                                issues.append(f"{rel}@{viewport}: {observed['reason']}")
                            if path.name=='p1-oplata-po-ks2.html' and observed['ok']:
                                if args.screenshots_dir:
                                    page.screenshot(path=str(args.screenshots_dir/
                                        f'p1-{viewport}-hero.png'))
                                    page.evaluate('window.scrollTo(0,0)')
                                    page.screenshot(path=str(args.screenshots_dir/
                                        f'p1-{viewport}-firstscreen.png'))
                                # A missing node and zero geometric width MUST fail the gate.
                                page.evaluate("() => {document.querySelector('.product-hero img').style.transform='scaleX(0)'}")
                                mutated=page.evaluate(CHECK_JS)
                                if mutated['ok'] or mutated.get('renderedWidth')!=0:
                                    issues.append('NEGATIVE_GATE_FAILED: width=0')
                                page.evaluate("() => document.querySelector('.product-hero img').remove()")
                                if page.evaluate(CHECK_JS)['ok']:
                                    issues.append('NEGATIVE_GATE_FAILED: missing image')
                        except Exception as ex:
                            issues.append(f'{rel}@{viewport}: {type(ex).__name__}: {str(ex)[:140]}')
                        finally:
                            page.close()
            finally:
                browser.close()
    finally:
        server.shutdown();server.server_close()
    print(json.dumps({'tested':len(receipts),'passed':sum(bool(x['ok']) for x in receipts),
                      'failures':issues,'p1':[x for x in receipts if x['page'].endswith('p1-oplata-po-ks2.html')]},
                      ensure_ascii=False))
    return 1 if issues else 0

if __name__=='__main__':sys.exit(main())
