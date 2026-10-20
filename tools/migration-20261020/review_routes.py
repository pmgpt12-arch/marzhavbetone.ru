#!/usr/bin/env python3
"""One bounded migration unit: route/context preservation and native UI acceptance.
No SSH, production writes, payment calls, buyer-file editing or retired-SKU revival.
Uses the existing migration workflow, manifest generator, link and browser tests.
"""
from __future__ import annotations
import copy, functools, hashlib, http.server, importlib.util, json, os, re
import shutil, subprocess, threading
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
OUT = D / 'evidence'
MARKER = '/* NSP migration 20261020: section headings must not size article-card titles. */'
CSS_FIX = '''\n/* NSP migration 20261020: section headings must not size article-card titles. */
body.rebrand-approved .showcase-card h2{
  font-size:clamp(22px,1.9vw,28px);
  line-height:1.2;
  letter-spacing:-.025em;
  overflow-wrap:normal;
  word-break:normal;
}
'''
OWN_HOSTS = {'marzhavbetone.ru','www.marzhavbetone.ru','nastoronepodryadchika.ru','www.nastoronepodryadchika.ru'}
RETIRED = {'t1':'p1','t4':'p9','t5':'p8','t6':'p11','p12':'p5'}


def run(args, timeout=30):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=True, timeout=timeout)


