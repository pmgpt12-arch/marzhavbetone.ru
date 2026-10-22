#!/usr/bin/env python3
import hashlib,io,json,re,subprocess,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
R=Path('/home/denis/projects/marzhavbetone.ru')
B=R/'.worktrees/codex-p3-aosr-form-layout-20261015'
OUT=Path('/home/denis/.local/state/mb001-executor-terminology-20261015')
PAT=re.compile(r'(?iu)\bстроител[а-яё]*\b')
ROLE=re.compile(r'(?iu)\bстроител(?:ь|я|ю|ем|и|ям|ями|ях)\b|строительная организация|организация[- ]строитель\b|_СТРОИТЕЛЬ(?!СТВА|[А-ЯЁ])|_СТРОИТЕЛЯ(?![А-ЯЁ])')
def get_text(name,dat):
 if name.endswith('.docx'):
  w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
  with zipfile.ZipFile(io.BytesIO(dat)) as z:
   lines=[]
   for key in z.namelist():
    if key=='word/document.xml' or re.fullmatch(r'word/(?:header|footer)\d+\.xml',key):
     root=ET.fromstring(z.read(key))
     for p in root.iter(w+'p'):
      t=''.join(x.text or '' for x in p.iter(w+'t'))
      if t:lines.append(t)
   return '\n'.join(lines)
 if name.endswith('.xlsx'):
  ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
  with zipfile.ZipFile(io.BytesIO(dat)) as z:
   texts=[]
   for key in z.namelist():
    if key=='xl/sharedStrings.xml':
     root=ET.fromstring(z.read(key))
     texts+=[''.join(t.text or '' for t in si.iter(ns+'t')) for si in root.iter(ns+'si')]
    if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',key):
     root=ET.fromstring(z.read(key))
     texts+=[''.join(x.itertext()) for x in root.iter(ns+'f')]
   return '\n'.join(texts)
 if name.endswith('.pdf'):
  p=subprocess.run(['pdftotext','-layout','-','-'],input=dat,capture_output=True,timeout=6)
  if p.returncode:raise ValueError('PDF_EXTRACT_FAILED')
  return p.stdout.decode('utf8','replace')
 return dat.decode('utf8','replace')
seen=set();matches=[];failures=[];counts=Counter()
def check(path,data,scope):
 ext=Path(path).suffix.lower()
 key=(hashlib.sha256(data).hexdigest(),ext)
 if key in seen:return
 seen.add(key);counts['scanned_unique_files']+=1
 try:s=get_text(path,data)
 except Exception as e:
  failures.append({'source':scope,'file':path,'error':str(e)});return
 for ln,line in enumerate(s.splitlines(),1):
  for m in PAT.finditer(line):
   context=line[max(0,m.start()-90):m.end()+110]
   row={'source':scope,'path':path,'sha256':key[0],'line':ln,'term':m.group(),
    'context':context[:240],
    'possible_party_role':bool(ROLE.search(line)) and 'строительный контроль' not in m.group().lower()}
   matches.append(row)
def visit(root,scope):
 if not root.exists():return
 for p in sorted(root.rglob('*')):
  if p.is_file() and p.suffix.lower() in ('.docx','.xlsx','.pdf','.txt'):
   try:check(str(p.relative_to(root)),p.read_bytes(),scope)
   except Exception as e:failures.append({'source':scope,'file':str(p),'error':str(e)})
visit(R/'products-storage','LEGACY_STORAGE')
for d in ['portfolio-owner-editorial-v3-20261013','portfolio-owner-editorial-legal-v4-20261013','portfolio-owner-pdf-20261013']:
 visit(B/'tools/candidates'/d,d)
zpath=B/'tools/candidates/p3-aosr-form-layout-20261015/P3-11-buyer-AOSR-formatted-20261015.zip'
with zipfile.ZipFile(zpath) as z:
 for n in z.namelist():
  if n.lower().endswith(('.docx','.xlsx','.pdf','.txt')):check(n,z.read(n),'P3_ACTUAL_STAGED_ZIP')
group=defaultdict(lambda:{'count':0,'role':0,'paths':set()})
for r in matches:
 s=group[r['source']];s['count']+=1;s['role']+=int(r['possible_party_role']);s['paths'].add(r['path'])
stats={k:{'matches':v['count'],'possible_party_roles':v['role'],'files':len(v['paths'])} for k,v in group.items()}
summary={'read_only':True,'files_unique':counts['scanned_unique_files'],'hits':len(matches),
 'possible_party_role_hits':sum(m['possible_party_role'] for m in matches),'groups':stats,'errors':failures,
 'limitation':'Historical storage + editor candidate versions are distinct evidence; actual final nominations per SKU not established by this scan.'}
OUT.mkdir(exist_ok=True)
(OUT/'audit.json').write_text(json.dumps({'summary':summary,'matches':matches},ensure_ascii=False,indent=2)+'\n')
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with (OUT/'matches.tsv').open('w') as f:
 f.write('source\tpath\tsha256\tline\tterm\tpossible_party_role\tcontext\n')
 for r in matches:
  f.write('\t'.join(str(r[k]).replace('\t',' ').replace('\n',' ') for k in ('source','path','sha256','line','term','possible_party_role','context'))+'\n')
print(json.dumps(summary,ensure_ascii=False))
print('TOP',Counter((m['source'],m['path']) for m in matches if m['possible_party_role']).most_common(22))
