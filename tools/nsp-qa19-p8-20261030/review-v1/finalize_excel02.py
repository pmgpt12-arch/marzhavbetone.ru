from pathlib import Path
from lxml import etree as E
from copy import deepcopy
import zipfile
R=Path(__file__).resolve().parent;q=lambda n:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+n
src=next((R/'source').glob('02*'));raw=R.parent/'outputs/p8-20261030'/src.name
with zipfile.ZipFile(src)as z:original={n:z.read(n)for n in z.namelist()}
with zipfile.ZipFile(raw)as z:parts={n:z.read(n)for n in z.namelist()}
w=E.fromstring(parts['xl/workbook.xml']);sw=E.fromstring(original['xl/workbook.xml']);old=w.find(q('definedNames'))
if old is not None:w.remove(old)
w.append(deepcopy(sw.find(q('definedNames'))));parts['xl/workbook.xml']=E.tostring(w,xml_declaration=True,encoding='UTF-8')
for i in range(1,8):
 n='xl/worksheets/sheet'+str(i)+'.xml';s=E.fromstring(parts[n]);ss=E.fromstring(original[n])
 for tag in ['sheetPr','printOptions','pageMargins','pageSetup','headerFooter','rowBreaks','colBreaks']:
  old=s.find(q(tag));el=ss.find(q(tag))
  if old is not None:s.remove(old)
  if el is not None:
   if tag=='sheetPr':s.insert(0,deepcopy(el))
   else:s.append(deepcopy(el))
 if i in [3,4]:s.find(q('pageSetup')).set('paperSize','8') # A3 for sixteen-column cash profiles
 if i==5:
  s.find(q('pageMargins')).attrib.update({'top':'0.35','bottom':'0.35'})
 parts[n]=E.tostring(s,xml_declaration=True,encoding='UTF-8')
with zipfile.ZipFile(R/'candidate'/src.name,'w',zipfile.ZIP_DEFLATED)as z:
 for n,b in parts.items():z.writestr(n,b)
print('02 source print settings restored, A3 profiles, summary margins')
