#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from copy import deepcopy
from lxml import etree as ET
from datetime import datetime,timezone
import hashlib,json,os,sys
ROOT=Path('/home/denis/projects/mb001-p11-ics-cleanup-20261014');C=ROOT/'tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami';E=ROOT/'tools/candidates/portfolio-owner-pdf-20261013/p11-50-53-ics-cleanup-20261014'
FILES={'50-slovar-poley-raschet-metrami.docx':('e4b1aa51546f5c7b3e3347057e4f09b4596893084e5a310fb08cbab470e40932',1),'53-zapros-status-obekta.docx':('eadc711f3e9b1b6a094d4f9382bf0f8c212722c5fa4f73b3bd25b324aca53ffd',3)}
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def sha(b):return hashlib.sha256(b).hexdigest()
def sf(p):return sha(p.read_bytes())
def atomic(p,b):
 t=p.with_name(p.name+'.tmp')
 with t.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p);d=os.open(p.parent,os.O_RDONLY);os.fsync(d);os.close(d)
def aj(p,o):atomic(p,(json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode())
def active(root,tag):return [x for x in root.iter(W+tag) if x.get(W+'val','true') not in ('0','false','False')]
def visible(root):return [''.join(t.text or '' for t in p.iter(W+'t')) for p in root.iter(W+'p')]
def colors(styles):
 sm={x.get(W+'styleId'):x for x in styles.iter(W+'style')}
 return {sid:next(sm[sid].iter(W+'color')).get(W+'val') for sid in ('Heading1','Heading2')}
def patch(name,expected,count):
 p=C/name;before=p.read_bytes();assert sha(before)==expected
 with ZipFile(BytesIO(before)) as z:
  assert z.testzip() is None;infos=z.infolist();parts={i.filename:z.read(i.filename) for i in infos}
 before_hash={n:sha(b) for n,b in parts.items()};doc=ET.fromstring(parts['word/document.xml']);styles=ET.fromstring(parts['word/styles.xml']);text=visible(doc)
 assert len(active(doc,'i'))==0 and len(active(doc,'iCs'))==count and colors(styles)=={'Heading1':'323539','Heading2':'323539'}
 touched=[]
 for node in active(doc,'iCs'):
  run=next(a for a in node.iterancestors() if a.tag==W+'r')
  touched.append(''.join(t.text or '' for t in run.iter(W+'t')));node.set(W+'val','0')
 assert len(active(doc,'iCs'))==0 and visible(doc)==text
 parts['word/document.xml']=ET.tostring(doc,encoding='utf-8')
 out=BytesIO()
 with ZipFile(out,'w') as z:
  for info in infos:z.writestr(deepcopy(info),parts[info.filename])
 result=out.getvalue()
 with ZipFile(BytesIO(result)) as z:
  assert z.testzip() is None;after_hash={n:sha(z.read(n)) for n in z.namelist()}
 changed=sorted(n for n in before_hash if before_hash[n]!=after_hash[n]);assert changed==['word/document.xml']
 bad=ET.fromstring(parts['word/document.xml']);first=next(bad.iter(W+'iCs'));first.set(W+'val','true');assert len(active(bad,'iCs'))==1
 atomic(p,result);assert sf(p)==sha(result)
 return {'file':name,'input_sha256':expected,'output_sha256':sf(p),'active_i_before':0,'active_iCs_before':count,'active_i_after':0,'active_iCs_after':0,'touched_run_text':touched,'visible_text_identical':True,'changed_zip_parts':changed,'negative_mutation_detected':True}
def main():
 passport={'schema_version':1,'id':'P11-50-53-ICS-CLEANUP','status':'PREPARED','prepared_at':datetime.now(timezone.utc).isoformat(),'base_head':'58ed5fe199dbcdecf6261eca634fe73b712c73fd','branch':'codex/p11-ics-cleanup-20261014','inputs':{n:v[0] for n,v in FILES.items()},'executor':{'path':str(Path(__file__)),'sha256':sf(Path(__file__))},'contract':['set exactly 1+3 active w:iCs properties to false','preserve visible text, existing graphite styles and compact table layout','change only word/document.xml in two DOCX'],'acceptance':['no active w:i or w:iCs','exact changed ZIP parts','native Word new exact SHA, 2+3 pages, visual review','independent reviewer required'],'checkpoint_policy':'verified_only','release':'HOLD'}
 aj(E/'passport.json',passport)
 report={'schema_version':1,'id':'P11-50-53-ICS-CLEANUP-AUTHOR','status':'RUNNING','started_at':datetime.now(timezone.utc).isoformat(),'model_calls':0}
 try:
  report['files']=[patch(n,*v) for n,v in FILES.items()];report['status']='PASS_AUTHOR_PATCH_ONLY';code=0
 except Exception as exc:
  report['status']='FAIL';report['error_type']=type(exc).__name__;report['error']=str(exc);code=1
 report['finished_at']=datetime.now(timezone.utc).isoformat();report['limitations']=['native Word pending','independent review pending','release HOLD']
 aj(E/'patch-report.json',report);atomic(E/'exit.code',(str(code)+'\n').encode());print(json.dumps({'status':report['status'],'files':report.get('files')},ensure_ascii=False));return code
if __name__=='__main__':sys.exit(main())
