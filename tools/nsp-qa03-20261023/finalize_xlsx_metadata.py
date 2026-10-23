"""Print/hyperlink metadata only; no cell value/formula/style changes or protection."""
from pathlib import Path
import zipfile,io,json,hashlib,xml.etree.ElementTree as E
O=Path(__file__).resolve().parent;P=O/'candidate/02-reestr-uderzhaniy-po-obektu.xlsx'
N='http://schemas.openxmlformats.org/spreadsheetml/2006/main';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';PK='http://schemas.openxmlformats.org/package/2006/relationships'
E.register_namespace('',N);E.register_namespace('r',R);tag=lambda s:'{'+N+'}'+s
before=P.read_bytes();(O/'proof/pre-metadata.xlsx').write_bytes(before)
with zipfile.ZipFile(io.BytesIO(before))as z:parts={n:z.read(n)for n in z.namelist()};infos=z.infolist()
specs=[('Реестр удержаний','A1:I25',9),('Условия возврата','A1:M26',8)]
def payload(root):return {c.get('r'):E.tostring(c,encoding='unicode')for c in root.iter(tag('c'))}
for i,(name,area,paper)in enumerate(specs,1):
 path=f'xl/worksheets/sheet{i}.xml';root=E.fromstring(parts[path]);old=payload(root)
 assert root.find(tag('sheetProtection'))is None
 pr=root.find(tag('sheetPr'))
 if pr is None:pr=E.Element(tag('sheetPr'));root.insert(0,pr)
 ps=pr.find(tag('pageSetUpPr'))
 if ps is None:ps=E.SubElement(pr,tag('pageSetUpPr'))
 ps.set('fitToPage','1');ps.set('autoPageBreaks','0')
 for n in ['printOptions','pageMargins','pageSetup']:
  e=root.find(tag(n))
  if e is not None:root.remove(e)
 if i==2:
  hp=E.SubElement(root,tag('hyperlinks'));rels=E.Element('{'+PK+'}Relationships')
  for j,l in enumerate(json.loads((O/'proof/XLSX_HYPERLINKS.json').read_text()),1):
   ident='qa03link'+str(j);E.SubElement(hp,tag('hyperlink'),ref=l['cell'],attrib={'{'+R+'}id':ident})
   E.SubElement(rels,'{'+PK+'}Relationship',Id=ident,Type=R+'/hyperlink',Target=l['url'],TargetMode='External')
  parts[f'xl/worksheets/_rels/sheet{i}.xml.rels']=E.tostring(rels,encoding='utf-8',xml_declaration=True)
 E.SubElement(root,tag('printOptions'),horizontalCentered='1')
 E.SubElement(root,tag('pageMargins'),left='0.25',right='0.25',top='0.3',bottom='0.3',header='0.1',footer='0.1')
 E.SubElement(root,tag('pageSetup'),paperSize=str(paper),orientation='landscape',fitToWidth='1',fitToHeight='1')
 assert payload(root)==old
 parts[path]=E.tostring(root,encoding='utf-8',xml_declaration=True)
root=E.fromstring(parts['xl/workbook.xml']);names=root.find(tag('definedNames'))
if names is None:names=E.SubElement(root,tag('definedNames'))
for e in list(names):
 if e.get('name')in ['_xlnm.Print_Area','_xlnm.Print_Titles']:names.remove(e)
for i,(name,area,_)in enumerate(specs):
 addr=':'.join('$'+''.join(c for c in x if c.isalpha())+'$'+''.join(c for c in x if c.isdigit())for x in area.split(':'))
 E.SubElement(names,tag('definedName'),name='_xlnm.Print_Area',localSheetId=str(i)).text="'"+name+"'!"+addr
cp=root.find(tag('calcPr'))
if cp is None:cp=E.SubElement(root,tag('calcPr'))
cp.set('calcMode','auto');cp.set('fullCalcOnLoad','1');cp.set('forceFullCalc','1');parts['xl/workbook.xml']=E.tostring(root,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(P,'w',zipfile.ZIP_DEFLATED)as z:
 for info in infos:z.writestr(info,parts.pop(info.filename))
 for n,b in parts.items():z.writestr(n,b)
with zipfile.ZipFile(P)as z:
 assert z.testzip()is None
 for n in z.namelist():
  if n.endswith(('.xml','.rels')):E.fromstring(z.read(n))
sha=lambda b:hashlib.sha256(b).hexdigest()
(O/'proof/XLSX_METADATA_GATE.json').write_text(json.dumps(dict(status='PASS_METADATA_NATIVE_PENDING',before_sha256=sha(before),after_sha256=sha(P.read_bytes()),cell_payloads_unchanged=True,protection='none; matches source editing model',sheets=specs,print_area_recognition='verify actual native output'),ensure_ascii=False,indent=2)+'\n')
for p in(O/'candidate').glob('*.ndjson'):p.unlink()
print(sha(P.read_bytes()))
