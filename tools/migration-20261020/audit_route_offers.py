#!/usr/bin/env python3
"""Read-only scan of all route offers, including demo/free/article pages.
Collect every mismatch before failing a release gate; do not rebuild documents.
"""
from __future__ import annotations
import hashlib,json,re,subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'

class Offers(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True)
        self.buttons=[];self.links=[];self.verbatim=[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='button' and 'add-to-cart' in (a.get('class') or '').split():
            self.buttons.append({'sku':a.get('data-sku'),'price':a.get('data-price'),
              'name':a.get('data-product'),'line':self.getpos()[0],'source_tag':self.get_starttag_text()})
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if a.get('data-verbatim'):self.verbatim.append(a['data-verbatim'])

def main():
    c=json.loads((D/'contract.json').read_text())
    m=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
    plan=json.loads((OUT/'prepared-site-plan.json').read_text())
    base=c['approved_base_commit'];pages=[r['file'] for r in plan['shipping_files'] if r['file'].endswith('.html')]
    rows=[];issues=[];references=[];historical=[]
    for rel in sorted(pages):
        text=(ROOT/rel).read_text();doc=Offers(text)
        old=subprocess.run(['git','show',base+':'+rel],cwd=ROOT,text=True,capture_output=True,check=True,timeout=15).stdout
        baseline=Offers(old)
        for button in doc.buttons:
            sku=button['sku'];price=button['price'];expected=m.get(sku)
            if sku=='test1':continue
            issue=None
            if sku in c['retired_skus']:issue='RETIRED_SKU_PURCHASE'
            elif expected is None:issue='UNKNOWN_SKU_PURCHASE'
            elif price!=str(expected['price']):issue='PRICE_DISAGREES_WITH_SERVER'
            observation={'page':rel,**button,'expected_price':expected['price'] if expected else None,
              'expected_name':expected['name'] if expected else None,'issue':issue,
              'inherited_from_published_main':any(x['sku']==sku and x['price']==price and x['name']==button['name'] for x in baseline.buttons)}
            rows.append(observation)
            if issue:issues.append(observation)
        for fragment in doc.verbatim:
            p=ROOT/'products-storage'/fragment
            references.append({'page':rel,'buyer_source':fragment,'exists_in_current_master_tree':p.is_file(),
              'classification':'SOURCE_EXISTENCE_ONLY_NOT_CONTENT_ACCEPTANCE' if p.is_file() else 'PREEXISTING_STALE_DEMO_SOURCE',
              'must_not_restore_archived_buyer_documents':True})
        for href in doc.links:
            u=urlsplit(urljoin('https://nastoronepodryadchika.ru/'+rel,href))
            match=re.search(r'^/products/([pt]\d+)-',u.path)
            if u.hostname in {c['old_domain'],c['new_domain']} and match and match.group(1) in c['retired_skus']:
                historical.append({'source':rel,'target':u.path,'retired_sku':match.group(1)})
    report={'status':'INVENTORY_COMPLETE_WITH_BLOCKERS' if issues else 'PASS_ALL_PUBLIC_PURCHASE_PRICES',
      'source_main':base,'candidate_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'html_pages':len(pages),'purchase_buttons_checked':len(rows),'price_or_retired_purchase_issues':issues,
      'all_offers':rows,'demo_source_references':references,'legacy_intermediate_links':historical,
      'buyer_files_edited':False,'production_touched':False,
      'interpretation':'Existing four integration warnings are not relabelled PASS. A published-main mismatch is inherited, but still requires an explicit website-price correction before accepting migration. Do not repair stale demos by restoring old buyer files.'}
    (OUT/'commercial-route-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('ROUTE_OFFER_INVENTORY',len(pages),'PAGES',len(rows),'BUTTONS',len(issues),'BLOCKERS',flush=True)
    for row in issues:print(row['page'],row['sku'],row['price'],'EXPECTED',row['expected_price'],'INHERITED',row['inherited_from_published_main'],flush=True)

if __name__=='__main__':main()
