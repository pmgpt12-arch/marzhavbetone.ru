"""Nominate only the exact six-file candidate with preserved workbook behaviour."""
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from io import BytesIO
from lxml import etree as E
import json,hashlib,subprocess,re

P=Path(__file__).resolve().parent
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
sheetnames=['Опись','Как заполнять','Виды','Пример заполнения']
src=ZipFile(P/'T2-peredacha-ID-6-files-business-R1.zip')
name='03-opis-peredavaemogo-komplekta.xlsx'
old=ZipFile(BytesIO(src.read(name))); new=ZipFile(P/'final-files'/name)
edits=json.loads((P/'r2-excel-text-edits.json').read_text())
edits['Опись']['A2']=json.loads((P/'r2-a2-authored-text.json').read_text())['value']
canon=lambda x:E.tostring(x,method='c14n') if x is not None else None
sig=lambda x:(x.tag,tuple(sorted(x.attrib.items())),x.text or '',tuple(sig(y) for y in x))
assert old.namelist()==new.namelist()
changed=[n for n in old.namelist() if old.read(n)!=new.read(n)]
assert set(changed)=={'xl/workbook.xml','xl/styles.xml','xl/comments/comment1.xml',*[f'xl/worksheets/sheet{i}.xml' for i in range(1,5)]}
formulas={}; beforeformulas={}; textchanges=[]
allowedstyles={1:{'D133','B135','G135'},2:{'A4','A5','A6','A7','A8','A9','A12','A13','A14','A15'},3:set(),4:set()}
for i,sh in enumerate(sheetnames,1):
 part=f'xl/worksheets/sheet{i}.xml'; a=E.fromstring(old.read(part));b=E.fromstring(new.read(part))
 ca={c.get('r'):c for c in a.findall('.//s:sheetData/s:row/s:c',ns)}
 cb={c.get('r'):c for c in b.findall('.//s:sheetData/s:row/s:c',ns)}
 assert ca.keys()==cb.keys()
 for address,c in ca.items():
  d=cb[address]; beforeformulas[(sh,address)]=canon(c.find('s:f',ns));formulas[(sh,address)]=canon(d.find('s:f',ns))
  if address in edits[sh]:
   assert ''.join(d.find('s:is',ns).itertext())==edits[sh][address]
   assert c.attrib==d.attrib
   textchanges.append([sh,address])
  else:
   cc=E.fromstring(E.tostring(c));dd=E.fromstring(E.tostring(d))
   if address in allowedstyles[i]: cc.attrib.pop('s',None);dd.attrib.pop('s',None)
   assert sig(cc)==sig(dd),(sh,address,'unapproved value/formula/style change')
 for feature in ('conditionalFormatting','dataValidations','mergeCells','sheetViews','sheetFormatPr','legacyDrawing'):
  assert [sig(x) for x in a.findall('s:'+feature,ns)]==[sig(x) for x in b.findall('s:'+feature,ns)],(sh,feature)
 assert sig(a.find('s:sheetPr/s:outlinePr',ns))==sig(b.find('s:sheetPr/s:outlinePr',ns))
assert formulas==beforeformulas
formula_count=sum(x is not None for x in formulas.values());assert formula_count==124
# Original style definitions remain; added variants affect only approved cells.
sa=E.fromstring(old.read('xl/styles.xml'));sb=E.fromstring(new.read('xl/styles.xml'))
for a,b in zip(sa,sb):
 assert a.tag==b.tag
 if a.tag.endswith('}cellXfs'):
  assert len(b)>=len(a) and [sig(x) for x in a]==[sig(x) for x in b[:len(a)]]
 else: assert sig(a)==sig(b),a.tag
# Notes retain every anchor and author. Three instruction texts changed.
aa=E.fromstring(old.read('xl/comments/comment1.xml'));bb=E.fromstring(new.read('xl/comments/comment1.xml'))
assert sig(aa[0])==sig(bb[0]);assert [x.attrib for x in aa[1]]==[x.attrib for x in bb[1]]
assert len(aa[1])==len(bb[1])==8
for a,b in zip(aa[1],bb[1]):
 if a.get('ref') not in ('A10','E10','H10'): assert sig(a)==sig(b)

files=sorted((P/'final-files').iterdir()); assert len(files)==6 and {p.name for p in files}==set(src.namelist())
for p in files:
 if p.suffix!='.xlsx': assert p.read_bytes()==(P/'r2-files'/p.name).read_bytes()
target=P/'T2-peredacha-ID-6-files-business-R2.zip'
with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:
  info=ZipInfo(p.name,(2026,10,17,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o100644<<16
  z.writestr(info,p.read_bytes())
with ZipFile(target) as z:
 assert z.testzip() is None
 for p in files:assert z.read(p.name)==p.read_bytes()
gate=subprocess.run(['python3',str(P.parents[1]/'editorial_business_style_gate.py'),str(target)],capture_output=True,text=True,timeout=30)
assert gate.returncode==0,(gate.stdout,gate.stderr)
print(gate.stdout.strip())
manifest={'status':'T2_R2_READY_FOR_OWNER_REVIEW_NOT_RELEASED','product_title':'Система документального подтверждения передачи исполнительной документации','target_price_rub':9900,'source_commit':'530f615','source_R1_sha256':hashlib.sha256((P/'T2-peredacha-ID-6-files-business-R1.zip').read_bytes()).hexdigest(),'buyer_file_count':6,'zip_name':target.name,'zip_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'zip_bytes':target.stat().st_size,'buyer_files':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files],'changed_from_previous_draft':[name],'checks':{'crc':'PASS','exact_member_names':'PASS','editorial_automated':gate.stdout.strip(),'editorial_semantic':'PASS: instructions, examples, notes and cross-document references reviewed','formula_count':formula_count,'formula_text_and_cached_values':'IDENTICAL_TO_R1','other_values':'IDENTICAL except 22 authorized text cells (including A2) and three note texts','validations_conditional_formatting_merges_views':'IDENTICAL_TO_R1','styles':'Existing definitions retained; scoped wrapping variants appended','print':'EVIDENCE_REQUIRED','native_formula_scenarios':'EVIDENCE_REQUIRED','word_pdf':'Reused unchanged SHA and previous successful render: PDF 1 page; DOCX 3/1/1/5 pages'},'owner_review_required':True,'published':False,'release_scope':'No storefront, checkout, production or accepted primary product changes','main_product_counter':'3/13 unchanged; T2 is separate SKU'}
(P/'r2-final-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'zip':target.name,'sha256':manifest['zip_sha256'],'xlsx_sha256':next(x['sha256'] for x in manifest['buyer_files'] if x['name']==name),'text_cells':len(textchanges),'formula_count':formula_count},ensure_ascii=False))
