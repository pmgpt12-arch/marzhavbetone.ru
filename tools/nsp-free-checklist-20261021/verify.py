#!/usr/bin/env python3
"""Public PDF gate: text/metadata/URLs, 20 checkpoints, accepted catalog facts."""
import hashlib,json,re,sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
pdf=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'downloads/checklist-zakrytiya-rabot.pdf'
data=json.loads((HERE/'content.json').read_text());reader=PdfReader(pdf);assert len(reader.pages)==2 and not reader.is_encrypted
normalize=lambda s:re.sub(r'\s+',' ',s).strip()
texts=[normalize(page.extract_text()) for page in reader.pages];alltext=' '.join(texts)+' '+str(reader.metadata)
assert not re.search(r'маржа\s+в\s+бетоне|marzhavbetone|зач[её]т|40 документов|10 документов',alltext,re.I),'STALE_BRAND_OR_PRODUCT_FACT'
assert 'На стороне подрядчика' in str(reader.metadata) and 'НА СТОРОНЕ ПОДРЯДЧИКА' in texts[0]
assert len(data['sections'])==4 and all(len(s['items'])==5 for s in data['sections'])
for section in data['sections']:
 for item in section['items']:assert normalize(item) in texts[0],item
# Each source sentence occurs once; PDF checkbox squares are drawn as vectors.
assert sum(texts[0].count(normalize(i)) for s in data['sections'] for i in s['items'])==20
catalog=(ROOT/'katalog.html').read_text()
for p in data['products']:
 article=next(a for a in re.findall(r'<article\b.*?</article>',catalog,re.S) if 'data-sku="'+p['sku']+'"' in a)
 assert 'data-price="'+str(p['rubles']*100)+'"' in article and p['name'] in article
 assert p['name'] in texts[1] and str(p['files'])+' файлов' in texts[1]
 assert str(p['files'])+' файлов' in article,'CATALOG_FILE_COUNT_'+p['sku']
urls=[]
for page in reader.pages:
 for ref in page.get('/Annots',[]):
  a=ref.get_object().get('/A',{});uri=a.get('/URI')
  if uri:urls.append(str(uri))
expected={p['url'] for p in data['products']}|{url for _,url in data['contacts']}|{'https://nastoronepodryadchika.ru/'}
assert set(urls)==expected and len(urls)==9,(urls,expected)
for label,_ in data['contacts']:assert normalize(label) in texts[1]
# No scripts/forms/hidden attachment payload is expected in this public checklist.
assert not reader.get_fields() and '/OpenAction' not in reader.trailer['/Root']
print(json.dumps({'status':'PASS','sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':2,'checkpoints':20,'product_cards':4,'links':len(urls),'metadata_brand':'PASS','stale_brand':'ABSENT','catalog_prices':'MATCH'},ensure_ascii=False))
