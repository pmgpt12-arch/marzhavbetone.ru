"""Собрать проверочные карты P2 в PDF."""
from __future__ import annotations

import argparse
from pathlib import Path
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
pdfmetrics.registerFont(TTFont('DejaVu',FONT))
pdfmetrics.registerFont(TTFont('DejaVuBold',BOLD))
INK=HexColor('#263039'); GOLD=HexColor('#8E6F32'); PALE=HexColor('#E1E3E4')

def wrapped(text: str, width: float, size: float, name: str='DejaVu') -> list[str]:
    words=text.split(); lines=[]; line=''
    for word in words:
        trial=f'{line} {word}'.strip()
        if pdfmetrics.stringWidth(trial,name,size)>width and line:
            lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    return lines

class Page:
    def __init__(self,path:Path,title:str,lead:str):
        self.c=canvas.Canvas(str(path),pagesize=A4)
        self.w,self.h=A4;self.y=self.h-55;self.page=1;self.title=title
        self.c.setTitle(title)
        self.line(title,16,'DejaVuBold',leading=22)
        self.line(lead,9.2,'DejaVu',leading=15)
        self.y-=9
    def new_page(self):
        self.footer();self.c.showPage();self.page+=1;self.y=self.h-55
        self.line(self.title,12,'DejaVuBold',leading=18)
    def footer(self):
        self.c.setStrokeColor(PALE);self.c.line(45,42,self.w-45,42)
        self.c.setFont('DejaVu',8);self.c.setFillColor(INK)
        self.c.drawString(45,28,'МАРЖА В БЕТОНЕ  /  ДОПОЛНИТЕЛЬНЫЕ РАБОТЫ')
        self.c.drawRightString(self.w-45,28,str(self.page))
    def ensure(self,height):
        if self.y-height<65:self.new_page()
    def line(self,text,size=9.5,name='DejaVu',leading=16,indent=0,color=INK):
        lines=wrapped(text,self.w-90-indent,size,name)
        self.ensure(len(lines)*leading)
        self.c.setFillColor(color);self.c.setFont(name,size)
        for line in lines:
            self.c.drawString(45+indent,self.y,line);self.y-=leading
    def section(self,title):
        self.y-=10;self.ensure(42)
        self.line(title,11,'DejaVuBold',leading=20,color=GOLD)
    def item(self,n,title,desc):
        lines=wrapped(desc,self.w-45-88,9)
        height=26+13*len(lines)
        self.ensure(height)
        self.c.setStrokeColor(PALE);self.c.line(45,self.y+7,self.w-45,self.y+7)
        self.c.setFillColor(GOLD);self.c.setFont('DejaVuBold',10);self.c.drawString(45,self.y-9,f'{n:02}')
        self.c.setStrokeColor(INK);self.c.rect(68,self.y-10,9,9)
        self.c.setFillColor(INK);self.c.setFont('DejaVuBold',9.3);self.c.drawString(88,self.y-9,title)
        yy=self.y-23;self.c.setFont('DejaVu',9)
        for line in lines:
            self.c.drawString(88,yy,line);yy-=13
        self.y-=height
    def finish(self):
        self.footer();self.c.save()

def photos(path:Path):
    p=Page(path,'Фотофиксация дополнительных работ','Карточка к объекту [___], договору № [___], участку [___] и позиции формы 02 № [___]. Для каждой работы сохраните исходные файлы и связь с журналом 08.')
    p.section('До начала и во время работ')
    for n,title,desc in [
        (1,'Общий план','Показан объект, помещение, участок или захватка и устойчивый ориентир.'),
        (2,'Границы','Средний план показывает начало и конец объёма, смежные конструкции и привязку к чертежу.'),
        (3,'Причина','Зафиксировано обнаруженное обстоятельство до изменения или закрытия конструкции.'),
        (4,'Масштаб','Измерительный инструмент и единицы видны на кадре; есть обмерная ведомость или схема.'),
        (5,'Ход работ','Снимки по этапам позволяют связать материал, операцию и фактический объём.'),
        (6,'Скрываемое','Снимки сделаны до закрытия участка; указана связь с актом 04 и датой осмотра.'),
    ]:p.item(n,title,desc)
    p.section('После выполнения и перед передачей')
    for n,title,desc in [
        (7,'Итоговый вид','Показаны результат, границы и детали, значимые для приёмки.'),
        (8,'Идентификация','Файлы названы по объекту, месту, работе и дате; есть реестр соответствия позициям.'),
        (9,'Оригиналы','Исходные файлы с метаданными сохранены отдельно от копий для переписки.'),
        (10,'Сверка','Для каждой позиции формы 02 указаны файлы фото, запись журнала 08, акт и чертёж.'),
        (11,'Передача','Перечень и ссылку направили уполномоченному адресату; дата и подтверждение доставки сохранены.'),
    ]:p.item(n,title,desc)
    p.section('Реестр передачи')
    p.line('Носитель / папка [___]    Диапазон файлов [___]    Передано [___]    Получатель [___]    Подтверждение [___]',9)
    p.finish()

def algorithm(path:Path):
    p=Page(path,'Алгоритм дополнительных работ','Выберите один маршрут и связывайте каждую позицию с исходным договором, решением заказчика, расчётом, фактом и закрывающими документами.')
    p.section('Маршрут А  Работы ещё не начаты')
    for n,title,desc in [
        (1,'Определить отличие','Сверьте договор, техническую документацию, смету и границы участка; запишите позицию отдельно.'),
        (2,'Зафиксировать источник','Получите письменное поручение 01 или зафиксируйте обнаружение и направьте уведомление 03.'),
        (3,'Согласовать объём','Заполните форму 02, ведомость, схему и подтверждения. Проверьте полномочия подписанта.'),
        (4,'Рассчитать условия','Расчёт 07 и изменение графика 05; подпишите соглашения 11 и 12 по меняющимся условиям.'),
        (5,'Начать и вести учёт','Записывайте работы в журнал 08, сохраняйте фото 09, освидетельствуйте скрываемое актом 04.'),
        (6,'Закрыть и сверить оплату','Передайте приёмочные документы по договору, зафиксируйте включение в КС-2 и поступление оплаты в журнале.'),
    ]:p.item(n,title,desc)
    p.section('Маршрут Б  Работы уже выполнены')
    for n,title,desc in [
        (7,'Собрать факт','Запишите реальные даты, инициатора, его полномочия, переписку, журнал, фото и акты.'),
        (8,'Отделить объём','Сверьте дополнительные позиции с договором и проектом; восстановите границы и обмеры.'),
        (9,'Сообщить заказчику','Направьте уведомление 03 текущей датой, приложите доказательства и запросите решение по форме 02.'),
        (10,'Согласовать расчёт','Представьте цену в 07, оформите соглашение 11 и при изменении графика соглашение 12.'),
        (11,'Завершить учёт','Свяжите согласованные позиции с приёмкой, КС-2, журналом 08 и подтверждением оплаты.'),
    ]:p.item(n,title,desc)
    p.section('Если ответ отсутствует или работы остановлены')
    p.line('Сохраните уведомление и доказательство доставки, зафиксируйте затронутые работы и меры по сохранности. Используйте письмо 06 с датами, ссылкой на договорный срок ответа и журналом 08. Не подменяйте фактические даты задними числами.',9)
    p.finish()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    photos(args.output_dir/'09-checklist-fotofiksacii.pdf')
    algorithm(args.output_dir/'10-algoritm-doprabot.pdf')
