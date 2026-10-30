from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
import fitz,hashlib,json,zipfile
R=Path(__file__).resolve().parent;O=R/'candidate';I=R/'internal';H=lambda b:hashlib.sha256(b).hexdigest()
assert H((R/'source.zip').read_bytes())=='07a16f0d80fe9d3bfdc435acdc513aa4df45029450f0f7afe951d8c19819e038'
tests=json.loads((I/'EXCEL_TEST_RESULTS.json').read_text());assert len(tests)==10 and all(t['passed']for t in tests)
for f in O.glob('*.docx'):
 d=Document(f)
 for t in d.tables:
  assert t._tbl.tblPr.find(qn('w:tblW')).get(qn('w:w'))=='9866',f.name
  assert sum(int(g.get(qn('w:w')))for g in t._tbl.tblGrid)==9866,f.name
preview=fitz.open();rows=[];toc=[]
for f in sorted(O.iterdir()):
 if f.suffix=='.pdf':pdf=f
 elif f.suffix=='.docx':pdf=R/'render-word'/f.stem/(f.stem+'.pdf')
 else:pdf=R/'render-excel'/(f.stem+'.pdf')
 d=fitz.open(pdf);start=len(preview)+1;toc.append([1,f.name,start]);preview.insert_pdf(d)
 rows.append({'name':f.name,'sha256':H(f.read_bytes()),'bytes':f.stat().st_size,'preview_first_page':start,'preview_last_page':len(preview)})
assert len(rows)==12 and len(list(O.glob('*.docx')))==9 and len(list(O.glob('*.xlsx')))==2
preview.set_toc(toc);previewname='P8_predprosmotr_'+str(len(preview))+'str.pdf';preview.save(R/'output'/previewname,garbage=4,deflate=True)
archive=R/'output/P8_Dosrochnoe_pogashenie_avansa_v1.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
 for f in sorted(O.iterdir()):
  info=zipfile.ZipInfo(f.name,(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,f.read_bytes())
with zipfile.ZipFile(archive)as z:assert z.testzip()is None and len(z.namelist())==12
m={'sku':'p8','edition':'P8-review-v1','status':'READY_FOR_OWNER_REVIEW','title':'Требование о досрочном погашении аванса','subtitle':'Проверка оснований, расчёт отработанной части, подготовка ответа заказчику','source_commit':'5361c80125107d9bb47d355bd5730f8b6e2da2c1','source_sha256':H((R/'source.zip').read_bytes()),'files':rows,'file_count':12,'rendered_pages':len(preview),'archive':{'name':archive.name,'sha256':H(archive.read_bytes()),'bytes':archive.stat().st_size},'preview':{'name':previewname,'sha256':H((R/'output'/previewname).read_bytes())},'checks':{'word_table_width_twips':9866,'excel_scenarios_hard_recalculation_passed':10,'all_file_views_reviewed':True,'legal_sources_checked':'2026-10-30','new_native_microsoft_office_run':False,'full_qa_pass':False,'production_changed':False,'owner_edition_approval_pending':True}}
(I/'REVIEW_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print(json.dumps({'archive':m['archive'],'preview':m['preview'],'pages':len(preview)},ensure_ascii=False))
