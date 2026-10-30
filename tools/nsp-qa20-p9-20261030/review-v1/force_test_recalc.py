from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
R=Path(__file__).resolve().parent;q=lambda n:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+n
for f in (R/'test-input').glob('*.xlsx'):
 with ZipFile(f)as z:parts={n:z.read(n)for n in z.namelist()}
 for n in list(parts):
  if n.startswith('xl/worksheets/sheet')and n.endswith('.xml'):
   r=E.fromstring(parts[n])
   for c in r.iter(q('c')):
    fo=c.find(q('f'))
    if fo is not None:
     for v in list(c.findall(q('v'))):c.remove(v)
   parts[n]=E.tostring(r,xml_declaration=True,encoding='UTF-8')
 w=E.fromstring(parts['xl/workbook.xml']);cp=w.find(q('calcPr'))
 if cp is None:cp=E.SubElement(w,q('calcPr'))
 cp.attrib.update({'calcMode':'auto','fullCalcOnLoad':'1','forceFullCalc':'1'});parts['xl/workbook.xml']=E.tostring(w,xml_declaration=True,encoding='UTF-8')
 with ZipFile(f,'w',ZIP_DEFLATED)as z:
  for n,b in parts.items():z.writestr(n,b)
profile=Path('/tmp/p9-force-recalc/user');profile.mkdir(parents=True,exist_ok=True)
(profile/'registrymodifications.xcu').write_text('''<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item></oor:items>''')
print('Removed all formula caches from disposable test inputs; forced recalculation profile')
