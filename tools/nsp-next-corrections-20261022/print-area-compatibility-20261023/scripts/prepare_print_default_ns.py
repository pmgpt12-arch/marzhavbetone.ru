from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import json,base64,hashlib
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');src=Q/'print-area-diagnostic-20261023/inputs/nsp-print-area-diagnostic-v1-20261023';out=[]
for tag,sheet in [('latin','PrintTest'),('cyrillic','Печать')]:
 with ZipFile(src/(tag+'.xlsx'))as z:parts={n:z.read(n)for n in z.namelist()}
 before=parts['xl/workbook.xml'];after=before.replace(b'xmlns:x=',b'xmlns=').replace(b'<x:',b'<').replace(b'</x:',b'</')
 a,b=E.fromstring(before),E.fromstring(after)
 signature=lambda root:[(n.tag,tuple(sorted(n.attrib.items())),n.text)for n in root.iter()]
 assert signature(a)==signature(b);assert b'<x:'not in after and b'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'in after
 parts['xl/workbook.xml']=after
 import io
 mem=io.BytesIO()
 with ZipFile(mem,'w',ZIP_DEFLATED)as z:
  for n,v in parts.items():z.writestr(n,v)
 data=mem.getvalue();out.append({'name':tag+'.xlsx','sheet':sheet,'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()})
(Q/'print-diagnostic-default-ns-transfer.json').write_text(json.dumps(out,ensure_ascii=False))
old=(Q/'scripts/run_print_diagnostic.py').read_text();new=old.replace("D=Q/'print-area-diagnostic-20261023'","D=Q/'print-area-default-ns-20261023'").replace("jid='nsp-print-area-diagnostic-v1-20261023'","jid='nsp-print-area-default-ns-v1-20261023'").replace("Q/'print-diagnostic-transfer.json'","Q/'print-diagnostic-default-ns-transfer.json'")
assert old!=new
(Q/'scripts/run_print_default_ns.py').write_text(new)
print('PREPARED_DEFAULT_NAMESPACE_ONLY',[(x['name'],x['sha256'])for x in out])