def write(name, value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def git_source(base, rel):
    return run(['git','show',base+':'+rel]).stdout


def normalize_url(value, page):
    absolute = urljoin('https://nastoronepodryadchika.ru/'+page,value)
    parts = urlsplit(absolute)
    if parts.hostname in OWN_HOSTS:
        return 'SITE:'+urlunsplit(('', '', parts.path or '/', parts.query, parts.fragment))
    return value


class PageLinks(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links=[];self.buttons=[]
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        for key in ('href','src','action','poster'):
            if a.get(key) is not None and 'brand-approved-2026.css' not in a[key]:
                self.links.append((tag,key,a[key]))
        if tag=='button' and 'add-to-cart' in (a.get('class') or '').split():
            self.buttons.append({k:a.get(k) for k in ('data-sku','data-price','data-product')})


def links_signature(source, page):
    return [(t,k,normalize_url(v,page)) for t,k,v in PageLinks(source).links]


def scenarios(source):
    match=re.search(r'const SCENARIOS\s*=\s*(\[.*?\]);',source,re.S)
    if not match:raise AssertionError('DIAGNOSTIC_SCENARIOS_MISSING')
    return json.loads(match.group(1))


def source_review(contract, plan):
    base=contract['approved_base_commit']
    run(['git','fetch','--no-tags','--depth=1','origin','main'],45)
    assert run(['git','rev-parse','FETCH_HEAD']).stdout.strip()==base,'MAIN_ADVANCED_RECONCILIATION_REQUIRED'
    active=contract['active_skus']
    pages=sorted(x['file'] for x in plan['shipping_files'] if x['file'].endswith('.html'))
    assert len(pages)==88,'PUBLIC_ROUTE_SCOPE_DRIFT'
    rows=[];old_intermediates=[]
    for rel in pages:
        before=git_source(base,rel);now=(ROOT/rel).read_text(encoding='utf-8')
        assert links_signature(before,rel)==links_signature(now,rel),'ROUTE_OR_QUERY_OR_FRAGMENT_CHANGED:'+rel
        bp,np=PageLinks(before),PageLinks(now)
        assert bp.buttons==np.buttons,'COMMERCE_BINDING_CHANGED:'+rel
        for b in np.buttons:
            sku=b['data-sku']
            if sku=='test1':continue
            assert sku in active and sku not in RETIRED,'RETIRED_OR_UNKNOWN_PURCHASE:'+rel+':'+str(sku)
            assert int(b['data-price'])==active[sku]['price'],'PRICE_DRIFT:'+rel+':'+sku
        product_links=[]
        for tag,key,value in np.links:
            if tag!='a' or key!='href':continue
            normalized=normalize_url(value,rel)
            if not normalized.startswith('SITE:/products/'):continue
            match=re.search(r'/products/([pt]\d+)-',normalized)
            if match:
                sku=match.group(1)
                product_links.append({'url':normalized[5:],'sku':sku,'retired':sku in RETIRED,'successor':RETIRED.get(sku)})
                if sku in RETIRED:old_intermediates.append({'source':rel,'target':normalized[5:],'retired_sku':sku,'successor':RETIRED[sku]})
        rows.append({'page':rel,'source_sha256':hashlib.sha256(before.encode()).hexdigest(),
                     'candidate_sha256':hashlib.sha256(now.encode()).hexdigest(),
                     'link_count':len(np.links),'route_signature_preserved':True,
                     'product_links':product_links,'purchase_buttons':np.buttons})
    before=scenarios(git_source(base,'diagnostika.html'))
    after=scenarios((ROOT/'diagnostika.html').read_text())
    assert after==before,'DIAGNOSTIC_DECISION_TREE_CHANGED'
    assert len(after)==12,'DIAGNOSTIC_SCENARIO_COUNT_DRIFT'
    for scenario in after:
        for role in ('entry','core'):
            offer=scenario.get(role)
            if not offer:continue
            m=re.search(r'/products/([pt]\d+)-',offer['url']);assert m,scenario['id']
            sku=m.group(1)
            assert sku in active and sku not in RETIRED,'DIAGNOSTIC_RETIRED_SKU:'+scenario['id']
            assert offer['price']*100==active[sku]['price'],'DIAGNOSTIC_PRICE:'+scenario['id']
    forbidden=['data/business/diagnostic.yaml','data/business/money-pains.yaml']
    assert all(not (ROOT/p).exists() for p in forbidden),'DELETED_DIAGNOSTIC_SOURCE_RESTORED'
    for rel in ['payment.php','webhook.php','check-payment.php','download.php','app.js','attribution.js']:
        actual=(ROOT/rel).read_bytes()
        old=subprocess.run(['git','show',base+':'+rel],cwd=ROOT,capture_output=True,check=True,timeout=20).stdout
        assert actual==old,'CHECKOUT_OR_ATTRIBUTION_CODE_CHANGED:'+rel
    spec=importlib.util.spec_from_file_location('nsp_inspection',D/'inspect_backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    manifest=module.repo_manifest()
    accepted=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
    assert manifest==accepted,'BUYER_172_FILE_OR_CATALOG_DRIFT'
    redirect=(D/'old-domain-cutover.htaccess').read_text()
    assert 'RewriteCond %{REQUEST_METHOD} ^(?:GET|HEAD)$' in redirect
    assert 'https://nastoronepodryadchika.ru%{REQUEST_URI}' in redirect
    assert '^\\.well-known/acme-challenge/' in redirect
    assert '^ healthcare' not in redirect
    assert '^ medication' not in redirect
    assert '^ materials' not in redirect
    assert '^ financial' not in redirect
    assert '^ housing' not in redirect
    assert '^(?:payment|webhook|check-payment|download|contact)\\.php$ - [L]' in redirect,'PAYMENT_POST_REDIRECT_GUARD_MISSING'
    report={'status':'PASS_ROUTE_AND_BUYER_SOURCE_INVARIANTS','baseline':base,
      'public_pages':len(pages),'diagnostic_scenarios':after,'diagnostic_scenario_count':len(after),
      'independent_product_choice_MB007':'preserved; not a compulsory entry-then-core purchase ladder',
      'diagnostic_legacy_generator':'DO_NOT_RUN: deleted YAML sources intentionally absent',
      'active_skus':sorted(active),'retired_to_successor':RETIRED,'buyer_files':172,
      'payment_and_attribution_sources_unchanged':True,'pages':rows,
      'legacy_product_intermediates':old_intermediates,
      'legacy_intermediates_policy':'Existing links preserved; no retired purchase button. Semantic Product Fit not inferred from link existence.',
      'redirect_check':'source-only GET/HEAD and POST exemption; not live HTTP acceptance',
      'unimplemented_growth_routes':'AIOS #367/#423/#427 and site #268 remain separate accepted-dependency gates',
      'production_touched':False}
    write('route-source-review.json',report)
    print('ROUTE_SOURCE_PASS',len(pages),'PAGES',len(after),'SCENARIOS',len(active),'SKUS',flush=True)
    return report


def fix_typography(plan):
    # Root cause: broad .section h2 selector overrides editorial card typography.
    # Keep the accepted theme; append the narrow component rule, not a redesign.
    for row in plan['shipping_files']:
        p=ROOT/row['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],'UNREVIEWED_SHIPPING_DRIFT:'+row['file']
    css=ROOT/'brand-approved-2026.css';text=css.read_text()
    if MARKER not in text:css.write_text(text.rstrip()+'\n'+CSS_FIX,encoding='utf-8')
    else:assert CSS_FIX.strip() in text,'CARD_FIX_MARKER_WITH_DIFFERENT_CONTENT'
    run(['python3','tools/asset_versions.py','--write'])
    run(['python3','tools/asset_versions.py','--check'])
    for row in plan['shipping_files']:
        data=(ROOT/row['file']).read_bytes();row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
    plan['route_typography_revision']='20261020-scoped-showcase-h2'
    write('prepared-site-plan.json',plan)


def card_browser_review():
    from playwright.sync_api import sync_playwright
    class Static(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Static,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    rows=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.set_default_timeout(10000)
            page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            for width in (390,1366,1440,1600,1920):
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/articles/index.html',wait_until='domcontentloaded')
                page.wait_for_timeout(300)
                metrics=page.evaluate('''() => ({scroll:document.documentElement.scrollWidth,width:innerWidth,
                  headings:[...document.querySelectorAll('.showcase-card h2')].map(e=>{
                    const s=getComputedStyle(e),r=e.getBoundingClientRect(),c=document.createElement('canvas').getContext('2d');
                    c.font=[s.fontStyle,s.fontWeight,s.fontSize,s.fontFamily].join(' ');
                    const words=e.textContent.trim().split(/\\s+/);
                    return {text:e.textContent.trim(),font:parseFloat(s.fontSize),width:r.width,
                      longest:Math.max(0,...words.map(w=>c.measureText(w).width))};})})''')
                assert metrics['scroll']<=width+1,('EDITORIAL_OVERFLOW',width,metrics['scroll'])
                assert metrics['headings'],'NO_EDITORIAL_CARDS'
                assert all(h['font']<=28.1 for h in metrics['headings']),('CARD_INHERITS_SECTION_H2',width)
                assert all(h['longest']<=h['width']+2 for h in metrics['headings']),('BROKEN_CARD_WORD',width)
                rows.append({'width':width,'cards':len(metrics['headings']),'pass':True,'headings':metrics['headings']})
            browser.close()
        write('route-card-browser.json',{'status':'PASS_COMPONENT_TYPOGRAPHY','viewports':rows,'external_calls':False})
    finally:
        server.shutdown();server.server_close()
    print('CARD_TYPOGRAPHY_PASS',len(rows),'VIEWPORTS',flush=True)


def main():
    contract=json.loads((D/'contract.json').read_text())
    plan_path=OUT/'prepared-site-plan.json';original_plan=plan_path.read_bytes()
    plan=json.loads(original_plan)
    checkpoint={'status':'RUNNING','source_main':contract['approved_base_commit'],
      'run':os.getenv('GITHUB_RUN_ID'),'production_touched':False,'payment_submitted':False}
    try:
        source_review(contract,plan)
        fix_typography(plan)
        for cmd in [
          ['python3','tools/check_nav.py'],['python3','tools/link_audit.py','--verify'],
          ['python3','tools/build_sitemap.py','--verify'],
          ['node','tools/test_diagnostic_sku_standalone.js']]:
            output=run(cmd,60);print(output.stdout[-2000:],flush=True)
        card_browser_review()
        output=run(['python3',str(D/'test_candidate.py')],300)
        print(output.stdout[-3000:],flush=True)
        source_review(contract,plan)
        checkpoint.update(status='PASS_ROUTES_AND_CURRENT_13SKU_BROWSER',pages=88,
          scenarios=12,active_skus=13,buyer_files=172,card_viewports=5,
          remaining='remote scoped dry-run; isolated staging; live payment/email/13 downloaded ZIPs; redirects')
    except Exception as exc:
        plan_path.write_bytes(original_plan)
        checkpoint.update(status='FAIL_ROUTE_REVIEW_OR_UI',error=type(exc).__name__+':'+str(exc)[:2000])
        raise
    finally:
        write('route-review-checkpoint.json',checkpoint)
    print('ROUTES_AND_CANDIDATE_VERIFIED_NO_CUTOVER',flush=True)


if __name__=='__main__':main()
