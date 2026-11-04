from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree as E
import json,hashlib,re
q=Path(__file__).resolve().parents[1];manifest=json.loads((q/'new-workbook-manifest.json').read_text());ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};n='{'+ns['s']+'}'
def colnum(a):
 v=0
 for c in re.match('[A-Z]+',a)[0]:v=v*26+ord(c)-64
 return v
def colname(v):
 s=''
 while v:v,m=divmod(v-1,26);s=chr(m+65)+s
 return s
for rec in manifest:
 p=q/'candidates'/rec['path'];raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==rec['sha256'];parts={}
 with ZipFile(p)as z:
  infos=[deepcopy(i)for i in z.infolist()];parts={i.filename:z.read(i.filename)for i in infos}
 wb=E.fromstring(parts['xl/workbook.xml']);cp=wb.find('s:calcPr',ns)
 if cp is None:cp=E.SubElement(wb,n+'calcPr')
 cp.set('calcMode','auto');cp.set('fullCalcOnLoad','1');cp.set('forceFullCalc','1');parts['xl/workbook.xml']=E.tostring(wb,encoding='utf-8',xml_declaration=True)
 for part in rec['changed_parts']:
  r=E.fromstring(parts[part]);dim=r.find('s:dimension',ns)
  if dim is not None:
   cells=r.findall('s:sheetData/s:row/s:c',ns);maxcol=max(colnum(c.get('r'))for c in cells);maxrow=max(int(re.search('[0-9]+',c.get('r'))[0])for c in cells);dim.set('ref','A1:'+colname(maxcol)+str(maxrow));parts[part]=E.tostring(r,encoding='utf-8',xml_declaration=True)
 with ZipFile(p,'w')as out:
  for i in infos:out.writestr(i,parts[i.filename])
 rec['pre_calc_contract_sha256']=rec['sha256'];rec['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();rec['git_blob']=hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()).hexdigest();rec['changed_parts'].append('xl/workbook.xml');rec['calc_contract']='automatic full recalc on open; no formula cache used as acceptance'
(q/'new-workbook-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('RECALC_CONTRACT',len(manifest))

