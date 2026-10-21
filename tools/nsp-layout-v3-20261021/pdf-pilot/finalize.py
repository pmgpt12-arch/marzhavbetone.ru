"""Complete the existing DOCX->PDF export with image-link annotations (LO drops these)."""
from pathlib import Path
from pypdf import PdfReader,PdfWriter
from pypdf.annotations import Link
from pypdf.generic import NameObject,TextStringObject
import pdfplumber,json,hashlib,sys
HERE=Path(__file__).resolve().parent;source=Path(sys.argv[1]);dest=HERE/'NSP_P1_design_pilot.pdf';contacts=json.loads((HERE/'contacts.json').read_text());r=PdfReader(source);w=PdfWriter();w.clone_document_from_reader(r)
assert len(r.pages)==4
with pdfplumber.open(source) as pdf:
 for index,page in enumerate(pdf.pages):
  icons=sorted([i for i in page.images if 10<i['width']<13 and 10<i['height']<13 and i['y1']<55],key=lambda i:i['x0']);assert len(icons)==5
  for icon,c in zip(icons,contacts):
   rect=(icon['x0']-2,icon['y0']-2,icon['x1']+2,icon['y1']+2);link=Link(rect=rect,url=c['url']);link[NameObject('/Contents')]=TextStringObject(c['name']);w.add_annotation(page_number=index,annotation=link)
w.add_metadata({'/Title':'Система получения оплаты за выполненные работы | Пилот оформления','/Author':'На стороне подрядчика','/Subject':'Пилот оформления PDF без изменения покупательских мастеров'})
with dest.open('wb') as f:w.write(f)
check=PdfReader(dest);assert [p.extract_text() for p in check.pages]==[p.extract_text() for p in r.pages]
for page in check.pages:
 links=[a.get_object() for a in page.get('/Annots',[])];footer=[a for a in links if float(a['/Rect'][1])<55];assert len(footer)==5
 assert [str(a['/A']['/URI']) for a in footer]==[c['url'] for c in contacts]
 assert all(float(a['/Rect'][2])<float(b['/Rect'][0]) for a,b in zip(footer,footer[1:]))
text='\n'.join(p.extract_text() for p in check.pages);assert 'marzhavbetone' not in text.lower()+str(check.metadata).lower()
proof={'status':'PASS','pages':4,'links_per_page':[len(p.get('/Annots',[])) for p in check.pages],'footer_icon_links':20,'footer_link_mapping':'PASS','overlap':'NONE','export_text':'UNCHANGED','searchable_text':'PASS','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'tagged_pdf':'NOT_CLAIMED; PDF export is untagged, annotation Contents names are supplied','unified_forms':'No unified form in chosen instruction; source forms and buyer masters unchanged','status_scope':'PILOT_ONLY; owner approval required before propagation'};(HERE/'verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(proof)
