"""Addressed port from #569 onto official-forms base; never touches live files."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
from lxml import etree

BASE='b85a2e716d501cbc54c840f58027ecfd6a60964b'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
CHANGES={
 '00-INSTRUKCIYA.docx':('a27ffb94bb47a66743fe01d188055813159a04117d09514db8f8aeef9c14f609', 'объёма, срок ответа, статус участка и приложения.', 'объёма, применимый срок ответа и его основание, статус участка и приложения.'),
 '03-uvedomlenie-o-doprabotah.docx':('7360634f99b3b7f288c394bc88140cc84f92d6a0a2786b7816d8c2bc23a5ae16', 'подрядчик по п. 3 ст. 743 ГК РФ обязан приостановить соответствующие работы.', 'подрядчик по п. 3 ст. 743 ГК РФ обязан приостановить соответствующие работы. Иной применимый срок по закону или договору, если есть: основание [___], срок [___].'),
}
def run(source, output):
 output.mkdir(parents=True,exist_ok=True)
 report={'base_commit':BASE,'source_pr':569,'source_head':'25baa15cfc224f5445929263646a23f65f1837c1','changed':[],'status':'CANDIDATE_NOT_ACCEPTED'}
 for p in sorted(source.iterdir()):
  if p.is_file(): shutil.copy2(p,output/p.name)
 for name,(sha,old,new) in CHANGES.items():
  p=source/name; raw=p.read_bytes(); assert hashlib.sha256(raw).hexdigest()==sha,name
  with zipfile.ZipFile(p) as z: parts={i.filename:(i,z.read(i.filename)) for i in z.infolist()}
  root=etree.fromstring(parts['word/document.xml'][1]);hits=0
  for t in root.findall('.//w:t',NS):
   if old in (t.text or ''):
    assert t.text.count(old)==1
    t.text=t.text.replace(old,new);hits+=1
  assert hits==1,(name,hits)
  xml=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
  with zipfile.ZipFile(output/name,'w') as z:
   for path,(info,data) in parts.items(): z.writestr(info,xml if path=='word/document.xml' else data)
  with zipfile.ZipFile(output/name) as z:
   assert all(z.read(path)==data for path,(info,data) in parts.items() if path!='word/document.xml')
  after=(output/name).read_bytes()
  report['changed'].append({'name':name,'before_sha256':sha,'after_sha256':hashlib.sha256(after).hexdigest(),'replacement_before':old,'replacement_after':new,'unchanged_zip_parts':len(parts)-1})
 (output.parent/'route-a-delta.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('source',type=Path);a.add_argument('output',type=Path);v=a.parse_args();run(v.source,v.output)
