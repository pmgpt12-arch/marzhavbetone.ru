#!/usr/bin/env python3
"""Exact website-only corrections for inherited offers found by the route audit.
No changes to products-config.php, masters, order records or payment handlers.
Demo routes remain public; their sales cards point to the accepted full system.
"""
from __future__ import annotations
import hashlib,html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'
DEMOS={
 'demo/algoritm-pri-zaderzhke-oplaty.html':('p1','p1','/products/p1-oplata-po-ks2.html'),
 'demo/obshchiy-princip-osparivaniya-uderzhaniy.html':('p5','p5','/products/p5-shtrafy-uderzhaniya.html'),
 'demo/pretenziya-na-neoplatu.html':('t1','p1','/products/p1-oplata-po-ks2.html'),
 'demo/strategiya-otveta-na-zamechaniya.html':('p4','p4','/products/p4-ispolnitelnaya-dokumentaciya-pto.html'),
}
RETIRED_PAGE='products/t6-kvartiry-vmesto-deneg.html'
SCOPE=set(DEMOS)|{'index.html',RETIRED_PAGE}
CARD=re.compile(r'<article\b[^>]*class="(?:product-card|solution-card)"[^>]*>.*?</article>',re.S)


def once(text,old,new,where):
    assert text.count(old)==1,('EXACT_OFFER_ANCHOR_DRIFT',where,old[:80],text.count(old))
    return text.replace(old,new)


def money(price):
    assert isinstance(price,int) and price%100==0
    return f'{price//100:,}'.replace(',',' ')+' ₽'


def expected_source(text,rel,manifest):
    if rel not in SCOPE:return text
    if rel in DEMOS:
        oldsku,sku,url=DEMOS[rel]
        marker=f'data-current-system="{sku}"'
        if marker in text:
            assert 'add-to-cart' not in text and url in text,('INVALID_REPAIRED_DEMO',rel)
            return text
        blocks=[m for m in CARD.finditer(text) if f'data-sku="{oldsku}"' in m.group(0)]
        assert len(blocks)==1,('DEMO_SALES_CARD_DRIFT',rel,len(blocks))
        product=manifest[sku];name=html.escape(product['name']);count=len(product['files'])
        block=(f'<article class="product-card" {marker}>\n'
          f'          <h3>{name}</h3>\n'
          f'          <p>Действующий комплект: {count} покупательских файлов. Состав и порядок применения представлены на странице системы.</p>\n'
          f'          <p><strong>{money(product["price"])}</strong></p>\n'
          f'          <p><a class="button" href="{url}">Перейти к составу системы →</a></p>\n'
          '        </article>')
        m=blocks[0]
        return text[:m.start()]+block+text[m.end():]
    if rel=='index.html':
        blocks=[m for m in CARD.finditer(text) if 'data-sku="p5"' in m.group(0)]
        assert len(blocks)==1,('HOME_P5_CARD_DRIFT',len(blocks))
        m=blocks[0];block=m.group(0);target=manifest['p5']
        marker='data-current-offer="p5"'
        if marker in block:
            assert f'data-price="{target["price"]}"' in block and money(target['price']) in block
            return text
        block=once(block,'data-price="299000"',f'data-price="{target["price"]}"',rel)
        block=once(block,'<strong>2 990 ₽</strong>',f'<strong>{money(target["price"])}</strong>',rel)
        tag=re.search(r'<button\b[^>]*data-sku="p5"[^>]*>',block)
        assert tag and 'data-product=' in tag.group(0)
        updated=re.sub(r'data-product="[^"]*"','data-product="'+html.escape(target['name'],quote=True)+'"',tag.group(0),count=1)
        block=once(block,tag.group(0),updated,rel)
        block=once(block,'<article class="solution-card">','<article class="solution-card" '+marker+'>',rel)
        return text[:m.start()]+block+text[m.end():]
    marker='data-retired-route="t6-to-p11"'
    if marker in text:
        assert 'data-sku="t6"' not in text and '/products/p11-raschet-metrami.html' in text
        return text
    assert text.count('data-sku="t6"')==1,'T6_EXPECTED_ONE_RETIRED_BUTTON'
    target=manifest['p11'];name=html.escape(target['name'])
    main=re.search(r'<main\b[^>]*>.*?</main>',text,re.S);assert main,'T6_MAIN_MISSING'
    replacement=(f'<main class="product-landing" {marker}><section class="section">'
      '<p class="eyebrow">Состав линейки обновлён</p>'
      f'<h1>{name}</h1>'
      '<p>Документы T6 включены в систему P11. Отдельная покупка T6 недоступна. '
      'Полный состав, порядок применения и стоимость представлены на странице действующей системы.</p>'
      '<a class="button" href="/products/p11-raschet-metrami.html">Перейти к составу системы</a>'
      '</section><section class="section"><p>По ранее оформленному заказу: '
      '<a href="mailto:marzhavbetone@yandex.ru">marzhavbetone@yandex.ru</a>.</p></section></main>')
    text=text[:main.start()]+replacement+text[main.end():]
    # T6 is already noindex and forwards to P11. Remove obsolete Product/Offer
    # and FAQ sales schema rather than advertising an unavailable separate SKU.
    text,n=re.subn(r'\s*<script\s+type="application/ld\+json">.*?</script>','',text,flags=re.S)
    assert n==1,('T6_SCHEMA_COUNT',n)
    text,n=re.subn(r'<title>.*?</title>','<title>'+name+'</title>',text,count=1,flags=re.S);assert n==1
    description='Документы T6 включены в систему P11. Актуальный состав и стоимость — на странице системы.'
    for attribute,key,value in [('name','description',description),('property','og:title',target['name']),('property','og:description',description)]:
        pattern=r'(<meta\s+'+attribute+'="'+key+r'"\s+content=")[^"]*(">)'
        text,n=re.subn(pattern,lambda m:m.group(1)+html.escape(value,quote=True)+m.group(2),text,count=1)
        assert n==1,('T6_META_ANCHOR',key)
    assert 'data-sku="t6"' not in text and '"@type": "Offer"' not in text
    return text


