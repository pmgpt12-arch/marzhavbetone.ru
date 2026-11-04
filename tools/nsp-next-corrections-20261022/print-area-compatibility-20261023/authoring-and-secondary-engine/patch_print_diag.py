from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import hashlib,json,base64
p=Path('/tmp/nsp-avans-20261023/print-diagnostic');ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main';q=lambda n:'{'+ns+'}'+n
out=[]
for tag,name in [('latin','PrintTest'),('cyrillic','Печать')]:
 with ZipFile(p/(tag+'-base.xlsx')) as z: parts={n:z.read(n)for n in z.namelist()}
 w=E.fromstring(parts['xl/workbook.xml']);old=w.find(q('definedNames'))
 if old is not None:w.remove(old)
 dn=E.Element(q('definedNames'))
 for key,ref in [('Print_Area',"'"+name+"'!$A$1:$A$3"),('Print_Titles',"'"+name+"'!$1:$1")]:E.SubElement(dn,q('definedName'),name='_xlnm.'+key,localSheetId='0').text=ref
 sheets=w.find(q('sheets'));w.insert(list(w).index(sheets)+1,dn);parts['xl/workbook.xml']=E.tostring(w,xml_declaration=True,encoding='utf-8')
 s=E.fromstring(parts['xl/worksheets/sheet1.xml']);sd=s.find(q('sheetData'));E.SubElement(s,q('sheetProtection'),sheet='1',objects='1',scenarios='1')
 # Put protection immediately after sheetData, per worksheet schema order.
 sp=s.find(q('sheetProtection'));s.remove(sp);s.insert(list(s).index(sd)+1,sp)
 parts['xl/worksheets/sheet1.xml']=E.tostring(s,xml_declaration=True,encoding='utf-8')
 f=p/(tag+'.xlsx')
 with ZipFile(f,'w',ZIP_DEFLATED)as z:
  for n,b in parts.items():z.writestr(n,b)
 out.append({'name':f.name,'sheet':name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'base64':base64.b64encode(f.read_bytes()).decode()})
(p/'transfer.json').write_text(json.dumps(out,ensure_ascii=False))
print(json.dumps([{k:v for k,v in a.items()if k!='base64'}for a in out],ensure_ascii=False))
