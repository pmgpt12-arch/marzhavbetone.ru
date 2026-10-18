#!/usr/bin/env python3
"""Targeted language/layout remediation; published forms bypass restyling."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,ZipInfo
from lxml import etree as E
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_ROW_HEIGHT_RULE
import json, shutil, hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'tools/candidates/remaining-batch-r3-20261018'
INPUT=Path('/tmp/mb-r3/input');OUT=Path('/tmp/mb-r3/work')
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
edits=json.loads((BASE/'text-edits.json').read_text())
OFFICIAL={('P1','01-ks-2.xls'):'KS-2-original.xls',('P1','02-ks-3.xls'):'KS-3-original.xls',('P2','04-akt-skrytyh-rabot.docx'):'AOSR-published.docx',('P4','31-akt-osvidetelstvovaniya-skrytyh-rabot.docx'):'AOSR-published.docx'}
if OUT.exists():shutil.rmtree(OUT)
shutil.copytree(INPUT,OUT)
for sku,filename in [('P1','01-ks-2.docx'),('P1','02-ks-3.docx')]:(OUT/sku/filename).unlink()
for (sku,filename),source in OFFICIAL.items():shutil.copyfile(BASE/'sources'/source,OUT/sku/filename)
for sku in sorted(p.name for p in OUT.iterdir()):
 for f in sorted((OUT/sku).iterdir()):
  selected=[e for e in edits if e['sku']==sku and e['file']==f.name]
  if (sku,f.name) in OFFICIAL:continue
  if f.suffix=='.docx':
   with ZipFile(f) as z:parts={n:z.read(n) for n in z.namelist()}
   for part in {e['loc'].split(':p')[0] for e in selected}:
    r=E.fromstring(parts[part]);paras=r.xpath('//w:p',namespaces=NS)
    for edit in [e for e in selected if e['loc'].startswith(part+':p')]:
     p=paras[int(edit['loc'].split(':p')[1])];texts=p.xpath('.//w:t',namespaces=NS)
     old=''.join(t.text or '' for t in texts);assert old==edit['old'],(sku,f.name,edit['loc'],old)
     texts[0].text=edit['new']
     for t in texts[1:]:t.text=''
    parts[part]=E.tostring(r,encoding='utf-8',xml_declaration=True,standalone=True)
   # Filename references follow the immutable original form format.
   if sku=='P1':
    for n in list(parts):
     if n.startswith('word/') and n.endswith('.xml'):
      parts[n]=parts[n].replace(b'01-ks-2.docx',b'01-ks-2.xls').replace(b'02-ks-3.docx',b'02-ks-3.xls')
   if selected or sku=='P1':
    with ZipFile(f,'w',ZIP_DEFLATED) as z:
     for n,b in parts.items():z.writestr(n,b)
   d=Document(f);changed=False
   for t in d.tables:
    # Fixed widths are kept inside the physical text area in both Word and LO.
    sec=d.sections[0];available=int(sec.page_width-sec.left_margin-sec.right_margin)
    total=sum(int(c.width or 0) for c in t.columns)
    if total>available+10000:
     factor=available/total
     for c in t.columns:c.width=int(c.width*factor)
     for row in t.rows:
      for c in row.cells:
       if c.width:c.width=int(c.width*factor)
     t.autofit=False;changed=True
    for row in t.rows:
     if row.height_rule==WD_ROW_HEIGHT_RULE.EXACTLY:row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST;changed=True
     if row._tr.trPr is None or row._tr.trPr.find(qn('w:cantSplit')) is None:
      row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'));changed=True
   if changed:d.save(f)
   if changed or selected or sku=='P1':
    with ZipFile(f) as z:canonical={n:z.read(n) for n in z.namelist()}
    with ZipFile(f,'w',ZIP_DEFLATED) as z:
     for n,b in sorted(canonical.items()):
      info=ZipInfo(n,(2026,10,18,0,0,0));info.compress_type=ZIP_DEFLATED
      z.writestr(info,b)
  elif f.suffix=='.txt':
   s=f.read_text()
   for e in selected:
    assert e['old'] in s,(sku,f.name,e['old']);s=s.replace(e['old'],e['new'])
   if sku=='P1':s=s.replace('01-ks-2.docx','01-ks-2.xls').replace('02-ks-3.docx','02-ks-3.xls')
   if 'СОСТАВ АРХИВА' in s:s=s.split('СОСТАВ АРХИВА',1)[0]+'СОСТАВ АРХИВА\n'+'\n'.join(sorted(p.name for p in (OUT/sku).iterdir() if p.is_file()))+'\n'
   f.write_text(s)
  elif f.suffix=='.xlsx':
   # Each value edit is authored through the documented Artifact Tool API.
   with ZipFile(f) as z:
    w=E.fromstring(z.read('xl/workbook.xml'));xn={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    names=[s.get('name') for s in w.findall('x:sheets/x:sheet',xn)]
   patch=[]
   for e in selected:
    part,cell=e['loc'].split(':');idx=int(part.rsplit('sheet',1)[1].split('.')[0])-1
    patch.append({'sheet':names[idx],'cell':cell,'text':e['new'],'part':part,'old':e['old']})
   p=Path('/tmp/mb-r3/patches')/sku;p.mkdir(parents=True,exist_ok=True)
   (p/(f.stem+'.json')).write_text(json.dumps(patch,ensure_ascii=False,indent=2))
sources=[{'sku':sku,'member':name,'source':source,'sha256':hashlib.sha256((BASE/'sources'/source).read_bytes()).hexdigest()} for (sku,name),source in OFFICIAL.items()]
(BASE/'original-form-lock.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
print('PREPARED',sum(1 for p in OUT.rglob('*') if p.is_file()),'files')
