from pathlib import Path
from lxml import etree as E
import zipfile,json
R=Path(__file__).resolve().parent
src=R.parent/'outputs/qa16-p4/38-reestr-id.xlsx';dst=R/'candidate/38-reestr-id.xlsx'
ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main';q=lambda n:'{'+ns+'}'+n
with zipfile.ZipFile(src) as z:entries={n:z.read(n) for n in z.namelist()}
w=E.fromstring(entries['xl/workbook.xml']);dn=w.find(q('definedNames'))
if dn is None:
 dn=E.Element(q('definedNames'));calc=w.find(q('calcPr'));w.insert(list(w).index(calc) if calc is not None else len(w),dn)
for name,text in [('_xlnm.Print_Area',"'Реестр'!$A$3:$Q$103"),('_xlnm.Print_Titles',"'Реестр'!$3:$3,'Реестр'!$A:$C")]:
 for x in list(dn):
  if x.get('name')==name and x.get('localSheetId')=='0':dn.remove(x)
 E.SubElement(dn,q('definedName'),name=name,localSheetId='0').text=text
entries['xl/workbook.xml']=E.tostring(w,xml_declaration=True,encoding='UTF-8',standalone=True)
s=E.fromstring(entries['xl/worksheets/sheet1.xml']);p=s.find(q('sheetPr'))
if p is None:p=E.Element(q('sheetPr'));s.insert(0,p)
t=p.find(q('pageSetUpPr'))
if t is None:t=E.SubElement(p,q('pageSetUpPr'))
t.set('fitToPage','1');p=s.find(q('pageSetup'))
if p is None:p=E.SubElement(s,q('pageSetup'))
for k,v in dict(orientation='landscape',paperSize='9',fitToWidth='2',fitToHeight='0').items():p.set(k,v)
hf=s.find(q('headerFooter'))
if hf is None:hf=E.SubElement(s,q('headerFooter'))
hd=hf.find(q('oddHeader'))
if hd is None:hd=E.SubElement(hf,q('oddHeader'))
hd.text='&C&10Реестр исполнительной документации'
ft=hf.find(q('oddFooter'))
if ft is None:ft=E.SubElement(hf,q('oddFooter'))
ft.text='&RСтраница &P из &N'
entries['xl/worksheets/sheet1.xml']=E.tostring(s,xml_declaration=True,encoding='UTF-8',standalone=True)
with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in entries.items():z.writestr(n,b)
(R/'internal/PRINT_METADATA_PATCH.json').write_text(json.dumps({'reason':'Documented Artifact Tool print surface unavailable after two bounded lookups','scope':'OOXML print metadata only; content authored with Artifact Tool','area':'A3:Q103','repeat':'row 3 and columns A:C','fit_width_pages':2,'title':'page header avoids clipping merged screen title on second horizontal panel'},indent=2))
