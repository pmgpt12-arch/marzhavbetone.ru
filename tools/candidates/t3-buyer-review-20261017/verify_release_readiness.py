#!/usr/bin/env python3
"""Prevent T3 stale price, wrong master, and mismatched buyer copy."""
from pathlib import Path
from zipfile import ZipFile
import hashlib, re, subprocess
root=Path(__file__).resolve().parents[3]
archive=root/'tools/candidates/t3-buyer-review-20261017/T3-vozrazheniya-5-files-business-R1.zip'
source=root/'products-storage/17-odnostoronniy-akt-i-zachet'
with ZipFile(archive) as z:
 assert z.testzip() is None
 assert sorted(z.namelist())==sorted(x.name for x in source.iterdir()), 'T3 source inventory mismatch'
 assert all(hashlib.sha256(z.read(x.name)).digest()==hashlib.sha256(x.read_bytes()).digest() for x in source.iterdir()), 'T3 source content mismatch'
name='Система подготовки возражений на односторонний акт или зачёт'
for path in ['products/t3-odnostoronniy-akt-i-zachet.html','katalog.html']:
 text=(root/path).read_text()
 if path.startswith('products/'):
  assert text.count('data-sku="t3"')==1 and 'data-price="1490000"' in text
  assert '990 ₽' not in text and '99000' not in text
  assert all(n in text for n in ZipFile(archive).namelist())
 else:
  card=re.search(r'<article class="product-card">[^<]*<div class="product-number">T3</div>.*?</article>',text,re.S).group()
  assert card.count('data-sku="t3"')==1 and 'data-price="1490000"' in card and '14 900 ₽' in card
  assert name in card
assert "'price' => 1490000" in (root/'products-config.php').read_text()
print('T3_RELEASE_READINESS_PASS files=5 source_sha=5/5 page_catalog_price=1490000')
