from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json
R=Path(__file__).resolve().parent
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def get(f):
 with ZipFile(f) as z:
  ss=[]
  if 'xl/sharedStrings.xml'in z.namelist():ss=[''.join(i.itertext()) for i in E.fromstring(z.read('xl/sharedStrings.xml'))]
  out={}
  for n in z.namelist():
   if n.startswith('xl/worksheets/sheet')and n.endswith('.xml'):
    r=E.fromstring(z.read(n));cells={}
    for c in r.xpath('//s:c',namespaces=ns):
     fo=c.find('s:f',ns);v=c.find('s:v',ns);i=c.find('s:is',ns)
     val=('F',fo.text)if fo is not None else('V',''.join(i.itertext())if i is not None else ss[int(v.text)]if c.get('t')=='s'and v is not None else v.text if v is not None else '')
     if val[1]:cells[c.get('r')]=val
    out[n]={'cells':cells,'merges':sorted(x for x in r.xpath('//s:mergeCell/@ref',namespaces=ns) if ':' in x and x.split(':')[0]!=x.split(':')[1]),'validations':sorted((x.get('sqref'),x.get('type'),str(x.xpath('s:formula1/text()',namespaces=ns)))for x in r.xpath('//s:dataValidation',namespaces=ns))}
  return out
f=next((R/'source').glob('09*'));a=get(f);b=get(R/'candidate'/f.name);diff=[]
for n in a:
 assert a[n]['merges']==b[n]['merges'],('merge changed',n)
 assert a[n]['validations']==b[n]['validations'],('validation changed',n)
 for k in set(a[n]['cells'])|set(b[n]['cells']):
  if a[n]['cells'].get(k)!=b[n]['cells'].get(k):diff.append((n,k,a[n]['cells'].get(k),b[n]['cells'].get(k)))
assert len(diff)==11,len(diff)
assert all(x[2][0]=='V' and x[3][0]=='V' for x in diff),'Formula changes outside scope'
(R/'internal/EXCEL_SCOPE_DIFF.json').write_text(json.dumps(diff,ensure_ascii=False,indent=1))
print('PASS: 11 text edits; formulas, merges and validations preserved')
