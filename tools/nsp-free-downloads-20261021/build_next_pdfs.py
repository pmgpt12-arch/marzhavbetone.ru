#!/usr/bin/env python3
"""Current next-step pages for the ten existing public free packs."""
from pathlib import Path
import json,os
from urllib.parse import urlsplit,urlunsplit,parse_qs
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
fonts=Path(os.environ.get('NSP_FONT_DIR','/usr/share/fonts/truetype/dejavu'))
for name,file in [('NSP','DejaVuSans.ttf'),('NSPB','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
W,H=A4;M=44;INK='#24292F';GOLD='#806238';SOFT='#4F5B65'
routes=json.loads((HERE/'routes.json').read_text());proof=[]
for route in routes:
 p=ROOT/'products-storage'/route['folder']/'99-chto-dalshe.pdf';old=PdfReader(p);urls=list(dict.fromkeys(str(ref.get_object().get('/A',{}).get('/URI')) for page in old.pages for ref in page.get('/Annots',[]) if ref.get_object().get('/A',{}).get('/URI')))
 before=Path('/tmp/nsp-free-original')/(route['folder']+'--'+p.name)
 if not before.exists():before.write_bytes(p.read_bytes())
 # Preserve the attribution query from each existing route while replacing host/path.
 links=[]
 for original,target in zip(urls,[route['product_url'],route['material_url'],'https://nastoronepodryadchika.ru/diagnostika.html']):
  u=urlsplit(target);links.append(urlunsplit((u.scheme,u.netloc,u.path,urlsplit(original).query,'')))
 assert len(links)==3
 c=canvas.Canvas(str(p),pagesize=A4,invariant=1,pageCompression=1);c.setTitle('Дальнейшие действия | '+route['material_title']);c.setAuthor('На стороне подрядчика');c.setSubject('Бесплатный набор и следующий шаг по ситуации');c.setCreator('На стороне подрядчика | free downloads revision 2026-10-21')
 def para(text,y,size=11,bold=False,color=INK):
  obj=Paragraph(escape(text),ParagraphStyle('p',fontName='NSPB' if bold else 'NSP',fontSize=size,leading=size*1.45,textColor=HexColor(color)));_,height=obj.wrap(W-2*M,900);obj.drawOn(c,M,y-height);return height
 c.setFillColor(HexColor(INK));c.rect(0,H-36,W,36,fill=1,stroke=0);c.setFillColor(HexColor('#FFFFFF'));c.setFont('NSPB',10);c.drawString(M,H-23,'НА СТОРОНЕ ПОДРЯДЧИКА');y=H-76
 y-=para('Дальнейшие действия',y,23,True)+18
 y-=para('Вы получили бесплатный набор «'+route['material_title']+'».',y,11,color=SOFT)+28
 y-=para('Комплект под вашу задачу',y,12,True,GOLD)+12
 top=y;y-=para(route['product'],y,16,True)+9;y-=para(format(route['rubles'],',').replace(',',' ')+' ₽',y,13,True)+14;y-=para('Открыть комплект →',y,11,True,GOLD);c.linkURL(links[0],(M,y-4,W-M,top+4),relative=0);y-=35
 y-=para('Разобраться в ситуации',y,12,True,GOLD)+10;top=y;y-=para('Открыть разбор и остальные бесплатные материалы по этой теме →',y,11);c.linkURL(links[1],(M,y-4,W-M,top+4),relative=0);y-=30
 y-=para('Найти решение для другой задачи',y,12,True,GOLD)+10;top=y;y-=para('Пройти диагностику ситуации на объекте →',y,11);c.linkURL(links[2],(M,y-4,W-M,top+4),relative=0);y-=40
 y-=para('Связь с проектом',y,12,True)+12
 for text,url in [('Telegram: @nastoronepodryadchika','https://t.me/nastoronepodryadchika'),('Email: nastoronepodryadchika@yandex.ru','mailto:nastoronepodryadchika@yandex.ru')]:
  top=y;y-=para(text,y,10.5,color=GOLD);c.linkURL(url,(M,y-3,W-M,top+3),relative=0);y-=10
 assert y>64,(p,y)
 c.setStrokeColor(HexColor('#D9D8D2'));c.line(M,45,W-M,45);c.setFont('NSP',8);c.setFillColor(HexColor(SOFT));c.drawString(M,29,'Редакция 21.10.2026  |  nastoronepodryadchika.ru');c.save();proof.append({'file':str(p.relative_to(ROOT)),'primary_sku':route['sku'],'links':links})
(HERE/'pdf-routes.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print('PDF_REBUILT=10')
