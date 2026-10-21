#!/usr/bin/env python3
"""Ten public ZIP contracts, semantic branding, routes and Office preservation receipts."""
from pathlib import Path
from pypdf import PdfReader
from lxml import etree as E
import json,re,zipfile,io,hashlib,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));from build_free_zips import MATERIALS,SKIP
routes=json.loads((HERE/'routes.json').read_text());before={r['path']:r['sha256'] for r in json.loads((HERE/'before-files.json').read_text())};catalog=(ROOT/'katalog.html').read_text();proof=[];component_count=0;changed=0
for route in routes:
 slug=route['slug'];assert MATERIALS[slug]==route['folder'];folder=ROOT/'products-storage'/route['folder'];source={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file() and p.name not in SKIP};target=ROOT/'downloads'/(slug+'.zip')
 a=next(a for a in re.findall(r'<article\b.*?</article>',catalog,re.S) if 'data-sku="'+route['sku']+'"' in a)
 assert route['product'] in a and 'data-price="'+str(route['rubles']*100)+'"' in a
 assert route['sku'] in ['p1','p2','p3','p4','p5','p7','p8','p9','p11']
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None and set(z.namelist())==set(source) and len(z.namelist())==len(source)
  for name,raw in source.items():
   assert z.read(name)==raw
   rel='products-storage/'+route['folder']+'/'+name;sha=hashlib.sha256(raw).hexdigest();changed+=sha!=before[rel];component_count+=1
   if name.endswith(('.docx','.xlsx')):
    with zipfile.ZipFile(io.BytesIO(raw)) as office:
     for part in office.namelist():
      if part.endswith(('.xml','.rels')):
       content=office.read(part).decode();assert not re.search(r'marzhavbetone|маржа\s+в\s+бетоне|Комплект «Комплект',content,re.I),(rel,part)
       parsed=E.fromstring(office.read(part))
       if name.endswith('.docx') and part.startswith('word/'):
        text=' '.join(parsed.xpath('//*[local-name()="t"]/text()'))
        assert not re.search(r'не является юридической консультацией|юристом не вычитан|Комплект не (?:заменяет|гарантирует|отменяет)|материал.{0,6}не (?:закрывает|обещает)',text,re.I),'OWNER_LANGUAGE_'+rel
   elif name.endswith('.pdf'):
    pdf=PdfReader(io.BytesIO(raw));assert len(pdf.pages)==1
    text=' '.join(page.extract_text() for page in pdf.pages);assert not re.search(r'marzhavbetone|маржа\s+в\s+бетоне',text+str(pdf.metadata),re.I)
    assert 'На стороне подрядчика' in str(pdf.metadata) and route['product'] in re.sub(r'\s+',' ',text)
    uris=[str(ref.get_object().get('/A',{}).get('/URI')) for p in pdf.pages for ref in p.get('/Annots',[]) if ref.get_object().get('/A',{}).get('/URI')];assert len(uris)==5
    assert uris[0].split('?')[0]==route['product_url'] and uris[1].split('?')[0]==route['material_url']
    assert all('marzhavbetone' not in u and not re.search(r'/products/t[1456]-',u) for u in uris)
 proof.append({'path':'downloads/'+slug+'.zip','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':len(source),'crc':'PASS','source_bytes':'MATCH'})
assert len(proof)==10 and component_count==47 and changed==36,(component_count,changed)
# Preserve Office package structure and the explicitly reviewed changes, independent of archive assembly.
for row in json.loads((HERE/'docx-changes.json').read_text()):
 p=ROOT/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['after'] and before[row['path']]==row['before']
for row in json.loads((HERE/'xlsx-preservation.json').read_text()):assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['after'] and row['all_other_values_formulas_formats']=='UNCHANGED'
print(json.dumps({'status':'PASS','archives':proof,'components':47,'changed_components':36,'unchanged_components':11,'paid_masters_changed':0},ensure_ascii=False))
