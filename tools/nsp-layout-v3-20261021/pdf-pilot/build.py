"""Pilot only: reuse accepted P1 DOCX and its existing LibreOffice PDF export."""
from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree as E
from PIL import Image
import cairosvg,json,hashlib,copy,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=ROOT/'products-storage/01-zakrytie-rabot/00-INSTRUKCIYA.docx';d=Document(SRC);original=[E.tostring(x) for x in d.element.body if not x.tag.endswith('sectPr')]
contacts=json.loads((HERE/'contacts.json').read_text());html=(ROOT/'index.html').read_text()
for key,title in [('telegram','Telegram'),('instagram','Instagram')]:
 svg=re.search(r'aria-label="'+title+r'" title="'+title+r'"><svg(.*?)</svg>',html,re.S)[1]
 (HERE/'icons'/f'{key}.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"'+svg.replace('currentColor','#4F5B65')+'</svg>')
for c in contacts:
 cairosvg.svg2png(url=str(HERE/'icons'/(c['key']+'.svg')),write_to=str(HERE/'icons'/(c['key']+'.png')),output_width=160,output_height=160)
assert (HERE/'edge-decoration.png').is_file(), 'MISSING_APPROVED_EDGE_ASSET'
# Existing instruction export works on a DOCX; add presentation pages around the untouched body.
body=d.element.body;first=body[0];cover=[]
for text,size,bold in [('НА СТОРОНЕ ПОДРЯДЧИКА',10,False),('Система получения оплаты за выполненные работы',30,True),('Инструкция по работе с комплектом',14,False),('Подтвердить объём, оформить сдачу результата работ и предъявить обоснованное требование об оплате.',12,False)]:
 p=d.add_paragraph();p.paragraph_format.space_after=Pt(24);p.paragraph_format.keep_with_next=True
 if len(cover)==0:p.paragraph_format.space_before=Pt(80)
 run=p.add_run(text);run.font.name='DejaVu Sans';run.font.size=Pt(size);run.bold=bold;run.font.color.rgb=RGBColor.from_string('252A2E');cover.append(p._p)
p=d.add_paragraph();p.add_run().add_break(__import__('docx').enum.text.WD_BREAK.PAGE);cover.append(p._p)
for node in cover:body.remove(node);first.addprevious(node)
p=d.add_paragraph('Связь с проектом',style='Title');p.paragraph_format.page_break_before=True;p.paragraph_format.space_before=Pt(48)
p=d.add_paragraph('Вопросы по заполнению документов и выбору порядка действий можно направить удобным способом. Укажите комплект и файл, по которому возник вопрос.');p.paragraph_format.space_after=Pt(28)
for c in contacts:
 p=d.add_paragraph();p.paragraph_format.space_after=Pt(18);run=p.add_run(c['name']+'\n');run.bold=True;run.font.size=Pt(11)
 rid=p.part.relate_to(c['url'],RT.HYPERLINK,is_external=True);link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rid);run=OxmlElement('w:r');props=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'4F5B65');props.append(color);run.append(props);t=OxmlElement('w:t');t.text=c['url'].removeprefix('mailto:');run.append(t);link.append(run);p._p.append(link)
for sec in d.sections:
 # Keep accepted margins, table geometry and body formatting.
 for p in sec.header.paragraphs:p.text=''
 f=sec.footer.paragraphs[0];f.text='';f.paragraph_format.space_before=Pt(0);f.paragraph_format.space_after=Pt(0)
 run=f.add_run('На стороне подрядчика   ');run.font.name='DejaVu Sans';run.font.size=Pt(9.5);run.font.color.rgb=RGBColor.from_string('4F5B65')
 for c in contacts:
  run=f.add_run();run.add_picture(str(HERE/'icons'/(c['key']+'.png')),width=Cm(.40),height=Cm(.40));link=OxmlElement('w:hyperlink');link.set(qn('r:id'),f.part.relate_to(c['url'],RT.HYPERLINK,is_external=True));f._p.remove(run._r);link.append(run._r);f._p.append(link);f.add_run('   ')
 run=f.add_run('  |  ');run.font.size=Pt(9)
 fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');f._p.append(fld)
 # Decoration occupies only the outer right margin. It never crosses the text/table area.
 p=sec.header.paragraphs[0];run=p.add_run();run.add_picture(str(HERE/'edge-decoration.png'),width=Cm(1.3),height=Cm(8))
 inline=run._r.xpath('.//wp:inline')[0];inline.tag=qn('wp:anchor');inline.set('behindDoc','1');inline.set('simplePos','0');inline.set('relativeHeight','0');inline.set('locked','0');inline.set('layoutInCell','1');inline.set('allowOverlap','1');pos=OxmlElement('wp:simplePos');pos.set('x','0');pos.set('y','0');inline.insert(0,pos)
 for axis,rel,value in [('H','page',19.6),('V','page',17.0)]:
  el=OxmlElement('wp:position'+axis);el.set('relativeFrom',rel);off=OxmlElement('wp:posOffset');off.text=str(int(Cm(value)));el.append(off);inline.insert(1 if axis=='H' else 2,el)
 wrap=OxmlElement('wp:wrapNone');inline.insert(5,wrap)
# Exact OOXML body preservation is checked before export (presentation pages are additional).
current=[E.tostring(x) for x in body];cursor=0
for raw in original:
 while cursor<len(current) and current[cursor]!=raw:cursor+=1
 assert cursor<len(current),'SOURCE_BODY_CHANGED';cursor+=1
d.styles['Title'].font.color.rgb=RGBColor.from_string('252A2E')
for node in list(d.styles['Title'].element.xpath('.//w:pBdr')):node.getparent().remove(node)
d.core_properties.title='Система получения оплаты за выполненные работы';d.core_properties.author='На стороне подрядчика';d.core_properties.subject='Пилот оформления инструкции P1'
out=HERE/'NSP_P1_design_pilot.docx';d.save(out)
(HERE/'source.json').write_text(json.dumps({'source':str(SRC.relative_to(ROOT)),'source_docx_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'accepted_pdf':'products-storage/01-zakrytie-rabot/00-INSTRUKCIYA.pdf','accepted_pdf_sha256':hashlib.sha256((ROOT/'products-storage/01-zakrytie-rabot/00-INSTRUKCIYA.pdf').read_bytes()).hexdigest(),'source_body_xml':'UNCHANGED subsequence','export':'existing LibreOffice DOCX to PDF','status':'PILOT_ONLY_NOT_FOR_PRODUCTION'},indent=2)+'\n')
print(out)
