#!/usr/bin/env python3
"""Bounded sequential batch over the existing Word worker, bound to exact SHA."""
from pathlib import Path
import hashlib,json,time,xml.etree.ElementTree as E,shutil,sys,argparse
from submit_office_review_job import submit
R=Path('/home/denis/.local/share/ai-business-os/tool-sandbox/excel-laptop-preflight-20261011')
WORK=Path('/tmp/mb-r3/work')
p=argparse.ArgumentParser();p.add_argument('--revision',default='r3');args=p.parse_args()
if not args.revision.isalnum():raise SystemExit('Invalid revision')
EVIDENCE=Path(__file__).resolve().parents[1]/'tools/candidates/remaining-batch-r3-20261018/evidence'
OUT=EVIDENCE/('word-native' if args.revision=='r3' else 'word-native-'+args.revision)
verified=set()
for index in EVIDENCE.glob('word-native*/summary.json'):
 for record in json.loads(index.read_text()):
  if record['status']=='PASS':
   for f in record['source_files']:verified.add((f['name'],f['sha256']))
OUT.mkdir(parents=True,exist_ok=True)
deadline=time.monotonic()+1800;summary=[]
for sku in sorted(p.name for p in WORK.iterdir()):
 files=[f for f in sorted((WORK/sku).glob('*.docx')) if (f.name,hashlib.sha256(f.read_bytes()).hexdigest()) not in verified]
 for offset in range(0,len(files),4):
  group=files[offset:offset+4];ident=f'{args.revision}-word-{sku.lower()}-{offset//4+1}-20261018'
  jobdir=R/'word'/ident;jobdir.mkdir(exist_ok=True);root=E.Element('job',id=ident,qa_only='true')
  for i,f in enumerate(group):
   b=f.read_bytes()
   E.SubElement(root,'file',name=f.name,tag=f'{sku.lower()}-{offset+i:02}',sha256=hashlib.sha256(b).hexdigest())
  receipt=R/'results/word'/ident/'report.xml'
  if receipt.exists():
   old=E.parse(jobdir/'job.xml').getroot()
   if E.tostring(old)!=E.tostring(root):raise SystemExit('Immutable job input mismatch: use a new revision')
  else:
   for f in group:(jobdir/f.name).write_bytes(f.read_bytes())
   E.ElementTree(root).write(jobdir/'job.xml',encoding='utf-8',xml_declaration=True)
  if not receipt.exists():
   submit(R,'word',jobdir);print('SUBMITTED',ident,flush=True)
   stop=min(deadline,time.monotonic()+240)
   while not receipt.exists() and time.monotonic()<stop:time.sleep(5)
  if not receipt.exists():raise SystemExit('BOUNDED_STOP: receipt missing '+ident)
  report=E.parse(receipt).getroot();target=OUT/ident;target.mkdir(exist_ok=True)
  if report.get('job')!=ident:raise SystemExit('Wrong receipt identity')
  shutil.copyfile(receipt,target/'report.xml');shutil.copyfile(jobdir/'job.xml',target/'job.xml')
  for pdf in receipt.parent.glob('*.pdf'):shutil.copyfile(pdf,target/pdf.name)
  summary.append({'job':ident,'status':report.get('status'),'source_files':[{'name':f.get('name'),'sha256':f.get('sha256'),'tag':f.get('tag')} for f in root]})
  (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
  print('RECEIPT',ident,report.get('status'),flush=True)
  if report.get('status')!='PASS':raise SystemExit('STOP: inspect failed Word receipt')
  if time.monotonic()>deadline:raise SystemExit('BOUNDED_STOP: total budget')
print('ALL_WORD_NATIVE_PASS',sum(len(x['source_files']) for x in summary))
