"""Fix confirmed native Word layout defects in two unaccepted free DOCX copies only."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import subprocess,json,hashlib,shutil
Q=Path(__file__).resolve().parents[1];O=Q/'native-recovery-20261022';S=Q/'prepared-office/word/nsp-next-word-b1-20261022';N='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';ns={'w':N[1:-1]}
sha=lambda b:hashlib.sha256(b).hexdigest()
records=[]
for name in ['01-proverochnyy-list-komplekta-ks.docx','03-tipovye-prichiny-vozvrata.docx']:
 src=S/name;dest=O/'additional-candidates/free/vozvrat-ks'/name;dest.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(src)as z:
  root=E.fromstring(z.read('word/document.xml'));icon=0;table_fixed=0;page=0
  for p in root.xpath('//w:p',namespaces=ns):
   text=''.join(p.xpath('.//w:t/text()',namespaces=ns))
   if 'Переход к полному комплекту'in text:
    for t in p.xpath('.//w:t',namespaces=ns):
     if t.text and '🔗'in t.text:t.text=t.text.replace('🔗 ','').replace('🔗','');icon+=1
   if name.startswith('01-')and text.startswith('Раздел 3.'):
    pp=p.find(N+'pPr')
    if pp is None:pp=E.Element(N+'pPr');p.insert(0,pp)
    if pp.find(N+'pageBreakBefore')is None:E.SubElement(pp,N+'pageBreakBefore')
    page+=1
  if name.startswith('01-'):
   for table in root.xpath('//w:tbl',namespaces=ns):
    rows=table.findall(N+'tr')
    for i,row in enumerate(rows):
     pr=row.find(N+'trPr')
     if pr is None:pr=E.Element(N+'trPr');row.insert(0,pr)
     if pr.find(N+'cantSplit')is None:E.SubElement(pr,N+'cantSplit')
     if i==0 and pr.find(N+'tblHeader')is None:E.SubElement(pr,N+'tblHeader')
     table_fixed+=1
  assert icon==1
  if name.startswith('01-'):assert page==1 and table_fixed>0
  after=E.tostring(root,encoding='utf-8',xml_declaration=True,standalone=True)
  with ZipFile(dest,'w',ZIP_DEFLATED)as o:
   for info in z.infolist():o.writestr(deepcopy(info),after if info.filename=='word/document.xml'else z.read(info.filename))
  with ZipFile(dest)as o:
   assert o.testzip()is None
   for info in z.infolist():
    if info.filename!='word/document.xml':assert o.read(info.filename)==z.read(info.filename)
    if info.filename.endswith(('.xml','.rels')):E.fromstring(o.read(info.filename))
   before_text=''.join(E.fromstring(z.read('word/document.xml')).xpath('//w:t/text()',namespaces=ns));after_text=''.join(root.xpath('//w:t/text()',namespaces=ns))
   assert before_text.replace('🔗 ','')==after_text
   assert 'word/_rels/document.xml.rels'not in z.namelist()or o.read('word/_rels/document.xml.rels')==z.read('word/_rels/document.xml.rels')
  assert sha(src.read_bytes())!=sha(dest.read_bytes())
 record={'archive':'downloads/vozvrat-ks.zip','path':'free/vozvrat-ks/'+name,'base_candidate_sha256':sha(src.read_bytes()),'new_sha256':sha(dest.read_bytes()),'changed_part':'word/document.xml','other_parts_byte_exact':True,'legal_price_and_link_content_unchanged':True,'fix':'Remove unsupported link emoji; checklist also starts Section3 on new page, repeats table headers and prevents row splitting'if name.startswith('01-')else'Remove unsupported link emoji','status':'NEW_LAYOUT_CANDIDATE_NOT_ACCEPTED'}
 records.append(record);print('BUILT',name,flush=True)
 out=O/'rendered-free-v2'/dest.stem
 subprocess.run(['/home/denis/projects/nsp-audit-fixes-20261021/.render-venv/bin/python','/home/denis/projects/nsp-audit-fixes-20261021/render_docx.py',str(dest),'--output_dir',str(out),'--emit_pdf'],capture_output=True,text=True,check=True,timeout=90)
 record['lo_pdf']=str(out/(dest.stem+'.pdf'));record['lo_page_images']=[str(x)for x in sorted(out.glob('page-*.png'))]
 assert record['lo_page_images']
(O/'FREE_DOCX_LAYOUT_V2.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('RENDERED',[(x['path'],len(x['lo_page_images']))for x in records],flush=True)
