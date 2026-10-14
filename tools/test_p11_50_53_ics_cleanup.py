#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from lxml import etree as ET
import argparse,hashlib,json,os,subprocess,sys
BASE='58ed5fe199dbcdecf6261eca634fe73b712c73fd';REL='tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami';W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
FILES={'50-slovar-poley-raschet-metrami.docx':('6f40e5d3757d77d6460efb990f459167220f5fb9f3f36a6a6bcfb92b415869d5',1),'53-zapros-status-obekta.docx':('c3fccbdc5e7e6841ca8c48b5ab1c199bdebe0d2f4990c232040d20f70bfc023e',3)}
def sha(b):return hashlib.sha256(b).hexdigest()
def parts(b):
 with ZipFile(BytesIO(b)) as z:assert z.testzip() is None;return {n:z.read(n) for n in z.namelist()}
def active(root,tag):return [x for x in root.iter(W+tag) if x.get(W+'val','true') not in ('0','false','False')]
def visible(root):return [''.join(t.text or '' for t in p.iter(W+'t')) for p in root.iter(W+'p')]
def atomic(p,o):
 b=(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode();t=p.with_name(p.name+'.tmp');p.parent.mkdir(parents=True,exist_ok=True)
 with t.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p);d=os.open(p.parent,os.O_RDONLY);os.fsync(d);os.close(d)
def main():
 a=argparse.ArgumentParser();a.add_argument('--root',default='.');a.add_argument('--report');x=a.parse_args();root=Path(x.root).resolve();out={};neg={}
 for name,(expected,count) in FILES.items():
  cur=(root/REL/name).read_bytes();base=subprocess.check_output(['git','show',f'{BASE}:{REL}/{name}'],cwd=root);cp=parts(cur);bp=parts(base)
  cd=ET.fromstring(cp['word/document.xml']);bd=ET.fromstring(bp['word/document.xml']);before=active(bd,'iCs')
  normalized=ET.fromstring(bp['word/document.xml'])
  for n in active(normalized,'iCs'):n.set(W+'val','0')
  changed=sorted(n for n in bp if sha(bp[n])!=sha(cp[n]))
  checks={'exact_sha':sha(cur)==expected,'changed_parts_only_document_xml':changed==['word/document.xml'],
   'baseline_active_i_zero':len(active(bd,'i'))==0,'baseline_active_iCs_exact':len(before)==count,
   'after_active_i_zero':len(active(cd,'i'))==0,'after_active_iCs_zero':len(active(cd,'iCs'))==0,
   'visible_text_identical':visible(cd)==visible(bd),'document_xml_exact_expected_normalization':ET.tostring(normalized,encoding='utf-8')==cp['word/document.xml']}
  bad=ET.fromstring(cp['word/document.xml']);next(bad.iter(W+'iCs')).set(W+'val','true');neg[name]=len(active(bad,'iCs'))==1
  out[name]={'input_sha256':sha(base),'output_sha256':sha(cur),'changed_parts':changed,'checks':checks}
 ok=all(all(v['checks'].values()) for v in out.values()) and all(neg.values());r={'schema_version':1,'id':'P11-50-53-ICS-CLEANUP-REGRESSION','status':'PASS' if ok else 'FAIL','base':BASE,'files':out,'negative_mutations':neg,'model_calls':0,'release':'HOLD'}
 if x.report:atomic(Path(x.report),r)
 print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
