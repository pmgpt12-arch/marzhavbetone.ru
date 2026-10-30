from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json
R=Path(__file__).resolve().parent;ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
cases=json.loads((R/'internal/EXCEL_TEST_CASES.json').read_text());results=[]
for case in cases:
 f=R/'test-recalc-hard'/(case['id']+'.xlsx')
 with ZipFile(f)as z:
  w=E.fromstring(z.read('xl/workbook.xml'));names=w.xpath('//s:sheet/@name',namespaces=ns);idx=names.index(case['sheet'])+1
  s=E.fromstring(z.read('xl/worksheets/sheet'+str(idx)+'.xml'));c=s.xpath('//s:c[@r="'+case['cell']+'"]',namespaces=ns)[0]
  v=c.find('s:v',ns);value=v.text if v is not None else ''
  expected=case['expected'];ok=(value in ['',None]if expected is None else abs(float(value)-expected)<0.005)
  results.append({**case,'libreOfficeValue':value,'passed':ok})
(R/'internal/EXCEL_TEST_RESULTS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=1))
assert all(c['passed']for c in results),'Scenario failure'
