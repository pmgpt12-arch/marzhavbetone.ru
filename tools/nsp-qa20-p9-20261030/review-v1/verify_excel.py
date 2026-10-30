from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json
R=Path(__file__).resolve().parent;ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def cells(f):
 out={}
 with ZipFile(f)as z:
  ss=[]
  if 'xl/sharedStrings.xml'in z.namelist():ss=[''.join(x.itertext())for x in E.fromstring(z.read('xl/sharedStrings.xml'))]
  for n in z.namelist():
   if n.startswith('xl/worksheets/sheet')and n.endswith('.xml'):
    r=E.fromstring(z.read(n));out[n]={}
    for c in r.xpath('//s:c',namespaces=ns):
     fo=c.find('s:f',ns);v=c.find('s:v',ns);i=c.find('s:is',ns)
     value=('F',fo.text)if fo is not None else('V',''.join(i.itertext())if i is not None else ss[int(v.text)]if c.get('t')=='s'and v is not None else v.text if v is not None else '')
     if value[1]:out[n][c.get('r')]=value
 return out
f=next((R/'source').glob('*.xlsx'));a=cells(f);b=cells(R/'candidate'/f.name);diff=[]
for n in a:
 for k in set(a[n])|set(b[n]):
  if a[n].get(k)!=b[n].get(k):diff.append((n,k,a[n].get(k),b[n].get(k)))
assert {(n,k)for n,k,*_ in diff}=={('xl/worksheets/sheet1.xml','B27'),('xl/worksheets/sheet1.xml','C24'),('xl/worksheets/sheet3.xml','A16')}
tests=json.loads((R/'internal/EXCEL_TEST_CASES.json').read_text());results=[]
for case in tests:
 with ZipFile(R/'test-recalc-hard'/(case['id']+'.xlsx'))as z:
  r=E.fromstring(z.read('xl/worksheets/sheet1.xml'));c=r.xpath('//s:c[@r="B27"]',namespaces=ns)[0];v=c.find('s:v',ns);actual=v.text or ''
  if c.get('t')=='s':actual=''.join(E.fromstring(z.read('xl/sharedStrings.xml'))[int(actual)].itertext())
  results.append({**case,'libreOfficeValue':actual,'passed':actual.startswith(case['expectedPrefix'])})
assert all(x['passed']for x in results),results
(R/'internal/EXCEL_TEST_RESULTS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));(R/'internal/EXCEL_SCOPE_DIFF.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2));print('PASS six hard-recalc cases; one formula and two text cells changed')
