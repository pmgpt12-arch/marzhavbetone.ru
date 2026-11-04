from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import json,base64,hashlib,io
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');src=Q/'print-area-default-ns-20261023/inputs/nsp-print-area-default-ns-v1-20261023/latin.xlsx';out=[];ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
for tag,area,titles in [('bare-en','Print_Area','Print_Titles'),('reserved-ru','_xlnm.Область_печати','_xlnm.Печатать_заголовки'),('bare-ru','Область_печати','Печатать_заголовки')]:
 with ZipFile(src)as z:parts={n:z.read(n)for n in z.namelist()}
 w=E.fromstring(parts['xl/workbook.xml']);d=w.find('{'+ns+'}definedNames');assert len(d)==2
 d[0].set('name',area);d[1].set('name',titles);parts['xl/workbook.xml']=E.tostring(w,encoding='utf-8',xml_declaration=True)
 mem=io.BytesIO()
 with ZipFile(mem,'w',ZIP_DEFLATED)as z:
  for n,v in parts.items():z.writestr(n,v)
 data=mem.getvalue();out.append({'name':tag+'.xlsx','sheet':'PrintTest','sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()})
(Q/'print-diagnostic-name-matrix-transfer.json').write_text(json.dumps(out,ensure_ascii=False))
old=(Q/'scripts/run_print_diagnostic.py').read_text();new=old.replace("D=Q/'print-area-diagnostic-20261023'","D=Q/'print-area-name-matrix-20261023'").replace("jid='nsp-print-area-diagnostic-v1-20261023'","jid='nsp-print-area-name-matrix-v1-20261023'").replace("Q/'print-diagnostic-transfer.json'","Q/'print-diagnostic-name-matrix-transfer.json'")
new=new.replace("assert names[0].get('name')=='_xlnm.Print_Area'and names[0].get('localSheetId')=='0'and","assert names[0].get('localSheetId')=='0'and")
new=new.replace('for i in [1,2]:','for i in [1,2,3]:');assert new!=old
(Q/'scripts/run_print_name_matrix.py').write_text(new)
print('PREPARED_DIAGNOSTIC_NAME_VARIANTS_ONLY',[(x['name'],x['sha256'])for x in out])
