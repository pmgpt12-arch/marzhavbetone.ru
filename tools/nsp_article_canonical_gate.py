#!/usr/bin/env python3
"""READ-ONLY gate for current approved article/source snapshot. Exit nonzero on drift."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,zipfile,requests,sys
N=Path('/mnt/server-data/nsp')
ref=N/'operations/NSP_CANONICAL_ACTIVE_20261111.json'
d=json.loads(ref.read_text())
assert d['decision']=='PUBLISHED_APPROVED_ARTICLES_ARE_SOURCE_OF_TRUTH'
assert len(d['paid_articles'])==d['paid_products_count']==11
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for path,key in [(Path(d['public_site_reference_zip']),'public_site_sha256'),(Path(d['product_reference_zip']),'product_reference_sha256')]:
 assert path.is_file() and sha(path)==d[key],('CANON_SNAPSHOT_SHA_MISMATCH',str(path))
 with zipfile.ZipFile(path) as z:assert z.testzip() is None
print('CANON_ARCHIVE_SHA_AND_CRC_PASS 2',flush=True)
prod=Path(d['product_reference_zip'])
with zipfile.ZipFile(prod) as z:
 manifest=json.loads(z.read('CANONICAL_PRODUCT_SNAPSHOT_MANIFEST.json'))
 for item in manifest['paid_products']:
  with zipfile.ZipFile(__import__('io').BytesIO(z.read(item['archive']))) as inner:
   assert inner.testzip() is None and len(inner.namelist())==item['file_count']
 for item in manifest['free_products']:
  raw=z.read(item['archive']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
assert manifest['paid_count']==manifest['free_count']==11
print('CANON_PRODUCTS_11_PAID_11_FREE_MEMBER_COUNTS_PASS',flush=True)
site=Path(d['public_site_reference_zip'])
with zipfile.ZipFile(site) as z:
 idx=json.loads(z.read('SITE_PUBLIC_CANON_MANIFEST.json'))
 assert idx['pages_from_sitemap']==82 and idx['previews_from_11_paid_editorials']==44
 for a in d['paid_articles']:
  relative=a['article_url'].split('nastoronepodryadchika.ru/',1)[1]
  assert hashlib.sha256(z.read(relative)).hexdigest()==a['article_sha256']
print('CANON_SITE_82_PAGES_44_PREVIEWS_ARTICLE_SHA_PASS',flush=True)
def check(a):
 r=requests.get(a['article_url'],timeout=13,headers={'Cache-Control':'no-cache','Accept-Encoding':'identity'})
 got=hashlib.sha256(r.content).hexdigest()
 return a['sku'],r.status_code,got==a['article_sha256']
with ThreadPoolExecutor(max_workers=4) as pool:checks=list(pool.map(check,d['paid_articles']))
for sku,code,ok in checks:
 print('LIVE_ARTICLE_CANON',sku,code,'SHA_PASS' if ok else 'SHA_DRIFT',flush=True)
assert all(code==200 and ok for _,code,ok in checks),('ARTICLE_SOURCE_DRIFT',checks)
print('NSP_ARTICLE_CANONICAL_REFERENCE_GATE_PASS; PRODUCT_NATIVE_QA_AND_PAYMENT_E2E_NOT_INCLUDED',flush=True)
