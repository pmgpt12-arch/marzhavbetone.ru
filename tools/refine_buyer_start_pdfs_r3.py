#!/usr/bin/env python3
"""Two buyer instruction PDFs from explicit, reviewed source text."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import subprocess
import os
OUT=Path('/tmp/mb-r3/work')
regular=subprocess.check_output(['fc-match','-f','%{file}','Arial'],text=True).strip()
bold=subprocess.check_output(['fc-match','-f','%{file}','Arial:style=Bold'],text=True).strip()
if not regular.lower().endswith('.ttf') or not bold.lower().endswith('.ttf'):
 fonts=Path(os.environ.get('CODEX_PRIMARY_RUNTIME_ROOT','/opt/codex/runtimes/codex-primary-runtime'))/'dependencies/native/libreoffice-headless/libreoffice/share/fonts/truetype'
 regular=str(fonts/'LiberationSans-Regular.ttf');bold=str(fonts/'LiberationSans-Bold.ttf')
pdfmetrics.registerFont(TTFont('Business',regular));pdfmetrics.registerFont(TTFont('BusinessBold',bold))
styles={
'title':ParagraphStyle('title',fontName='BusinessBold',fontSize=16,leading=19,spaceAfter=10,textColor=colors.HexColor('#262F37')),
'head':ParagraphStyle('head',fontName='BusinessBold',fontSize=10.5,leading=13,spaceBefore=8,spaceAfter=5,textColor=colors.HexColor('#8E6F32')),
'body':ParagraphStyle('body',fontName='Business',fontSize=9.5,leading=12.5,spaceAfter=5),
'cell':ParagraphStyle('cell',fontName='Business',fontSize=8.1,leading=10.1),
}
def P(t,kind='body'):return Paragraph(t,styles[kind])
def table(rows):
 t=Table([[P(a,'cell'),P(b,'cell')] for a,b in rows],colWidths=[88*mm,86*mm],hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F2EFE9')),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#D9D9D9')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
 return t
def save(sku,story):
 def footer(c,d):
  c.setFont('Business',8);c.setFillColor(colors.HexColor('#62666A'));c.drawString(18*mm,12*mm,'НА СТОРОНЕ ПОДРЯДЧИКА  /  '+sku)
 SimpleDocTemplate(str(OUT/sku/'00-START-HERE.pdf'),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=16*mm,bottomMargin=20*mm,title='Порядок применения комплекта',author='На стороне подрядчика').build(story,onFirstPage=footer,onLaterPages=footer)
story=[P('Подготовка ответа на претензию заказчика','title'),P('Результат','head'),P('Мотивированная позиция по каждому требованию: основание, сумма, подтверждающие документы, адресат, срок и доказательства направления ответа.'),P('Порядок действий','head')]
for t in [
'1. Зарегистрируйте претензию, дату и способ получения. Проверьте предусмотренные договором срок и адрес ответа, полномочия подписанта.',
'2. В карте 01 выделите самостоятельные требования. По каждой позиции укажите основание, сумму, проверенный факт, расчёт и подтверждающий документ.',
'3. По порядку 02 подготовьте договор, акты, исполнительную документацию, переписку, материалы осмотра и доказательства передачи. Недостающие документы запросите отдельно.',
'4. Для ответа стороне договора используйте форму 03, при гарантийном дефекте — 04. При прямом требовании иного лица проверьте основание обращения и подготовьте формы 05 и 06. Применимые правовые доводы приведены в файле 07.',
'5. Заполните реквизиты, исключите неподтверждённые утверждения и неприменимые варианты. Сверьте приложения и контррасчёт. Направьте подписанный ответ и сохраните подтверждения отправки и получения.'
]:story.append(P(t))
story+=[P('Состав комплекта','head'),table([('Файл','Назначение'),('01-karta-pretenzii.docx','Учёт требований, доказательств и расчётов.'),('02-poryadok-otveta.docx','Порядок проверки и направления ответа.'),('03-otvet-na-pretenziyu.docx','Мотивированный ответ стороне договора.'),('04-otvet-na-garantiynuyu-pretenziyu.docx','Ответ по гарантийному дефекту и организация осмотра.'),('05-otvet-na-pryamoe-trebovanie.docx','Ответ предъявителю, с которым отсутствует прямой договор.'),('06-uvedomlenie-kontragentu.docx','Уведомление стороны договора о прямом требовании.'),('07-vstavnye-bloki.docx','Формулировки возражений по отдельным основаниям.')]),P('Контроль перед подписанием','head'),P('Сопоставьте ответ с претензией, договором и приложениями. По обстоятельствам, требующим проверки, укажите запрошенные документы и порядок осмотра. Сохраните подписанный экземпляр, опись и доказательства направления.')]
save('P10',story)
story=[P('Проверка сметы и выявление непокрытых затрат','title'),P('Результат','head'),P('Перечень непокрытых расходов, оценка их влияния на плановую прибыль и согласованная цена с распределением обязанностей до подписания договора.'),P('Порядок действий','head')]
for t in ['1. Проверьте состав и исходные данные сметы по алгоритму 61 и проверочному листу 62.','2. Заполните реестр 63. Оцените непокрытую часть, исключив расходы, учтённые расценками и начислениями. Используйте памятки 66–68.','3. По словарю 60 заполните запрос 64 и приложение с расчётом и подтверждающими документами.','4. Согласуйте изменения протоколом 65 и включите его в состав договорных документов.','5. Сопоставьте оставшиеся непокрытые расходы с плановой прибылью. Зафиксируйте решение уполномоченного руководителя до подписания цены.']:story.append(P(t))
story+=[P('Состав комплекта','head'),table([('Файл','Назначение'),('60-slovar-poley-smeta.docx','Реквизиты и источники заполнения форм.'),('61-algoritm-proverki-smety.docx','Порядок проверки сметы до подписания.'),('62-chek-list-vypadayushchih-zatrat.docx','Проверочный лист затрат по объекту.'),('63-reestr-zatrat-po-obektu.xlsx','Учёт покрытия, оценок и согласований.'),('64-zapros-o-vklyuchenii-zatrat.docx','Запрос о включении или уточнении затрат.'),('65-protokol-raznoglasiy-po-smete.docx','Согласованные изменения сметы.'),('66-pamyatka-nakladnye-i-smetnaya-pribyl.docx','Проверка накладных расходов и сметной прибыли.'),('67-pamyatka-zimnee-udorozhanie-i-vzis.docx','Проверка зимних затрат и временных сооружений.'),('68-pamyatka-musor-transport-nepredvidennye.docx','Проверка отходов, транспорта и непредвиденных затрат.')]),P('Контроль решения','head'),P('Проверьте все применимые расходы и документы покрытия. Нулевая оценка подтверждает отсутствие непокрытого остатка; незаполненная оценка требует уточнения. Сохраните исходную и согласованную смету, расчёты и переписку.')]
save('P13',story)
print('P10/P13 instruction PDFs regenerated')
