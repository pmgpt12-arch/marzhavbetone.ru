from pathlib import Path
from pypdf import PdfReader
import re,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
assert (ROOT/'assets/nsp-hero-desktop.webp').stat().st_size<=250*1024 and (ROOT/'assets/nsp-hero-mobile.webp').stat().st_size<=150*1024
text=(ROOT/'index.html').read_text();assert text.count('class="home-opening"')==1;assert 'home-v3' in text and 'Сохраните</span> прибыль по объекту' in text
assert text.count('<h1')==1 and text.count('class="stage-solutions"')==1
for url in ['/katalog.html#group-do-podpisaniya','/katalog.html#group-zakrytie-i-oplata','/katalog.html#selection-oplata']:assert 'href="'+url+'"' in text
source=json.loads((HERE/'pdf-pilot/source.json').read_text());assert hashlib.sha256((ROOT/source['source']).read_bytes()).hexdigest()==source['source_docx_sha256'];assert hashlib.sha256((ROOT/source['accepted_pdf']).read_bytes()).hexdigest()==source['accepted_pdf_sha256']
contacts=json.loads((HERE/'pdf-pilot/contacts.json').read_text());pdf=PdfReader(HERE/'pdf-pilot/NSP_P1_design_pilot.pdf');assert len(pdf.pages)==4
for page in pdf.pages:
 links=[a.get_object() for a in page.get('/Annots',[])];links=[a for a in links if float(a['/Rect'][1])<55];assert len(links)==5 and [str(a['/A']['/URI']) for a in links]==[c['url'] for c in contacts]
assert not re.search('marzhavbetone','\n'.join(p.extract_text() for p in pdf.pages)+str(pdf.metadata),re.I)
# None of the accepted buyer masters may be edited by this homepage/pilot branch.
changed=subprocess.check_output(['git','diff','--name-only','ec8a7865c2a86da62c8259cbfb5dc15dce207b7c'],cwd=ROOT,text=True).splitlines();assert not any(p.startswith('products-storage/') for p in changed)
print('HOME_V3_SOURCE=PASS; assets within budget; 5 PDF icon destinations; buyer source unchanged')
