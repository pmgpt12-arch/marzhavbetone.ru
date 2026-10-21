#!/usr/bin/env python3
"""Reproducible two-page public checklist; never edits buyer masters."""
import json,os
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
FONT=Path(os.environ.get('NSP_FONT_DIR','/usr/share/fonts/truetype/dejavu'))
pdfmetrics.registerFont(TTFont('NSP',str(FONT/'DejaVuSans.ttf')));pdfmetrics.registerFont(TTFont('NSP-Bold',str(FONT/'DejaVuSans-Bold.ttf')))
DATA=json.loads((HERE/'content.json').read_text());W,H=A4;M=42;INK='#24292F';SOFT='#4F5B65';GOLD='#806238';LINE='#D9D8D2';PAPER='#F7F6F2'
OUT=Path(os.environ.get('NSP_CHECKLIST_OUTPUT',str(ROOT/'downloads/checklist-zakrytiya-rabot.pdf')));OUT.parent.mkdir(parents=True,exist_ok=True)
c=canvas.Canvas(str(OUT),pagesize=A4,invariant=1,pageCompression=1)
c.setTitle('Чек-лист закрытия выполненных работ | На стороне подрядчика');c.setAuthor('На стороне подрядчика');c.setSubject('20 контрольных пунктов перед передачей результата и получением оплаты');c.setCreator('На стороне подрядчика | public checklist revision 2026-10-21');c.setKeywords('На стороне подрядчика, закрытие работ, контроль оплаты, чек-лист')
def para(text,x,y,width,size=10.2,bold=False,color=INK,leading=None):
 style=ParagraphStyle('text',fontName='NSP-Bold' if bold else 'NSP',fontSize=size,leading=leading or size*1.4,textColor=HexColor(color))
 p=Paragraph(escape(text),style);_,height=p.wrap(width,1000);p.drawOn(c,x,y-height);return height

def frame(page):
 c.setFillColor(HexColor(INK));c.rect(0,H-32,W,32,fill=1,stroke=0)
 c.setFont('NSP-Bold',9);c.setFillColor(HexColor('#FFFFFF'));c.drawString(M,H-21,'НА СТОРОНЕ ПОДРЯДЧИКА')
 c.setFillColor(HexColor('#D2B88B'));c.setFont('NSP',8);c.drawRightString(W-M,H-21,'КОНТРОЛЬ ЗАКРЫТИЯ РАБОТ')
 c.setStrokeColor(HexColor(LINE));c.line(M,38,W-M,38)
 c.setFont('NSP',8);c.setFillColor(HexColor(SOFT));c.drawString(M,24,'nastoronepodryadchika.ru');c.linkURL('https://nastoronepodryadchika.ru/',(M,20,M+150,34),relative=0)
 c.drawRightString(W-M,24,str(page)+' / 2')
frame(1);y=H-64
y-=para('Чек-лист закрытия',M,y,W-2*M,22,True)
y-=para('выполненных работ',M,y,W-2*M,22,True)+12
y-=para('20 контрольных пунктов перед передачей результата и получением оплаты',M,y,W-2*M,10.2,color=SOFT)+20
for index,section in enumerate(DATA['sections'],1):
 y-=para(str(index)+'. '+section['title'],M,y,W-2*M,12.3,True,GOLD)+9
 for item in section['items']:
  c.setStrokeColor(HexColor(GOLD));c.setLineWidth(.8);c.rect(M+2,y-10,6,6,stroke=1,fill=0)
  height=para(item,M+20,y,W-2*M-20,10.1,leading=14)
  row=max(22,height+8);c.setStrokeColor(HexColor(LINE));c.setLineWidth(.4);c.line(M,y-row+4,W-M,y-row+4);y-=row
 y-=12
assert y>55,('PAGE_ONE_OVERFLOW',y)
c.showPage();frame(2);y=H-65
y-=para('Проверка нашла проблему?',M,y,W-2*M,22,True)+10
y-=para('Выберите комплект под свою ситуацию: документы, расчёты и порядок действий для вашей компании.',M,y,W-2*M,11,color=SOFT)+22
for product in DATA['products']:
 height=103;bottom=y-height
 c.setFillColor(HexColor(PAPER));c.setStrokeColor(HexColor(LINE));c.roundRect(M,bottom,W-2*M,height,6,fill=1,stroke=1)
 cy=y-13;cy-=para(product['situation'],M+14,cy,W-2*M-28,9.5,True,GOLD)+6
 cy-=para(product['name'],M+14,cy,W-2*M-28,11.1,True,leading=14.3)+7
 c.setFillColor(HexColor(SOFT));c.setFont('NSP',9.5);c.drawString(M+14,bottom+13,str(product['files'])+' файлов  |  '+format(product['rubles'],',').replace(',',' ')+' ₽')
 c.setFont('NSP-Bold',9.5);c.setFillColor(HexColor(GOLD));c.drawRightString(W-M-14,bottom+13,'Открыть комплект →');c.linkURL(product['url'],(M,bottom,W-M,y),relative=0)
 assert cy>bottom+25,('CARD_OVERFLOW',product['sku'],cy,bottom);y=bottom-12
y-=6
y-=para('Каталог и связь с проектом',M,y,W-2*M,13,True)+12
for label,url in DATA['contacts']:
 h=para(label,M,y,W-2*M,10.1,color=GOLD);c.linkURL(url,(M,y-h-2,W-M,y+2),relative=0);y-=h+8
y-=7
y-=para('Отмечайте проверенные пункты. Если пункт не подтверждён, назначьте ответственного и зафиксируйте срок устранения. Документы применяйте с учётом договора и требований к вашему объекту.',M,y,W-2*M,9.3,color=SOFT)
assert y>55,('PAGE_TWO_OVERFLOW',y)
c.showPage();c.save();print(OUT)
