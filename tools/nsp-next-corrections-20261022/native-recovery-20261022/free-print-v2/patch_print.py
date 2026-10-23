from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import hashlib,json
P=Path(__file__).resolve().parent;O=P/'print-v2';O.mkdir(exist_ok=True)
N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}';ns={'s':N[1:-1]}
sha=lambda b:hashlib.sha256(b).hexdigest();records=[]
for name,area in [('04-reestr-doprabot.xlsx','$A$1:$J$5'),('02-reestr-prilozheniy.xlsx','$A$1:$G$7')]:
 src=P/name;dest=O/name
 with ZipFile(src)as z:
  wb=E.fromstring(z.read('xl/workbook.xml'));ws=E.fromstring(z.read('xl/worksheets/sheet1.xml'));before=deepcopy(ws);before_wb=deepcopy(wb)
  sheet=wb.find('s:sheets',ns)[0].get('name');assert len(wb.find('s:sheets',ns))==1
  assert ws.find(N+'pageSetup')is None
  sp=ws.find(N+'sheetPr');assert sp is not None
  ps=sp.find(N+'pageSetUpPr');assert ps is not None;ps.set('fitToPage','1')
  margins=ws.find(N+'pageMargins');assert margins is not None
  margins.attrib.update({'left':'0.35','right':'0.35','top':'0.4','bottom':'0.4','header':'0.2','footer':'0.2'})
  setup=E.Element(N+'pageSetup',paperSize='9',orientation='landscape',fitToWidth='1',fitToHeight='0')
  ws.insert(list(ws).index(margins)+1,setup)
  names=wb.find(N+'definedNames');assert names is not None and len(names)==0
  E.SubElement(names,N+'definedName',name='_xlnm.Print_Area',localSheetId='0').text="'"+sheet.replace("'","''")+"'!"+area
  # Removing only native printing metadata must recover identical XML content.
  clean=deepcopy(ws);clean.remove(clean.find(N+'pageSetup'));clean.find(N+'sheetPr').find(N+'pageSetUpPr').attrib.clear();bpr=before.find(N+'sheetPr').find(N+'pageSetUpPr');clean.find(N+'sheetPr').find(N+'pageSetUpPr').attrib.update(bpr.attrib);clean.replace(clean.find(N+'pageMargins'),deepcopy(before.find(N+'pageMargins')))
  assert E.tostring(clean,method='c14n')==E.tostring(before,method='c14n')
  cleanwb=deepcopy(wb);cleanwb.find(N+'definedNames').clear();assert E.tostring(cleanwb,method='c14n')==E.tostring(before_wb,method='c14n')
  updates={'xl/workbook.xml':E.tostring(wb,encoding='utf-8',xml_declaration=True),'xl/worksheets/sheet1.xml':E.tostring(ws,encoding='utf-8',xml_declaration=True)}
  with ZipFile(dest,'w',ZIP_DEFLATED)as out:
   for info in z.infolist():out.writestr(deepcopy(info),updates.get(info.filename,z.read(info.filename)))
  with ZipFile(dest)as out:
   assert out.testzip()is None
   for n in z.namelist():
    if n not in updates:assert out.read(n)==z.read(n)
    if n.endswith(('.xml','.rels')):E.fromstring(out.read(n))
  records.append({'file':name,'source_sha256':sha(src.read_bytes()),'new_sha256':sha(dest.read_bytes()),'sheet':sheet,'area':area,'change':'A4 landscape, 1 page wide, native print area and margins only','cell_formula_style_and_validation_xml_unchanged':True,'other_zip_parts_byte_exact':True,'status':'PRINT_V2_CANDIDATE_NATIVE_QA_PENDING','tool_limitation':'Documented Artifact Tool API has no print/pageSetup surface; native OOXML-only metadata patch preserves all preaccepted cell bytes'})
 (O/'PRINT_PATCH_MANIFEST.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print(json.dumps(records,ensure_ascii=False))
