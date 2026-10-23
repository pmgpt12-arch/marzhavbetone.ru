from pathlib import Path
import hashlib, json, re, subprocess, zipfile
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'retention'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
receipt=load(OUT/'native/RESULTS.json')
candidate=OUT/'candidate/04-pismo-o-vozvrate-uderzhaniya.docx'
row=next(f for f in receipt['files'] if f['tag']=='after')
assert receipt['status']==row['status']=='PASS'
assert row['result']['source_sha256']==sha(candidate)
assert row['result']['word_version']=='16.0'
pdf=OUT/'native/evidence/after.pdf'
assert sha(pdf)==row['pdf_sha256']==row['pdf_sha256_verified']
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
assert re.search(r'Pages:\s+5\b',info)
text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
assert 'Повторно их не вычитайте.' in text
assert 'за вычетом подтверждённых возвратов' not in text
source=ROOT/'downloads/uderzhaniya.zip'
target=OUT/'uderzhaniya-QA-only.zip'
assert not target.exists()
with zipfile.ZipFile(source)as old,zipfile.ZipFile(target,'w')as new:
    for entry in old.infolist():
        new.writestr(entry,candidate.read_bytes() if entry.filename==candidate.name else old.read(entry.filename))
with zipfile.ZipFile(source)as old,zipfile.ZipFile(target)as new:
    assert old.namelist()==new.namelist() and new.testzip()is None
    changed=[n for n in old.namelist()if old.read(n)!=new.read(n)]
    assert changed==[candidate.name]
    members=[dict(name=n,sha256=hashlib.sha256(new.read(n)).hexdigest(),changed=n in changed)for n in new.namelist()]
visual=[]
for engine,paths in [('canonical',Path('/workspace/scratch/4c2f1716d70e/qa01-render/retention').glob('page-*.png')),
                     ('native',Path('/workspace/scratch/4c2f1716d70e/qa01-render').glob('native-retention-*.png'))]:
    for p in sorted(paths):
        dst=OUT/'visual'/engine/(p.stem+'.webp');dst.parent.mkdir(parents=True,exist_ok=True)
        im=Image.open(p);im.save(dst,format='WEBP',lossless=True)
        assert ImageChops.difference(im.convert('RGBA'),Image.open(dst).convert('RGBA')).getbbox()is None
        visual.append(dict(engine=engine,path=str(dst.relative_to(OUT)),sha256=sha(dst),pixels_identical=True,
                           reviewed=True))
assert len(visual)==10
result=dict(issue='FL10',status='SCOPED_FIX_NATIVE_PASS_FULL_PRODUCT_BLOCKED',
            candidate_sha256=sha(candidate),source_zip_sha256=sha(source),qa_zip_sha256=sha(target),
            native_job=receipt['job'],native_receipt_sha256=receipt['receipt_sha256'],
            native_pdf_sha256=sha(pdf),native_pdf_pages_viewed=5,canonical_pages_viewed=5,
            word_statistics_pages=row['result']['pages'],
            page_count_limit='Word ComputeStatistics reports 6 for both before and after; actual exported PDF contains 5. Five actual pages reviewed; no claim of six PDF pages.',
            visual_scope='Changed paragraph readable; no new clipping. Existing split letter and near-empty page 5 with missing link glyph remain product layout blockers.',
            arithmetic_cases=3,changed_docx_parts=['word/document.xml'],changed_members=changed,members=members,
            other_members_byte_exact=True,visual=visual,publication=False,
            remaining=['FL12: event already occurred versus expected; actual demand for return versus request for date.',
                       'Other categorical legal statements, support and applicable clickable norms require review.',
                       'Existing Word layout and glyph defect; no whole-product visual PASS.'])
(OUT/'ACCEPTANCE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k]for k in ['status','qa_zip_sha256','native_pdf_pages_viewed','canonical_pages_viewed']},ensure_ascii=False))
