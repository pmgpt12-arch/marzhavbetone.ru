from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree as E
import json,hashlib,re
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};n='{'+ns['s']+'}'
manifest=json.loads((Q/'new-workbook-manifest.json').read_text());rows=[]
def colnum(a):
 v=0
 for c in re.match('[A-Z]+',a)[0]:v=v*26+ord(c)-64
 return v
def colname(v):
 s=''
 while v:v,m=divmod(v-1,26);s=chr(m+65)+s
 return s
for rec in manifest:
 if not rec['path'].endswith('/22-reestr-garantiynyh-uderzhaniy.xlsx'):continue
 p=Q/'candidates'/rec['path'];raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==rec['sha256']
 with ZipFile(p)as z:infos=[deepcopy(i)for i in z.infolist()];parts={i.filename:z.read(i.filename)for i in infos}
 wb=E.fromstring(parts['xl/workbook.xml']);dn=wb.find('s:definedNames',ns)
 if dn is not None:raise AssertionError('Print areas already present: inspect instead of overwrite')
 dn=E.Element(n+'definedNames');cp=wb.find('s:calcPr',ns);wb.insert(wb.index(cp),dn)
 with ZipFile(R/rec['path'])as z:
  for i,s in enumerate(wb.findall('s:sheets/s:sheet',ns)):
   root=E.fromstring(z.read('xl/worksheets/sheet'+str(i+1)+'.xml'));cells=root.findall('s:sheetData/s:row/s:c',ns);mc=max(colnum(c.get('r'))for c in cells);mr=max(int(re.search('[0-9]+',c.get('r'))[0])for c in cells)
   area="'"+s.get('name').replace("'","''")+"'!$A$1:$"+colname(mc)+'$'+str(mr);E.SubElement(dn,n+'definedName',name='_xlnm.Print_Area',localSheetId=str(i)).text=area;rows.append({'sheet':s.get('name'),'area':area,'basis':'original cell bounds; excludes new helper O; no page setup or margins altered'})
 parts['xl/workbook.xml']=E.tostring(wb,encoding='utf-8',xml_declaration=True)
 with ZipFile(p,'w')as out:
  for i in infos:out.writestr(i,parts[i.filename])
 rec['pre_print_scope_sha256']=rec['sha256'];rec['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();rec['git_blob']=hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()).hexdigest();rec['print_scope']='Explicit original bounds on all three sheets; helper O excluded; existing page setup preserved'
(Q/'new-workbook-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(Q/'HELPER_PRINT_SCOPE.json').write_text(json.dumps({'P5_added_print_areas':rows,'T2':'existing area A1:I136 excludes new J','P13':'existing area A1:J56 excludes new K'},ensure_ascii=False,indent=2));print('PRINT_SCOPE',rows)
