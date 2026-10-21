#!/usr/bin/env python3
"""Narrow free DOCX identity/cross-sell edits. No paid directory traversal."""
from pathlib import Path
import json,re,shutil,zipfile,hashlib
from docx import Document
from docx.text.paragraph import Paragraph
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
routes=json.loads((HERE/'routes.json').read_text());old=json.loads((HERE/'old-generator-facts.json').read_text())
old_by_sku={re.search(r'/products/(p\d+)-',v['PAID_URL'])[1]:v for v in old.values()}
proof=[];temp=Path('/tmp/nsp-free-original');temp.mkdir(exist_ok=True)
def paragraph_text(p,text):
 # Map changes across existing w:t runs, leaving all run/paragraph formatting intact.
 nodes=p._p.xpath('.//w:t');original=''.join(n.text or '' for n in nodes)
 import difflib
 for op,a,b,c,d in reversed(difflib.SequenceMatcher(None,original,text,autojunk=False).get_opcodes()):
  if op=='equal':continue
  offsets=[];pos=0
  for n in nodes:offsets.append((pos,pos+len(n.text or ''),n));pos=offsets[-1][1]
  first=next((i for i,(lo,hi,n) in enumerate(offsets) if lo<=a<hi or (a==hi and i==len(offsets)-1)),None)
  if first is None:continue
  last=next((i for i,(lo,hi,n) in enumerate(offsets) if lo<b<=hi),first)
  lo,_,n=offsets[first];prefix=(n.text or '')[:a-lo];suffix=(offsets[last][2].text or '')[b-offsets[last][0]:]
  n.text=prefix+text[c:d]+(suffix if first==last else '')
  for i in range(first+1,last):offsets[i][2].text=''
  if last!=first:offsets[last][2].text=suffix
for route in routes:
 folder=ROOT/'products-storage'/route['folder'];facts=old_by_sku.get(route['sku'],{})
 for p in folder.glob('*.docx'):
  with zipfile.ZipFile(p) as z:hit=any(re.search(r'marzhavbetone|маржа в бетоне',z.read(n).decode(),re.I) for n in z.namelist() if n.endswith(('.xml','.rels')))
  if not hit:continue
  shutil.copy2(p,temp/(p.parent.name+'--'+p.name));before=hashlib.sha256(p.read_bytes()).hexdigest();doc=Document(p);changed=[]
  # Each XML paragraph is included once, including tables/headers/footers.
  containers=[doc.element]+[rel.target_part.element for rel in doc.part.rels.values() if rel.reltype.endswith(('/header','/footer'))]
  visited=set()
  for container in containers:
   for node in container.xpath('.//w:p'):
    if node in visited:continue
    visited.add(node);para=Paragraph(node,doc);text=''.join(n.text or '' for n in node.xpath('.//w:t'));updated=text
    updated=re.sub('marzhavbetone','nastoronepodryadchika',updated,flags=re.I)
    updated=re.sub('маржа в бетоне','На стороне подрядчика',updated,flags=re.I)
    if facts.get('PAID_NAME') and facts['PAID_NAME'] in updated:updated=updated.replace(facts['PAID_NAME'],route['product'][10:-1] if route['product'].startswith('Комплект «') else route['product'])
    if '/products/' in updated or ('Комплект' in updated and '₽' in updated):
     updated=re.sub(r'Стоимость:\s*[\d\s\u00a0]+₽','Стоимость: '+format(route['rubles'],',').replace(',',' ')+' ₽',updated)
     if facts.get('PAID_PRICE'):updated=updated.replace(facts['PAID_PRICE'],format(route['rubles'],',').replace(',',' ')+' ₽')
    if updated!=text:paragraph_text(para,updated);changed.append({'before':text,'after':updated})
  doc.core_properties.author='На стороне подрядчика';doc.core_properties.last_modified_by='На стороне подрядчика'
  doc.save(p)
  with zipfile.ZipFile(p) as a,zipfile.ZipFile(temp/(p.parent.name+'--'+p.name)) as b:assert set(a.namelist())==set(b.namelist()),'UNEXPECTED_PACKAGE_PART_CHANGE'
  # Relationship targets can hold the old address even when the visible label is clean.
  with zipfile.ZipFile(p) as z:entries=[(n,z.read(n)) for n in z.namelist()]
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
   for n,b in entries:
    if n.endswith('.rels'):b=re.sub(b'marzhavbetone',b'nastoronepodryadchika',b,flags=re.I)
    z.writestr(n,b)
  proof.append({'path':str(p.relative_to(ROOT)),'before':before,'after':hashlib.sha256(p.read_bytes()).hexdigest(),'paragraph_changes':changed})
assert len(proof)==24,len(proof)
(HERE/'docx-changes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('DOCX_CHANGED='+str(len(proof)))
