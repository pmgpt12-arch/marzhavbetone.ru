"""Verify the selected final delta after the documented layout-only recovery."""
import hashlib,io,json,subprocess
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
ROOT=Path(__file__).resolve().parent;W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
EXPECTED={'01-proverochnyy-list-komplekta-ks.docx':'14783a86a1a1a9e4ce5176770c2ba4c6b162261c8cc812f995455d8deb03b9e1','03-akt-skrytyh-rabot.docx':'512e1cdcd2870bf4d945db87b789f8b10cfa1ab278b83bfcc2bfda1cad935e30','09-tipovye-oshibki.docx':'8a7c1bdf2563a7b4da7f762c8ffb826219ff06c44f043a5378c975aa73b96c96','03-filled-example-QA.docx':'b70ed9368ef51eec6dacc30dd1ce32aad8b3d2db204489efee16f9069c22d82c'}
sha=lambda b:hashlib.sha256(b).hexdigest()
def xml(data):
    with ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        return etree.fromstring(z.read('word/document.xml'))
def ps(data):
    return [''.join((n.text or '') if n.tag==W+'t' else '\n' for n in p.iter() if n.tag in (W+'t',W+'br')) for p in xml(data).iter(W+'p')]
author=json.loads((ROOT/'author-structural.json').read_text());checks={};selected=[]
for name,expected in EXPECTED.items():
    data=(ROOT/'candidate'/name).read_bytes();assert sha(data)==expected,name
    xml(data);checks['identity_crc_'+name]=True
    role='synthetic_layout_fixture_not_buyer_file' if '-QA.' in name else 'candidate_not_nominated'
    selected.append({'path':'candidate/'+name,'sha256':expected,'bytes':len(data),'role':role})
for name,mapping in author['source_deltas'].items():
    original=(ROOT/'inputs'/name).read_bytes();data=(ROOT/'candidate'/name).read_bytes()
    assert ps(data)==[mapping.get(p,p) for p in ps(original)]
    with ZipFile(io.BytesIO(original)) as a,ZipFile(io.BytesIO(data)) as b:
        assert a.namelist()==b.namelist()
        assert [n for n in a.namelist() if a.read(n)!=b.read(n)]==['word/document.xml']
    checks['exact_delta_and_other_parts_'+name]=True
checklist=xml((ROOT/'candidate/01-proverochnyy-list-komplekta-ks.docx').read_bytes())
for table in checklist.iter(W+'tbl'):
    widths=[int(c.get(W+'w')) for c in table.find(W+'tblGrid')]
    assert widths[0]>=620 and widths[-2]>=1020
    for row in table.findall(W+'tr'):assert row.find(W+'trPr').find(W+'cantSplit') is not None
    assert table.find(W+'tr').find(W+'trPr').find(W+'tblHeader') is not None
checks['final_checklist_min_width_row_keep_and_repeat_headers']=True
prior=json.loads((ROOT/'verification.json').read_text());assert prior['positive_passed']==7 and prior['negative_detected']==8
for name in ['03-akt-skrytyh-rabot.docx','09-tipovye-oshibki.docx','03-filled-example-QA.docx']:
    record=next(r for r in author['artifacts'] if r['file']==name)
    assert record['sha256']==EXPECTED[name]
checks['reuse_unchanged_act_negative_tests_and_other_renders']=True
render=[]
for name in EXPECTED:
    folder=ROOT/('render-v3' if name.startswith('01-') else 'render')
    pdf=folder/name.replace('.docx','.pdf')
    info=subprocess.check_output(['pdfinfo',str(pdf)],text=True,timeout=5)
    images=sorted((folder if name.startswith('01-') else folder/Path(name).stem).glob('page-*.png'))
    count=int(info.split('Pages:')[1].splitlines()[0]);assert count==len(images)
    render.append({'docx_path':'candidate/'+name,'docx_sha256':EXPECTED[name],'pdf_path':str(pdf.relative_to(ROOT)),'pdf_sha256':sha(pdf.read_bytes()),'page_size':info.split('Page size:')[1].splitlines()[0].strip(),'pages':count,'page_images':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes())} for p in images]})
assert sum(r['pages'] for r in render)==18
checks['four_current_renders_18_page_images']=True
(ROOT/'selected-render-index.json').write_text(json.dumps(render,ensure_ascii=False,indent=2)+'\n')
result={'id':'P3-AOSR-SIGNATURES-REMEDIATION-20261014','base':'df29cf76472e7d8f83b759e69f60b46b25581fb7','claim':6167364456,'status':'PASS_AUTHOR_DELTA_ONLY','checks':checks,'passed':len(checks),'total':len(checks),'artifacts':selected,'retained_structural_checks':13,'retained_strict_checks':7,'retained_negative_mutations_detected':8,'checks_not_additive':'Some checks overlap; do not report them as distinct full buyer scenarios.','visual_record':'visual-review.json; author, not independent','native_word':'NOT_RUN','independent_subject_review':'PENDING','release':'HOLD','G1_G8_accepted_products':0,'product_documents':3,'qa_documents':1,'remaining':['full corporate design/A4 scope of inherited 01/09','remaining substantive claims in 01/09 outside selected delta','native Word of changed SHA','independent normative and buyer review','07 retention references','02/06 Excel','08 full route','10 claims','final kit nomination']}
(ROOT/'author-acceptance-final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'passed':result['passed'],'artifacts':selected,'renders':[{'file':r['docx_path'],'pages':r['pages'],'size':r['page_size']} for r in render]},ensure_ascii=False,indent=2))
