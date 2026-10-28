"""Conservative formula-cell dependency scan; ROW/ROWS/COLUMN/COLUMNS address-only calls excluded."""
from pathlib import Path
from zipfile import ZipFile
import re,json,hashlib,xml.etree.ElementTree as E
H=Path(__file__).resolve().parents[1];NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def col(a):
 n=0
 for x in re.match('[A-Z]+',a)[0]:n=n*26+ord(x)-64
 return n
def letter(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(k+65)+s
 return s
records=[]
for rec in json.loads((H/'new-workbook-manifest.json').read_text()):
 p=H/'candidates'/rec['path'];b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==rec['sha256'];formulas={}
 with ZipFile(p)as z:
  names=[x.get('name')for x in E.fromstring(z.read('xl/workbook.xml')).find('s:sheets',NS)]
  for i,name in enumerate(names):
   for c in E.fromstring(z.read('xl/worksheets/sheet%d.xml'%(i+1))).findall('.//s:sheetData/s:row/s:c',NS):
    f=c.findtext('s:f',namespaces=NS)
    if f is not None:formulas[(name,c.get('r'))]=f
 edges={k:set()for k in formulas};dynamic=[]
 pat=r"(?:(?:'((?:[^']|'')+)'|([\w]+))!)?(\$?[A-Z]{1,3}\$?\d+)(?::(\$?[A-Z]{1,3}\$?\d+))?"
 for key,f in formulas.items():
  f=re.sub(r'"(?:[^"]|"")*"','""',f);f=re.sub(r'\b(?:ROWS|COLUMNS|ROW|COLUMN)\([^()]*\)','0',f,flags=re.I)
  if re.search(r'\b(?:INDIRECT|OFFSET)\(',f,re.I):dynamic.append(key)
  for match in re.finditer(pat,f):
   s=(match[1]or match[2]or key[0]).replace("''", "'");start=match[3].replace('$','');end=(match[4]or start).replace('$','');r1=int(re.search('[0-9]+',start)[0]);r2=int(re.search('[0-9]+',end)[0]);c1=col(start);c2=col(end)
   for r in range(r1,r2+1):
    for c in range(c1,c2+1):
     ref=(s,letter(c)+str(r))
     if ref in formulas:edges[key].add(ref)
 state={};cycles=[]
 def visit(v,stack):
  if state.get(v)==1:cycles.append(stack[stack.index(v):]+[v]);return
  if state.get(v)==2:return
  state[v]=1
  for n in edges[v]:visit(n,stack+[v])
  state[v]=2
 for v in edges:visit(v,[])
 assert not cycles,(rec['path'],cycles[:3]);assert not dynamic,(rec['path'],'DYNAMIC_REFERENCE_REQUIRES_NATIVE_REVIEW',dynamic)
 records.append({'path':rec['path'],'sha256':rec['sha256'],'formula_cells':len(formulas),'formula_to_formula_edges':sum(map(len,edges.values())),'cycles':0,'dynamic_reference_functions':0,'scope':'cell/range value dependencies; address-only ROW/ROWS/COLUMN/COLUMNS excluded; not native Excel'})
(H/'DEPENDENCY_SCAN.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));print('DEPENDENCIES_PASS',len(records),'books; 0 cycles; no INDIRECT/OFFSET')
