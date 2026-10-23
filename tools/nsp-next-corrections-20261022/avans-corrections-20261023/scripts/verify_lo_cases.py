from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,subprocess,hashlib
P=Path(__file__).resolve().parent;source=P/'output/02-reestr-izyatiy-po-obektu.xlsx';before=hashlib.sha256(source.read_bytes()).hexdigest();out=P/'proof/lo-recalculated';out.mkdir(exist_ok=True)
inputs=sorted((P/'proof/lo-inputs').glob('*.xlsx'));assert len(inputs)==12
r=subprocess.run(['soffice','-env:UserInstallation=file://'+str(P/'lo-case-profile'),'--headless','--convert-to','xlsx','--outdir',str(out)]+[str(p)for p in inputs],capture_output=True,text=True,timeout=120)
assert r.returncode==0,(r.stdout,r.stderr)
N={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};rows=[];cases=json.loads((P/'proof/XLSX_CASES.json').read_text())['cases']
for p,c in zip(inputs,cases):
 q=out/p.name;assert q.is_file(),p.name
 with ZipFile(q)as z:
  ss=E.fromstring(z.read('xl/sharedStrings.xml'))if 'xl/sharedStrings.xml'in z.namelist()else None;strings=[''.join(si.itertext())for si in ss]if ss is not None else []
  root=E.fromstring(z.read('xl/worksheets/sheet1.xml'));actual=[]
  for row in range(12,17):
   el=root.find('.//m:c[@r="D'+str(row)+'"]',N);v=el.find('m:v',N)
   assert v is not None,(p.name,row,E.tostring(el))
   actual.append(strings[int(v.text)]if el.get('t')=='s'else(v.text if el.get('t')=='str'else float(v.text)))
  assert actual==c['expected'],(p.name,actual,c['expected'])
 rows.append({'case':c['name'],'expected':c['expected'],'actual':actual,'status':'PASS_LIBREOFFICE_RECALC'})
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(P/'proof/XLSX_LO_CASES.json').write_text(json.dumps({'status':'PASS','engine':'LibreOffice bundled runtime','source_sha256':before,'cases':rows,'checks':60,'stdout':r.stdout,'stderr':r.stderr,'native_office':'PENDING'},ensure_ascii=False,indent=2))
print('LIBREOFFICE_PASS',len(rows),'SCENARIOS',60,'EXPECTATIONS')
