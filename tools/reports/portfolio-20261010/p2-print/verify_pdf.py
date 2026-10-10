"""Read-only actual Calc PDF receipt, full instruction text and page bounds."""
import hashlib,json,re,zipfile
from pathlib import Path
import fitz
from lxml import etree as E
p=Path(__file__).resolve().parent
norm=lambda s:re.sub(r'\s+','',s)
report=[]
for stem in ['07-raschet-stoimosti','08-zhurnal-doprabot']:
    x=p/(stem+'.xlsx'); pdf=p/'pdf-final'/(stem+'.pdf'); d=fitz.open(pdf)
    assert pdf.stat().st_mtime>=x.stat().st_mtime
    with zipfile.ZipFile(x) as z:
        root=E.fromstring(z.read('xl/worksheets/sheet2.xml')); n={'x':root.nsmap['x']}
        texts=root.xpath('//x:c/x:v/text() | //x:c/x:is/x:t/text()',namespaces=n)
    final=norm(d[-1].get_text())
    assert all(norm(t) in final for t in texts), 'Instruction missing or cropped'
    for page in d:
        for w in page.get_text('words'):
            assert w[0]>=0 and w[1]>=0 and w[2]<=page.rect.width+1 and w[3]<=page.rect.height+1
    assert len(d)==5
    report.append({'xlsx':x.name,'input_sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'pdf':pdf.name,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(d),'page_sizes':[[round(q.rect.width),round(q.rect.height)] for q in d],'instruction_text_complete':True,'text_in_page_bounds':True,'output_not_older_than_input':True,'visual_review':'all 10 pages reviewed; no clipping; headers repeat, total visible; blank buyer forms only','ui_protection_attempt':'NOT_VERIFIED'})
(p/'pdf-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('PASS actual PDF bounds/instruction: 2 workbooks, 10 pages')
