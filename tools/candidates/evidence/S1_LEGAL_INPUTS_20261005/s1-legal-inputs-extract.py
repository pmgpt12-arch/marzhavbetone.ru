from pathlib import Path
import sys, json, hashlib, re, subprocess, zipfile, importlib.util
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
WT=Path('/home/denis/projects/marzhavbetone.ru/.worktrees/codex-s1-legal-inputs-20261005')
OUT=WT/'tools/candidates/evidence/S1_LEGAL_INPUTS_20261005'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('semantic_hash',WT/'tools/semantic_hash.py'); sem=importlib.util.module_from_spec(spec); spec.loader.exec_module(sem)
base=subprocess.check_output(['git','-C',str(WT),'rev-parse','HEAD'],text=True).strip()
folder=WT/'tools/candidates/s1-oplata-za-raboty'
files=sorted(p for p in folder.iterdir() if re.match(r'^\d{2}-',p.name) and p.suffix in ('.docx','.xlsx','.txt'))
assert len(files)==11,len(files)
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
terms=re.compile(r'\b(?:ГК|АПК|НК|ГПК)\b|стать[яеиюёй]|\bст\.\s*\d|Пленум|Верховн|закон|иск|досудеб|претензи|подсуд|судеб|госпошлин|процент|неустой|срок|вручени|зач[её]т|приостанов|удержани|уступк|давност|банкрот|обязатель|доказатель|односторон|допустим|арбитраж|договор|приемк|приёмк',re.I)
refpat=re.compile(r'(?:ч(?:асть|асти)?\.?\s*\d+(?:\.\d+)?\s*)?(?:п(?:ункт|ункты|унктов)?\.?\s*\d+(?:\.\d+)?\s*)?(?:ст\.|статья|статьи|статью|статей)\s*\d+(?:\.\d+)?(?:\s*(?:,|и|–|-)\s*\d+(?:\.\d+)?)*(?:\s*(?:ГК|АПК|НК|ГПК)(?:\s*РФ)?)?',re.I)
rows=[]
for p in files:
 if p.suffix=='.docx':
  with zipfile.ZipFile(p) as z: root=ET.fromstring(z.read('word/document.xml'))
  parts=[''.join(n.text or '' for n in par.iter(W+'t')) for par in root.iter(W+'p')]
  parts=[s for s in parts if s.strip()]
 elif p.suffix=='.xlsx': parts=sem.xlsx_parts(p)
 else: parts=[s for s in p.read_text().splitlines() if s.strip()]
 body='\n'.join(parts)
 extracted=OUT/(p.stem+'.extracted.txt'); extracted.write_text(body+'\n')
 claims=[{'location':('paragraph' if p.suffix=='.docx' else 'semantic_part' if p.suffix=='.xlsx' else 'nonempty_line')+':'+str(i+1),'text':s,'literal_references':refpat.findall(s),'classification':'OBSERVED_TEXT; EXPERT_REVIEW_NOT_PERFORMED'} for i,s in enumerate(parts) if terms.search(s)]
 rows.append({'path':p.relative_to(WT).as_posix(),'blob_sha':subprocess.check_output(['git','-C',str(WT),'rev-parse',base+':'+p.relative_to(WT).as_posix()],text=True).strip(),'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'semantic_hash':sem.semantic_hash(p) if p.suffix in ('.docx','.xlsx') else None,'extracted_path':extracted.relative_to(WT).as_posix(),'extracted_sha256':hashlib.sha256(extracted.read_bytes()).hexdigest(),'source_sha':base,'reference_candidates':claims,'literal_reference_count':sum(len(c['literal_references']) for c in claims),'registry_mapping_status':'BLOCKED_REGISTRY_UNAVAILABLE','normative_verdict':'NOT_VERIFIED'})
index={'observed_at':datetime.now(timezone.utc).isoformat(),'source_sha':base,'scope':'11 buyer files 00-10; MANIFEST excluded from buyer scan','extraction':'Literal text and broad keyword candidates only; not exhaustive legal scope, no legal verdict','semantic_hash_implementation':{'path':'tools/semantic_hash.py','file_sha256':hashlib.sha256((WT/'tools/semantic_hash.py').read_bytes()).hexdigest()},'registry_probe':{'expected':['data/legal/norms.yaml','data/legal/document-norms.yaml','data/legal/normative-results.yaml','data/legal/human-review.yaml'],'files_exist':{n:(WT/'data/legal'/n).exists() for n in ('norms.yaml','document-norms.yaml','normative-results.yaml','human-review.yaml')},'gitignore_observed':'SITE .gitignore:54:data/*','result':'BLOCKED_REGISTRY_UNAVAILABLE; no registry/historical hash comparison possible'},'documents':rows}
(OUT/'buyer-claims-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
legal=OUT/'literal-claims.md'
text=['# S1 literal reference and claim candidates','',f'Pinned source: `{base}`. This is deterministic extraction, not legal acceptance.','']
for row in rows:
 text.extend(['## '+row['path'].split('/')[-1],'',f"Semantic hash: `{row['semantic_hash']}`; byte SHA-256: `{row['file_sha256']}`.",''])
 for c in row['reference_candidates']: text.append('- '+c['location']+': '+c['text'])
 text.append('')
legal.write_text('\n'.join(text)+'\n')
print(json.dumps({'source_sha':base,'documents':len(rows),'literal_references':[(r['path'].split('/')[-1],r['literal_reference_count'],len(r['reference_candidates'])) for r in rows],'output':str(OUT)},ensure_ascii=False))
