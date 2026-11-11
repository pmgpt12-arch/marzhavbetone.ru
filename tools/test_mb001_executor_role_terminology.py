#!/usr/bin/env python3
"""Bounded terminology gate: flagged party names require review, never blind edits."""
import argparse,hashlib,io,json,re,subprocess,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TERM = re.compile(r"(?iu)\bстроител(?:ь|я|ю|ем|и|ям|ями|ях)\b|_СТРОИТЕЛЬ(?![А-ЯЁ])|_СТРОИТЕЛЯ(?![А-ЯЁ])|строительная организация")
SUFFIXES={'.docx','.xlsx','.pdf','.txt'}
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
X='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
def extract(name,data):
 ext=Path(name).suffix.lower()
 if ext=='.docx':
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   out=[]
   for k in z.namelist():
    if k=='word/document.xml' or re.fullmatch(r'word/(?:header|footer)\d+\.xml',k):
     root=ET.fromstring(z.read(k))
     for para in root.iter(W+'p'):
      s=''.join(t.text or '' for t in para.iter(W+'t'))
      if s:out.append(s)
   return '\n'.join(out)
 if ext=='.xlsx':
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   out=[]
   for name in z.namelist():
    if name=='xl/sharedStrings.xml':
     r=ET.fromstring(z.read(name))
     out+=[''.join(n.text or '' for n in si.iter(X+'t')) for si in r.iter(X+'si')]
    if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name):
     r=ET.fromstring(z.read(name))
     out+=[''.join(n.itertext()) for n in r.iter(X+'f')]
   return '\n'.join(out)
 if ext=='.pdf':
  p=subprocess.run(['pdftotext','-layout','-','-'],input=data,capture_output=True,timeout=8)
  if p.returncode:raise ValueError('PDF_TEXT_EXTRACTION_FAILED')
  return p.stdout.decode('utf-8','replace')
 return data.decode('utf-8','replace')

def self_test():
 yes=['Строитель','представитель строителя','СТРОИТЕЛЕМ','{{A1_СТРОИТЕЛЬ}}',
      '{{A5_ПРЕДСТАВИТЕЛЬ_СТРОИТЕЛЯ}}','строительная организация']
 no=['строительство','договор строительного подряда','строительный контроль',
     'строительный адрес','долевое строительство','{{ОБЪЕКТ_СТРОИТЕЛЬСТВА}}',
     'Исполнитель (лицо, осуществляющее строительство, реконструкцию)']
 assert all(TERM.search(s) for s in yes),[s for s in yes if not TERM.search(s)]
 assert all(not TERM.search(s) for s in no),[s for s in no if TERM.search(s)]
 return len(yes)+len(no)

def scan(path,hits,errors,stats):
 path=Path(path)
 paths=sorted(p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in SUFFIXES) if path.is_dir() else [path]
 for f in paths:
  try:
   if f.suffix.lower()=='.zip':
    with zipfile.ZipFile(f) as z:
     for member in z.namelist():
      if Path(member).suffix.lower() in SUFFIXES:
       inspect(str(f)+'::'+member,z.read(member),hits,stats)
   elif f.suffix.lower() in SUFFIXES:inspect(str(f),f.read_bytes(),hits,stats)
  except Exception as e:errors.append({'path':str(f),'error':str(e)})
def inspect(name,data,hits,stats):
 stats['file_count']+=1
 s=extract(name,data)
 digest=hashlib.sha256(data).hexdigest()
 for i,line in enumerate(s.splitlines(),1):
  for m in TERM.finditer(line):
   hits.append({'path':name,'sha256':digest,'line':i,'term':m.group(0),
    'context':line[max(m.start()-65,0):m.end()+95]})
def main():
 p=argparse.ArgumentParser()
 p.add_argument('paths',nargs='*',help='Files, ZIPs or directories. Requires explicit paths for real audit.')
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 tests=self_test()
 if a.self_test and not a.paths:
  print(json.dumps({'verdict':'PASS_SELF_TEST','cases':tests}));return 0
 if not a.paths:p.error('Specify paths to scan, or --self-test.')
 hits=[];errors=[];stats={'file_count':0}
 for src in a.paths:scan(src,hits,errors,stats)
 result={'verdict':'ERROR' if errors else ('REVIEW_REQUIRED' if hits else 'PASS_NO_PARTY_ROLE_HITS'),
         'files':stats['file_count'],'hits':len(hits),'self_test_cases':tests,'errors':errors,'matches':hits}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 return 2 if errors else (1 if hits else 0)
if __name__=='__main__':sys.exit(main())
