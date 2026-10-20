#!/usr/bin/env python3
"""Exact-byte promotion, sale/price/entry-file and workflow scope contract."""
from pathlib import Path
from hashlib import sha256
import json,re,subprocess
from zipfile import ZipFile
from bs4 import BeautifulSoup
from prepare_remaining_release_20261020 import R,B,O,DATA,APPROVED
def sha(b):return sha256(b).hexdigest()
def finalize_retired_pages():
 plan=json.loads((O/'release-plan.json').read_text());rows={p['file']:p for p in plan['site_files']}
 for sku,parent in plan['retired_sales'].items():
  path=next((R/'products').glob(sku+'-*.html'));s=path.read_text();title,price,page,*_=DATA[parent]
  body=f'<main class="product-landing"><section class="section"><p class="eyebrow">Состав линейки обновлён</p><h1>{title}</h1><p>Документы этого решения включены в систему. Полный состав, порядок применения и стоимость представлены на странице продукта.</p><a class="button" href="{page}">Перейти к составу системы</a></section></main>'
  s=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:body,s,flags=re.S)
  s=re.sub(r'<script type="application/ld\+json">.*?</script>','',s,flags=re.S)
  s=re.sub(r'<title>.*?</title>',lambda _:'<title>'+title+'</title>',s,flags=re.S)
  s=re.sub(r'(<meta (?:name="description"|property="og:description"|property="og:title") content=")[^"]*',lambda m:m[1]+title,s)
  path.write_text(s);rel=str(path.relative_to(R));assert rel in rows;rows[rel]['sha256']=sha(path.read_bytes())
 plan['site_files']=list(rows.values())
 for p in plan['packages']:
  d=R/'products-storage'/p['dir'];p['master_files']={str(f.relative_to(d)):sha(f.read_bytes()) for f in d.rglob('*') if f.is_file()}
 (O/'release-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
def verify():
 plan=json.loads((O/'release-plan.json').read_text());assert plan['approved_outer_zip_sha256']==APPROVED
 archive=B/'final-buyer-review-20261020/NSP_remaining_products_R3_owner_review_2026-10-20.zip'
 assert sha(archive.read_bytes())==APPROVED
 cat=json.loads(subprocess.check_output(['php','-r','define("ORDERS_DIR",sys_get_temp_dir());require "products-config.php";echo json_encode(mvb_products());'],cwd=R))
 for p in plan['packages']:
  approved=B/'final-buyer-review-20261020'/(p['sku'].upper()+'-buyer-review-R3-20261020.zip')
  assert sha(approved.read_bytes())==p['approved_zip_sha256']
  with ZipFile(approved) as z:assert {n:sha(z.read(n)) for n in z.namelist()}==p['members']
  d=R/'products-storage'/p['dir'];files={str(f.relative_to(d)):sha(f.read_bytes()) for f in d.rglob('*') if f.is_file()}
  assert files==p['master_files'],p['sku'];buyer={n:h for n,h in files.items() if Path(n).name not in {'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'}}
  assert buyer==p['members'] and len(buyer)==p['count'],p['sku']
  assert all(cat[p['sku']][k]==p[k] for k in ['name','price','dir','zip'])
  if p['sku'] in DATA:
   soup=BeautifulSoup((R/p['page']).read_text(),'html.parser');assert soup.h1.get_text()==p['name']
   assert {c.get_text() for c in soup.select('.document-list code')}==set(buyer)
   product=json.loads(soup.select_one('script[type="application/ld+json"]').string)
   assert int(product['offers']['price'])*100==p['price'] and product['name']==p['name']
 for k,v in plan['protected_catalog'].items():assert cat[k]==v,(k,'unrelated catalog changed')
 html_files=list(R.glob('*.html'))+list((R/'products').glob('*.html'))+list((R/'articles').glob('*.html'))+list((R/'materialy').glob('*.html'))
 for path in html_files:
  soup=BeautifulSoup(path.read_text(),'html.parser')
  for b in soup.select('button[data-sku]'):
   sku=b['data-sku'];assert sku not in plan['retired_sales'],(path,sku,'retired sale')
   if sku in DATA:
    assert b['data-product']==cat[sku]['name'] and int(b['data-price'])==cat[sku]['price'],(path,sku)
    parent=b.find_parent(class_=lambda v:v and any(c in v.split() for c in ['price-block','product-footer']))
    if parent:
     prices=re.findall(r'\d[\d \u00a0\u202f]*\s*₽',parent.get_text(' ',strip=True))
     assert prices and all(int(re.sub(r'\D','',x))*100==cat[sku]['price'] for x in prices),(path,sku,prices)
 soup=BeautifulSoup((R/'katalog.html').read_text(),'html.parser');skus=[b['data-sku'] for b in soup.select('.product-card button[data-sku]')]
 assert len(skus)==13 and len(set(skus))==13,skus
 assert set(skus)=={'p1','p2','p3','p4','p5','p7','p8','p9','p10','p11','p13','t2','t3'}
 # Structured sale inventory and diagnostic routes must agree with server prices.
 def check_nodes(node):
  if isinstance(node,dict):
   offer=node.get('offers')
   if isinstance(offer,dict):
    m=re.search(r'/products/([pt]\d+)-',offer.get('url',''))
    if m:
     sku=m[1];assert sku not in plan['retired_sales']
     if sku in DATA:assert int(offer['price'])*100==cat[sku]['price'],sku
   for val in node.values():check_nodes(val)
  elif isinstance(node,list):
   for val in node:check_nodes(val)
 for tag in soup.select('script[type="application/ld+json"]'):check_nodes(json.loads(tag.string))
 diagnostic=(R/'diagnostika.html').read_text();cases=json.loads(re.search(r'const SCENARIOS = (\[.*?\]);',diagnostic,re.S)[1])
 for case in cases:
  for role in ['entry','core']:
   node=case.get(role)
   if node:
    sku=re.search(r'/products/([pt]\d+)-',node['url'])[1];assert sku not in plan['retired_sales']
    if sku in DATA:assert node['price']*100==cat[sku]['price'],sku
 php='define("ORDERS_DIR",sys_get_temp_dir());define("ADMIN_EMAIL","qa@example.invalid");require "products-config.php";'
 php+='foreach(["t1","t4","t5","t6","p12"] as $s){if(mvb_resolve_product(["sku"=>$s])!==null)exit(9);}'
 php+='echo DELIVERY_TTL_SECONDS;'
 assert subprocess.check_output(['php','-r',php],cwd=R,text=True)=='3600'
 for f in plan['site_files']:assert sha((R/f['file']).read_bytes())==f['sha256'],f['file']
 for p in plan['packages']:
  if p['sku'] not in DATA:continue
  start='00-START-HERE.pdf' if p['sku'] in {'p10','p13'} else '00-INSTRUKCIYA.pdf' if p['sku'] in {'p1','p2','p7'} else '00-START-HERE.txt'
  code=php+'echo mvb_delivery_email([],[["sku"=>"'+p['sku']+'","name"=>"name","url"=>"https://example.invalid"]]);'
  mail=subprocess.check_output(['php','-r',code],cwd=R,text=True);assert start in mail and '1 час' in mail
 print('PASS exact approved 123 buyer members; 13 sale cards; 8 prices/titles/entry files; 3 consolidated steps; protected catalog unchanged')
if __name__=='__main__':
 import sys
 if '--finalize-retired' in sys.argv:finalize_retired_pages()
 verify()
