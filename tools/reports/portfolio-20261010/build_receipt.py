import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
from docx import Document
from pypdf import PdfReader
root=Path(__file__).resolve().parent
base=json.loads((root/'base-inventory.json').read_text())
a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);args=a.parse_args()
source=args.source
candidate=root/'candidate'
def digest(b): return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
expected={x['name']:x for x in base['files'] if x['name'] not in ['MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt','.htaccess']}
assert len(expected)==15
for name,row in expected.items(): assert blob((source/name).read_bytes())==row['git_blob'],name
shutil.copyfile(root/'qa/00-INSTRUKCIYA/00-INSTRUKCIYA.pdf',candidate/'00-INSTRUKCIYA.pdf')
members=[]
archive=root/'P2_ROUTE_A_CANDIDATE_2026-10-10.zip'
assert {p.name for p in candidate.iterdir()}==set(expected)
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name in sorted(expected):
  b=(candidate/name).read_bytes();info=zipfile.ZipInfo(name,(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
  row={'name':name,'sha256':digest(b),'git_blob':blob(b),'bytes':len(b),'base_git_blob':expected[name]['git_blob'],'changed':blob(b)!=expected[name]['git_blob']}
  if name.endswith('.pdf'):row['pdf_pages']=len(PdfReader(candidate/name).pages)
  members.append(row)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None;assert len(z.namelist())==15
 for row in members: assert digest(z.read(row['name']))==row['sha256']
assert sum(x['changed'] for x in members)==3
doc=Document(candidate/'00-INSTRUKCIYA.docx')
paras=[p.text for p in doc.paragraphs]
assert sum('применимый срок ответа и его основание' in p for p in paras)==1
assert any('Происхождение и применение форм'==p for p in paras)
pdf=' '.join(p.extract_text() for p in PdfReader(candidate/'00-INSTRUKCIYA.pdf').pages)
normal=lambda t:''.join(t.split()).replace('\u00ad','')
for p in paras:
 if p.strip():assert normal(p) in normal(pdf),p
receipt={'decision_id':'MB001-PRICE-PORTFOLIO-2026-10-10','target_name':'Система оформления и получения оплаты за дополнительные работы','target_price_rub':24900,'base_commit':base['commit'],'status':'CANDIDATE_NOT_PRODUCT_OR_RELEASE_ACCEPTED','zip':archive.name,'sha256':digest(archive.read_bytes()),'bytes':archive.stat().st_size,'members':members,'verification':{'members_exact':15,'unchanged_members':12,'changed_members':3,'docx_pdf_paragraphs_equal':True,'author_visual_pages_reviewed':5,'native_word_excel':'NOT_RUN','independent_legal':'BLOCKED_EXECUTOR_OFFLINE','G1_G8':'NOT_ACCEPTED'},'reproduce':['python port_route_a.py <exact-main-P2-dir> candidate','render_docx.py candidate/00-INSTRUKCIYA.docx --output_dir qa/00-INSTRUKCIYA --emit_pdf','python build_receipt.py']}
(root/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['zip','sha256','bytes','verification']},ensure_ascii=False))
