from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import subprocess,hashlib,json
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';O=Q/'native-recovery-20261022';S=Q.parent/'remaining-audit-20261022/free-sources/downloads';N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
idx=[]
for name in ['vozvrat-ks.zip','dop-raboty.zip']:
 src=S/name;raw=src.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();line=subprocess.check_output(['git','-C',str(R),'ls-tree','637a22fe1b34ded1db64a929a363f0fad14d466e','downloads/'+name],text=True,timeout=10);assert line.split()[2]==blob
 out=[]
 with ZipFile(src)as z:
  assert z.testzip()is None
  for n in z.namelist():
   b=z.read(n);idx.append({'archive':name,'file':n,'sha256':hashlib.sha256(b).hexdigest()})
   if n.endswith('.docx'):
    import io
    with ZipFile(io.BytesIO(b))as doc:
     rt=E.fromstring(doc.read('word/document.xml'));t='\n'.join(''.join(p.xpath('.//w:t/text()',namespaces=N))for p in rt.xpath('//w:p',namespaces=N))
     out+=['FILE: '+n,t,'']
 (O/'content'/name.replace('.zip','.txt')).write_text('\n'.join(out))
(O/'content/FREE_SOURCE_INDEX.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2))
print((O/'content/vozvrat-ks.txt').read_text())
print((O/'content/dop-raboty.txt').read_text())
