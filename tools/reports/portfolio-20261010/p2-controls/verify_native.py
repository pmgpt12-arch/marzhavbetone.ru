import argparse,hashlib,json,zipfile
from pathlib import Path
from lxml import etree
a=argparse.ArgumentParser();a.add_argument('output',type=Path);v=a.parse_args();root=Path(__file__).resolve().parent
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(v.output) as z:r=etree.fromstring(z.read('xl/worksheets/sheet1.xml'))
cs={c.get('r'):c for c in r.findall('.//s:c',ns)};results=[]
for t in json.loads((root/'native-expectations.json').read_text()):
 c=cs[t['cell']];value=c.find('s:v',ns);s='' if value is None or value.text is None else value.text
 actual=s if c.get('t') in ['e','str','inlineStr'] or s=='' else float(s)
 results.append({**t,'actual':actual,'pass':actual==t['expected']})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'engine':'LibreOfficeDev26.8.0.0.alpha0','input_sha256':sha(root/'native-fixture.xlsx'),'output_sha256':sha(v.output),'output_newer_than_input':v.output.stat().st_mtime>=(root/'native-fixture.xlsx').stat().st_mtime,'scope':'arithmetic only; no UI validation or MSExcel','cases':results}
(root/'native-results-v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert report['output_newer_than_input'];assert all(x['pass'] for x in results)
print('NATIVE_ARITHMETIC_PASS',len(results))
