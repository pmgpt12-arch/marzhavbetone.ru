#!/usr/bin/env python3
"""Verify the actual final work tree; never equate local QA with native Office."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import json,shutil,fitz
from editorial_business_style_gate import check,extract
from office_core_metadata_gate import check_bytes
from standard_form_original_gate import check_member
R=Path(__file__).resolve().parents[1]
B=R/'tools/candidates/remaining-batch-r3-20261018';A=B/'form-originals-audit'
W=Path('/tmp/mb-r3/work');C=Path('/tmp/mb-r3/official')
digest=lambda p:sha256(p.read_bytes()).hexdigest()
# Copies follow the exact reviewed current DOCX renders, not a former edition.
rendered=json.loads(Path('/tmp/mb-r3/render/word-render-status.json').read_text())
for sku in ['P1','P2']:
 p=W/sku/'00-INSTRUKCIYA.docx'
 row=next(r for r in rendered if r['sku']==sku and r['file']==p.name)
 assert digest(p)==row['source_sha256'] and row['returncode']==0
 shutil.copyfile(row['pdfs'][0],p.with_suffix('.pdf'))
refs=json.loads((A/'reference-manifest.json').read_text())
source_by_url={'https://minjust.consultant.ru/files/47785':'344-minjust.pdf','https://minjust.consultant.ru/files/28915':'1026-minjust.pdf','https://www.stroysmeta.ru/download/1259/269':'100-album.pdf','https://files.stroyinf.ru/Data/562/56263.pdf':'24297.pdf'}
for ref in refs:
 source=C/source_by_url[ref['source_url']];target=A/ref['file']
 assert digest(source)==ref['source_sha256'] and digest(target)==ref['sha256']
 original=fitz.open(source);result=fitz.open(target)
 start,end=ref['source_pages_1based'];assert len(result)==end-start+1
 for i,page in enumerate(result):
  assert original[start-1+i].rect==page.rect
  assert original[start-1+i].get_pixmap().samples==page.get_pixmap().samples
fitz.TOOLS.mupdf_warnings() # Source PDF garbage collector can log unused broken links.
for lock in json.loads((B/'original-form-lock.json').read_text()):
 assert digest(W/lock['sku']/lock['member'])==lock['sha256'],('original bytes',lock)
for p in (W/'P3').iterdir():
 if p.name not in {'00-START-HERE.txt','03-akt-skrytyh-rabot.pdf'}:
  assert digest(p)==digest(Path('/tmp/mb-r3/all-packages-extra/P3')/p.name),('P3 unrelated file changed',p)
expected={'P1':20,'P2':15,'P3':11,'P4':25,'P7':13,'P8':11,'P9':10,'P10':8,'P13':10}
obsolete=['06-zhurnal-obemov.xlsx','35-obshiy-zhurnal-rabot.xlsx','36-vhodnoy-kontrol.xlsx','04-akt-skrytyh-rabot.xlsx','03-akt-skrytyh-rabot.docx','31-akt-osvidetelstvovaniya-skrytyh-rabot.xlsx']
failures=[];pending=[];count=0;office=0;qualified=0
for folder in sorted(W.iterdir()):
 files=sorted(p for p in folder.iterdir() if p.is_file());assert len(files)==expected[folder.name]
 txt=folder/'00-START-HERE.txt'
 if txt.exists() and folder.name in {'P1','P2','P4'}:
  text=txt.read_text();inventory=text.split('СОСТАВ АРХИВА\n')[1].splitlines()
  assert inventory==sorted(p.name for p in files),(folder.name,'TXT inventory')
 for p in files:
  assert p.suffix in {'.docx','.xlsx','.xls','.pdf','.txt'}
  data=p.read_bytes();count+=1;failures+=check(p.name,data)
  if p.suffix in {'.docx','.xlsx'}:check_bytes(data,str(p));office+=1
  text=extract(p.name,data)
  assert not any(old in text for old in obsolete),('stale reference',p)
  if p.suffix=='.docx':
   with ZipFile(p) as z:
    assert not any(old.encode() in z.read(n) for old in obsolete for n in z.namelist() if n.endswith(('.xml','.rels'))),(p,'stale Word relationship')
  try:check_member(folder.name,p.name,data)
  except ValueError as e:pending.append(str(e))
  if p.suffix=='.pdf':
   d=fitz.open(p);assert len(d)>0
   for page in d:page.get_pixmap()
   assert not fitz.TOOLS.mupdf_warnings(),('final PDF warnings',p)
assert not failures,failures
report={'status':'LOCAL_PASS_NATIVE_OFFICE_PENDING','files':count,'office_core_metadata_crc_pass':office,'editorial':'PASS','obsolete_references':'ABSENT','buyer_inventories':'PASS','original_source_pages_identical':sum(r['pages'] for r in refs),'original_forms_bytes':'PASS','P3_unrelated_files':'UNCHANGED','counts':expected,'original_forms_pending':pending,'native_office':'PENDING','publication':'NOT_PERFORMED'}
(A/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