def apply_verified(plan):
    audit_path=OUT/'commercial-route-audit.json'
    audit=json.loads(audit_path.read_text())
    known={
      ('demo/obshchiy-princip-osparivaniya-uderzhaniy.html','p5','299000'),
      ('demo/pretenziya-na-neoplatu.html','t1','99000'),
      ('demo/strategiya-otveta-na-zamechaniya.html','p4','299000'),
      ('index.html','p5','299000'),
      ('products/t6-kvartiry-vmesto-deneg.html','t6','99000'),
    }
    issues=audit['price_or_retired_purchase_issues']
    # First execution corrects only the complete observed class; subsequent
    # executions must be already clean, not discover new unexpected mutations.
    assert not issues or {(r['page'],r['sku'],r['price']) for r in issues}==known,'UNREVIEWED_NEW_OFFER_DEFECT'
    assert all(r['inherited_from_published_main'] for r in issues),'NONBASELINE_DEFECT_REQUIRES_REVIEW'
    manifest=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
    declared={r['file']:r for r in plan['shipping_files']}
    pending=[];evidence=[]
    for rel in sorted(SCOPE):
        p=ROOT/rel;raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==declared[rel]['sha256'],'UNREVIEWED_SHIPPING_DRIFT:'+rel
        before=raw.decode('utf-8');after=expected_source(before,rel,manifest)
        assert expected_source(after,rel,manifest)==after,'OFFER_REPAIR_NOT_IDEMPOTENT:'+rel
        pending.append((p,after))
        evidence.append({'page':rel,'before_sha256':hashlib.sha256(raw).hexdigest(),
          'after_sha256':hashlib.sha256(after.encode()).hexdigest(),'changed':after!=before})
    if issues:
        (OUT/'commercial-route-audit-before-corrections.json').write_bytes(audit_path.read_bytes())
    for p,after in pending:p.write_text(after,encoding='utf-8')
    for row in plan['shipping_files']:
        if row['file'] in SCOPE:
            data=(ROOT/row['file']).read_bytes();row.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
    (OUT/'offer-route-corrections.json').write_text(json.dumps({
      'status':'APPLIED_PENDING_FULL_ROUTE_ACCEPTANCE','observed_inherited_defects':len(issues),
      'scope':evidence,'server_catalog_prices_changed':False,'buyer_documents_changed':False,
      'policy':'Demo cards explain current system and link directly to its accepted page; no obsolete buy buttons. T6 uses the existing retired-product bridge pattern to P11. Historical demo prose is not re-certified; no buyer master is restored.',
      'allowed_route_changes':{'demo/pretenziya-na-neoplatu.html':'old T1 offer -> direct P1 page',
        'products/t6-kvartiry-vmesto-deneg.html':'retired T6 sales body -> P11 information bridge'},
      'remaining_historical_demo_warning':'Original excerpt/source-reference checks remain under the preexisting build_preview classification; no legal or content acceptance is claimed.'
    },ensure_ascii=False,indent=2)+'\n')
    return manifest
