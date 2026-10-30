from pathlib import Path
from copy import deepcopy
import shutil, json, hashlib
from docx import Document
from docx.shared import Pt,Twips
from docx.oxml.ns import qn
from layout_helpers import norm,elem
R=Path(__file__).resolve().parent; S=R/'source'; O=R/'candidate'; I=R/'internal'
O.mkdir(exist_ok=True);I.mkdir(exist_ok=True)
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in S.iterdir():
 if p.suffix in ['.pdf','.xlsx']:shutil.copyfile(p,O/p.name)
changes=[]
for p in sorted(S.glob('*.docx')):
 d=Document(p)
 # Move letter addressing into one independent table without losing the text.
 address=[x for x in d.paragraphs if x.text.startswith(('Кому:','От:','Кому {{','Кому: {{'))]
 if address:
  t=d.add_table(rows=len(address),cols=1)
  for row,x in zip(t.rows,address):row.cells[0].text=x.text
  address[0]._p.addprevious(t._tbl)
  for x in address:x._p.getparent().remove(x._p)
 if p.name.startswith('43-'):
  x=next(x for x in d.paragraphs if x.text=='{{ДОЛЖНОСТЬ, ПОДПИСЬ, ФИО}}')
  t=d.add_table(rows=1,cols=1);t.cell(0,0).text='Подрядчик\nДолжность {{...}}    ФИО {{...}}\nПодпись ____________    Дата ____________'
  x._p.addprevious(t._tbl);x._p.getparent().remove(x._p)
 norm(d)
 for t in d.tables:
  n=len(t.columns);signature=all('Подпись' in c.text for c in t.rows[0].cells)
  address_table=t.cell(0,0).text.startswith(('Кому','От:'))
  widths=([4933,4933] if signature and n==2 else [650,3400,2700,3116] if n==4 and t.cell(0,0).text=='№' else [9866] if n==1 else None)
  if widths:
   for col,w in zip(t.columns,widths):col.width=Twips(w)
   for tr in t._tbl.tr_lst:
    for tc,w in zip(tr.tc_lst,widths):elem(tc.get_or_add_tcPr(),'w:tcW',{'w:type':'dxa','w:w':w})
  # Separate adjacent blocks with a real spacer paragraph.
  prev=t._tbl.getprevious()
  if prev is not None and prev.tag==qn('w:tbl'):
   from docx.oxml import OxmlElement
   spacer=OxmlElement('w:p');t._tbl.addprevious(spacer)
  if signature or address_table:
   for row in t.rows:
    for cell in row.cells:
     for x in cell.paragraphs:
      x.paragraph_format.space_before=Pt(3);x.paragraph_format.space_after=Pt(5)
 for x in d.paragraphs:
  if x.text and x.text.isupper() and len(x.text)>15 and not x.text.startswith('{{'):
   x.style='Title'
   from docx.shared import RGBColor
   for run in x.runs:run.font.name='Arial';run.font.size=Pt(14);run.font.bold=True;run.font.color.rgb=RGBColor(0,0,0)
   for node in [x._p.get_or_add_pPr(),d.styles['Title'].element.get_or_add_pPr()]:
    border=node.find(qn('w:pBdr'))
    if border is not None:node.remove(border)
   break
 d.save(O/p.name);changes.append({'name':p.name,'source_sha256':H(p),'sha256':H(O/p.name)})
# Keep the original official PDF as a reference and add the accepted editable working form.
a=R.parent/'qa15-p3/accepted-aosr.docx'
assert H(a)=='a0b0e8f48f7f0b8310a96358c226038a2066a17c159021d6f34f742b7969d7d7'
shutil.copyfile(a,O/'31A-rabochiy-akt-skrytyh-rabot.docx')
(I/'BUILD_RECEIPT.json').write_text(json.dumps({'sku':'p4','source_commit':'5361c80125107d9bb47d355bd5730f8b6e2da2c1','source_archive_sha256':H(R/'source.zip'),'changes':changes,'official_PDF_unchanged':True,'editable_AOSR_from_accepted_P2':True,'production_changed':False},ensure_ascii=False,indent=2))
print('DOCX',len(list(O.glob('*.docx'))))
