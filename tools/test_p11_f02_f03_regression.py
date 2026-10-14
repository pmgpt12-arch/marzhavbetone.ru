"""Read-only P11 F02/F03 regression. No Office, network or product writes.
Usage: python tools/test_p11_f02_f03_regression.py --root . --report report.json
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import argparse, hashlib, json, importlib.util, sys
sys.dont_write_bytecode = True

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--report',type=Path);args=ap.parse_args()
 root=args.root.resolve();candidate=root/'tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami';e=candidate.parent/'p11-f02-f03-20261014'
 spec=importlib.util.spec_from_file_location('p11_f02_f03_contract',e/'execution.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 sha=lambda b:hashlib.sha256(b).hexdigest();delta=json.loads((e/'delta.json').read_text());trees={};identity=[]
 for record in delta['records']:
  key=record['key'];path=root/record['path'];data=path.read_bytes();before=(e/'before'/path.name).read_bytes()
  assert sha(data)==record['after_sha256'] and sha(before)==record['before_sha256']
  beforetree=m.read_doc(before);tree=m.read_doc(data);trees[key]=tree
  expected=[m.txt(p) for p in m.pars(beforetree)]
  for change in record['edits']:
   assert expected.count(change['before'])==1
   expected[expected.index(change['before'])]=change['after']
  assert expected==[m.txt(p) for p in m.pars(tree)],'Unrecorded paragraph change'
  with ZipFile(BytesIO(data)) as afterzip,ZipFile(BytesIO(before)) as beforezip:
   assert afterzip.namelist()==beforezip.namelist()
   assert [n for n in afterzip.namelist() if beforezip.read(n)!=afterzip.read(n)]==['word/document.xml']
  identity.append({'path':record['path'],'sha256':sha(data),'exact_edits_only':True,'non_document_parts_identical':True})
 positive,negative=m.tests(trees)
 assert all(positive.values()) and all(negative.values())
 result={'verdict':'PASS','positive':positive,'negative_mutations_detected':negative,'identity':identity,'scope':'THREE_CHANGED_FILES_STATIC_ONLY_NOT_INDEPENDENT_ACCEPTANCE'}
 content=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if args.report:args.report.write_text(content)
 print(content,end='')
if __name__=='__main__':main()
