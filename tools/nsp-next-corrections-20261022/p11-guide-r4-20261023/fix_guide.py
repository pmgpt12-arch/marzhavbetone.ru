from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,hashlib,base64,copy
p=Path(__file__).resolve().parent;src=p/'source';out=p/'candidates';src.mkdir(exist_ok=True);out.mkdir(exist_ok=True);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
rows=[]
for x in json.loads((p/'source-transfer.json').read_text()):
 f=src/x['name'];f.write_bytes(base64.b64decode(x['base64'],validate=True));assert hashlib.sha256(f.read_bytes()).hexdigest()==x['sha256']
 with ZipFile(f)as z:infos=z.infolist();parts={i.filename:z.read(i)for i in infos}
 root=E.fromstring(parts['word/document.xml']);matches=root.xpath('.//w:t[contains(.,"Заказчику направляется заполненная форма")]',namespaces=ns);assert len(matches)==1
 before=E.tostring(root,method='c14n');n=matches[0];n.text=n.text.replace('Заказчику направляется заполненная форма','Адресату направляется заполненная форма');after=E.tostring(root,method='c14n')
 assert before.replace('Заказчику направляется заполненная форма'.encode(),'Адресату направляется заполненная форма'.encode())==after
 parts['word/document.xml']=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True);dst=out/f.name
 with ZipFile(dst,'w')as z:
  for i in infos:z.writestr(copy.copy(i),parts[i.filename])
 with ZipFile(f)as a,ZipFile(dst)as b:assert a.namelist()==b.namelist()and all(a.read(n)==b.read(n)for n in a.namelist()if n!='word/document.xml')
 rows.append({'file':f.name,'base_sha256':x['sha256'],'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'changes':'One recipient word in guide only; sendable letter and every other package part preserved','role':'TEST_ONLY'if f.name.startswith('example-')else'BUYER_CANDIDATE'})
(p/'MANIFEST.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rows,ensure_ascii=False))
