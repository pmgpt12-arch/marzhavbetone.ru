from pathlib import Path
from lxml import etree as E
from copy import deepcopy
import zipfile,json
R=Path(__file__).resolve().parent;ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main';q=lambda n:'{'+ns+'}'+n
src=next((R/'source').glob('09*'));raw=next((R.parent/'outputs/p8-20261030').glob('09*'))
with zipfile.ZipFile(src)as z:original={n:z.read(n)for n in z.namelist()}
with zipfile.ZipFile(raw)as z:parts={n:z.read(n)for n in z.namelist()}
w=E.fromstring(parts['xl/workbook.xml']);sw=E.fromstring(original['xl/workbook.xml'])
defs=w.find(q('definedNames'))
if defs is not None:w.remove(defs)
defs=deepcopy(sw.find(q('definedNames')))
calc=w.find(q('calcPr'));w.insert(list(w).index(calc)if calc is not None else len(w),defs)
if calc is None:calc=E.SubElement(w,q('calcPr'))
calc.attrib.update({'calcMode':'auto','fullCalcOnLoad':'1','forceFullCalc':'1'})
for i in range(1,8):
 name='xl/worksheets/sheet'+str(i)+'.xml';s=E.fromstring(parts[name]);ss=E.fromstring(original[name])
 for tag in ['sheetPr','printOptions','pageMargins','pageSetup','headerFooter','rowBreaks','colBreaks']:
  old=s.find(q(tag));replacement=ss.find(q(tag))
  if old is not None:s.remove(old)
  if replacement is not None:
   if tag=='sheetPr':s.insert(0,deepcopy(replacement))
   else:s.append(deepcopy(replacement))
 parts[name]=E.tostring(s,xml_declaration=True,encoding='UTF-8',standalone=True)
parts['xl/workbook.xml']=E.tostring(w,xml_declaration=True,encoding='UTF-8',standalone=True)
out=R/'candidate'/src.name
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in parts.items():z.writestr(n,b)
(R/'internal/PRINT_RECOVERY.json').write_text(json.dumps({'cause':'Artifact Tool roundtrip omitted source print areas, titles and fitToPage metadata','class':'spreadsheet serialization metadata loss','rule':'restore exact source print metadata after Artifact Tool narrow edits; preserve formulas and values','gate':'semantic comparison and LibreOffice PDF all-sheet review','fallback':'same unavailable print API established QA17/QA18'},ensure_ascii=False,indent=2))
print('Restored source print metadata on all seven sheets')
