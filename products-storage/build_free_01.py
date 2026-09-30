import io
import os
import re
import zipfile
from datetime import datetime, timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Следующий шаг после бесплатного набора — «Система получения оплаты за
# выполненные работы» (S1). По решению владельца (S1-EDITION-SKU-DECISION-MEMO,
# §7) она занимает ключ p1 и адрес /products/p1-oplata-po-ks2.html; T1 снимается
# с продажи. Цены здесь нет намеренно: скачанный файл не обновляется, а цена
# меняется. Состав S1 перечислен только тем, что в ней есть по кандидату
# (tools/candidates/s1-oplata-za-raboty/00-START-HERE.txt): маршрут
# заканчивается подготовкой обращения в арбитражный суд. Исполнительного
# производства, ФССП и «стратегий взыскания» в S1 нет — и в тексте их нет.
NEXT_KEY = "p1"
NEXT_NAME = "Система получения оплаты за выполненные работы"
NEXT_URL = "https://marzhavbetone.ru/products/p1-oplata-po-ks2.html"
# NEXT_NAME в предложном падеже — отдельной строкой, склонять f-строкой нельзя
NEXT_TEXT = (
    "Если КС подписаны, срок оплаты по договору истёк, а оплаты нет, "
    "следующий шаг описан в «Системе получения оплаты за выполненные работы»: "
    "фиксация задолженности, переговоры и перенос срока, уведомление и "
    "претензия, расчёт процентов, подготовка обращения в арбитражный суд. "
    "Это рабочий порядок действий и шаблоны, а не юридическая консультация "
    "и не гарантия оплаты."
)

# Лист «Что делать дальше» (99-chto-dalshe.pdf). До 28.09.2026 он собирался во
# внешнем репозитории и первым маршрутом вёл на T1; теперь его источник здесь.
# utm_content=dengi-primary сохранён, чтобы ряд сопоставлялся с историей.
UTM = "utm_source=site&utm_medium=magnet&utm_campaign=neoplata"
NEXT_STEPS = [
    ("1. Срок оплаты истёк, а денег нет — порядок действий по шагам",
     NEXT_TEXT,
     f"{NEXT_URL}?{UTM}&utm_content=dengi-primary"),
    ("2. Разобраться подробнее — разбор ситуации и остальные файлы набора",
     "",
     f"https://marzhavbetone.ru/materialy/dengi.html?{UTM}&utm_content=dengi-secondary"),
    ("3. Если на объекте застряло другое — определить, что именно",
     "",
     f"https://marzhavbetone.ru/diagnostika.html?{UTM}&utm_content=dengi-fallback"),
]
FREE_NAME = "КС подписаны, денег нет: первые 7 проверок"
NEXT_STEPS_VERSION = "версия 1.1.0 · источник от 2026-09-28"

# Одинаковый вход — одинаковые байты: архив dengi.zip пересобирается из этих
# файлов, и повторный прогон не должен давать diff без изменения текста.
FIXED_DATE = datetime(2026, 9, 28, tzinfo=timezone.utc)
ZIP_DATE = (2026, 9, 28, 0, 0, 0)

thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
header_font = Font(color="FFFFFF", bold=True, size=11)


def save_reproducible(save, filepath):
    """Сохраняет .docx/.xlsx с одинаковыми байтами при одинаковом содержимом.

    python-docx и openpyxl пишут в zip текущее время — и в даты элементов
    архива, и в свойства документа. Здесь оба времени фиксированы."""
    buffer = io.BytesIO()
    save(buffer)
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as source, \
            zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            fixed = zipfile.ZipInfo(item.filename, date_time=ZIP_DATE)
            fixed.compress_type = zipfile.ZIP_DEFLATED
            fixed.external_attr = 0o644 << 16
            data = source.read(item.filename)
            if item.filename == "docProps/core.xml":
                # openpyxl ставит modified = «сейчас» при каждом save()
                data = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*",
                              rb"\g<1>" + FIXED_DATE.strftime("%Y-%m-%dT%H:%M:%SZ").encode(),
                              data)
            target.writestr(fixed, data)


def create_excel(filepath, sheet_name="Лист1", headers=None, rows=None, col_widths=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    
    if headers:
        ws.append(headers)
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
    
    if rows:
        for r in rows:
            ws.append(r)
            row_num = ws.max_row
            for col_idx in range(1, len(r) + 1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="top", wrap_text=True)
    
    if col_widths:
        for idx, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(idx)].width = w
    
    wb.properties.creator = "Маржа в бетоне"
    wb.properties.created = FIXED_DATE.replace(tzinfo=None)
    wb.properties.modified = FIXED_DATE.replace(tzinfo=None)
    save_reproducible(wb.save, filepath)
    print(f"  [Excel] {filepath}")


def create_word_doc(filepath, title, sections):
    doc = Document()
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    
    for section in sections:
        if "heading" in section:
            doc.add_heading(section["heading"], level=1)
        
        if "text" in section:
            doc.add_paragraph(section["text"])
        
        if "bullet" in section:
            for item in section["bullet"]:
                doc.add_paragraph(item, style='List Bullet')
        
        if "table" in section:
            table_data = section["table"]
            if table_data:
                table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                table.style = 'Table Grid'
                for i, row_data in enumerate(table_data):
                    for j, cell_text in enumerate(row_data):
                        table.cell(i, j).text = str(cell_text)
                doc.add_paragraph()
        
        if "numbered" in section:
            for item in section["numbered"]:
                doc.add_paragraph(item, style='List Number')
    
    core = doc.core_properties
    core.author = core.last_modified_by = "Маржа в бетоне"
    core.created = core.modified = FIXED_DATE
    core.revision = 1
    save_reproducible(doc.save, filepath)
    print(f"  [Word]  {filepath}")


def create_pdf_simple(filepath, title, lines):
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 2*cm, title)
    
    c.setFont("Helvetica", 11)
    y = height - 3.5*cm
    for line in lines:
        if y < 2*cm:
            c.showPage()
            y = height - 2*cm
            c.setFont("Helvetica", 11)
        c.drawString(2*cm, y, line)
        y -= 0.6*cm
    
    c.save()
    print(f"  [PDF]   {filepath}")


FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def create_next_steps_pdf(filepath):
    """Одна страница «Что делать дальше»: не больше трёх маршрутов."""
    from reportlab.lib.utils import simpleSplit

    for name, file in (("DejaVuSans", "DejaVuSans.ttf"),
                       ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf")):
        path = os.path.join(FONT_DIR, file)
        if not os.path.exists(path):
            raise SystemExit(f"нет шрифта {path}: кириллица в PDF без него не выводится")
        pdfmetrics.registerFont(TTFont(name, path))

    width, height = A4
    left = 2.2 * cm
    text_width = width - 2 * left
    c = canvas.Canvas(filepath, pagesize=A4, invariant=1)
    c.setTitle("Что делать дальше")
    c.setAuthor("Маржа в бетоне")
    c.setSubject(FREE_NAME)
    y = height - 2.4 * cm

    def paragraph(text, font="DejaVuSans", size=10.5, leading=15, colour=(0, 0, 0)):
        nonlocal y
        c.setFont(font, size)
        c.setFillColorRGB(*colour)
        for line in simpleSplit(text, font, size, text_width):
            c.drawString(left, y, line)
            y -= leading

    def link(url, size=9, leading=13):
        # Адрес без пробелов simpleSplit не переносит — режем по символам,
        # и каждая строка остаётся кликабельной целиком.
        nonlocal y
        c.setFont("DejaVuSans", size)
        c.setFillColorRGB(0.13, 0.33, 0.62)
        line = ""
        lines = []
        for char in url:
            if pdfmetrics.stringWidth(line + char, "DejaVuSans", size) > text_width:
                lines.append(line)
                line = ""
            line += char
        lines.append(line)
        for part in lines:
            c.drawString(left, y, part)
            c.linkURL(url, (left, y - 3, left + pdfmetrics.stringWidth(part, "DejaVuSans", size), y + size),
                      relative=0)
            y -= leading

    paragraph("Что делать дальше", "DejaVuSans-Bold", 18, 26)
    y -= 4
    paragraph(f"Вы скачали набор «{FREE_NAME}». Ниже — куда идти, если ситуация уже "
              "перешла в следующую стадию. Больше трёх маршрутов здесь не бывает: их и есть три.")
    y -= 10
    for label, description, url in NEXT_STEPS:
        paragraph(label, "DejaVuSans-Bold", 11, 16)
        if description:
            paragraph(description, size=10, leading=14)
        link(url)
        y -= 12
    y -= 4
    paragraph("Материалы — редактируемые шаблоны. Их нужно адаптировать под ваш договор и "
              "обстоятельства объекта; они не заменяют юридическую консультацию.",
              size=9.5, leading=13, colour=(0.3, 0.3, 0.3))

    c.setFont("DejaVuSans", 8)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawString(left, 1.6 * cm, f"{FREE_NAME} · {NEXT_STEPS_VERSION} · marzhavbetone.ru")
    c.showPage()
    c.save()
    print(f"  [PDF]   {filepath}")


# ==================== FREE 01 ====================
def build_free_01():
    folder = os.path.join(BASE_DIR, "00-free-ks-podpisany-deneg-net")
    print(f"\n[BUILD] {folder}")
    
    create_word_doc(
        os.path.join(folder, "01-algoritm-pervichnoy-proverki.docx"),
        "АЛГОРИТМ ПЕРВИЧНОЙ ПРОВЕРКИ: КС подписаны, денег нет",
        [
            {"heading": "Шаг 1. Проверьте срок оплаты по договору",
             "numbered": [
                 "Откройте раздел 'Условия оплаты' в договоре подряда.",
                 "Определите: аванс / поэтапно / по факту.",
                 "Посчитайте крайний срок оплаты (рабочие или календарные дни - важно!)."
             ]},
            {"heading": "Шаг 2. Проверьте подписание КС-2 / КС-3",
             "numbered": [
                 "Есть ли подписи обеих сторон на КС-2?",
                 "Есть ли подписи на КС-3?",
                 "Совпадают ли даты подписания с фактом выполнения работ?",
                 "Если КС не подписана - это другая ситуация (см. раздел «Следующий шаг» в конце документа)."
             ]},
            {"heading": "Шаг 3. Проверьте срок исковой давности",
             "text": "По договору подряда - 3 года с даты, когда должна была быть произведена оплата. Если срок близок к истечению - срочно направьте претензию."},
            {"heading": "Шаг 4. Соберите доказательства выполнения работ",
             "bullet": [
                 "Акты скрытых работ (КС-11, АОСР)",
                 "Журналы работ",
                 "Фото/видео фиксация объемов",
                 "Переписка с заказчиком (email, Telegram, WhatsApp)",
                 "Протоколы совещаний"
             ]},
            {"heading": "Шаг 5. Проверьте наличие претензионного порядка",
             "text": "В 90% договоров подряда претензионный порядок обязателен. Без претензии суд откажет. Срок рассмотрения претензии - обычно 10-30 рабочих дней."},
            {"heading": "Шаг 6. Рассчитайте неустойку",
             "text": "Проверьте размер пени по договору. Если не указан - применяется ключевая ставка ЦБ (расчет в калькуляторе)."},
            {"heading": "Шаг 7. Подготовьте письмо-напоминание",
             "text": "Используйте шаблон письма из этого комплекта. Фиксируйте все коммуникации в письменном виде."},
            {"heading": "⚠️ Что этот материал НЕ закрывает",
             "bullet": [
                 "Составление полноценной претензии с юридическим обоснованием",
                 "Подготовка искового заявления и представление интересов в суде",
                 "Анализ сложных случаев: банкротство заказчика, субподрядные цепочки, залоги"
             ]},
            {"heading": "🔗 Следующий шаг",
             "text": f"{NEXT_TEXT}\n\nСтраница: {NEXT_URL}"},
        ]
    )
    
    create_excel(
        os.path.join(folder, "02-kalkulyator-sroka-oplaty.xlsx"),
        "Калькулятор срока оплаты",
        headers=["Параметр", "Значение", "Примечание"],
        rows=[
            ["Дата подписания КС-2", "", "Введите дату"],
            ["Дата подписания КС-3", "", "Введите дату"],
            ["Срок оплаты по договору (дней)", "", "Например: 15 рабочих дней"],
            ["Тип срока", "", "рабочие / календарные"],
            ["", "", ""],
            ["Крайний срок оплаты", "=IF(AND(B2<>\"\",B3<>\"\",B4<>\"\",B5<>\"\"),IF(B5=\"рабочие\",WORKDAY(B3,B4),IF(B5=\"календарные\",B3+B4,\"укажите тип срока\")),\"заполните данные\")", "Автоматический расчет"],
            ["Просрочка (дней)", "=IF(ISNUMBER(B7),MAX(0,TODAY()-B7),0)", "Автоматический расчет"],
            ["", "", ""],
            ["Ставка пени по договору (%/день)", "", "Например: 0,1%"],
            ["Сумма по КС-2 (руб.)", "", "Введите сумму"],
            ["Начисленные пени", "=IF(AND(ISNUMBER(B10),ISNUMBER(B11),ISNUMBER(B8)),B11*B10*B8/100,0)", "Автоматический расчет"],
        ],
        col_widths=[35, 25, 40]
    )
    
    create_word_doc(
        os.path.join(folder, "03-perechen-dokumentov.docx"),
        "ПЕРЕЧЕНЬ НЕОБХОДИМЫХ ДОКУМЕНТОВ для претензионной работы",
        [
            {"heading": "Обязательные документы",
             "numbered": [
                 "Договор подряда (все приложения, допсоглашения)",
                 "КС-2 (форма по ОКУД 0322001) - подписанная обеими сторонами",
                 "КС-3 (форма по ОКУД 0322002) - подписанная обеими сторонами",
                 "Журнал учета выполненных работ (формы КС-6, КС-6а)",
                 "Акты скрытых работ (КС-11, АОСР) - если применимо",
                 "Ведомость ресурсов (КС-4) - если применимо"
             ]},
            {"heading": "Дополнительные документы (усиливают позицию)",
             "bullet": [
                 "Календарный план производства работ",
                 "Журнал производства работ",
                 "Фото/видео материалы выполнения работ",
                 "Протоколы совещаний с заказчиком",
                 "Переписка (email, мессенджеры) - экспорт с метаданными",
                 "Письма заказчику с подтверждением доставки (заказные, email-уведомления)",
                 "Служебные записки внутри организации"
             ]},
            {"heading": "Если работы выполнены, но КС не подписана",
             "text": "В этом случае нужны дополнительные документы: акты внеплановой проверки, свидетельские показания, экспертная оценка объемов. Это выходит за рамки бесплатного материала - см. полный комплект."},
            {"heading": "Совет",
             "text": "Собирайте документы ПОСТЕПЕННО, в процессе работы. Не откладывайте на 'потом' - когда конфликт начался, заказчик может перестать отвечать и предоставлять документы."},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "04-shablon-pisma.docx"),
        "ШАБЛОН ПИСЬМА ЗАКАЗЧИКУ о задержке оплаты",
        [
            {"text": "[На бланке организации]"},
            {"text": ""},
            {"text": "Исх. № _____ от '___' ___________ 20___ г."},
            {"text": ""},
            {"text": "Генеральному директору"},
            {"text": "[Наименование заказчика]"},
            {"text": "[ФИО руководителя]"},
            {"text": ""},
            {"text": "От [Наименование подрядчика]"},
            {"text": ""},
            {"text": "УВЕДОМЛЕНИЕ"},
            {"text": "о нарушении срока оплаты по договору подряда № [номер] от [дата]"},
            {"text": ""},
            {"text": "Уважаемый [ФИО]!"},
            {"text": ""},
            {"text": "Настоящим сообщаем, что в соответствии с п. [номер] договора подряда № [номер] от [дата] (далее - Договор) заказчик обязан произвести оплату выполненных работ в срок [указать срок] с момента подписания формы КС-2."},
            {"text": ""},
            {"text": "Форма КС-2 № [номер] от [дата] подписана обеими сторонами [дата подписания заказчиком]. Крайний срок оплаты наступил [дата]."},
            {"text": ""},
            {"text": "По состоянию на '___' ___________ 20___ г. оплата не поступила. Просрочка составляет [количество] дней."},
            {"text": ""},
            {"text": "Согласно п. [номер] Договора, в случае нарушения срока оплаты заказчик уплачивает пени в размере [процент]% от суммы просроченной оплаты за каждый день просрочки. На текущую дату начисленные пени составляют [сумма] руб."},
            {"text": ""},
            {"text": "Просим в срок до [дата] произвести оплату в размере [сумма по КС-2] руб. и начисленных пени [сумма пеней] руб., всего [итог] руб."},
            {"text": ""},
            {"text": "В случае непоступления оплаты в указанный срок оставляем за собой право обратиться в суд с исковым требованием о взыскании основного долга, пеней, процентов по ст. 395 ГК РФ и судебных расходов."},
            {"text": ""},
            {"text": "Приложения:"},
            {"bullet": [
                "Копия договора подряда № ___ от ___ (л. __)",
                "Копия формы КС-2 № ___ от ___ (л. __)",
                "Копия формы КС-3 № ___ от ___ (л. __)",
                "Расчет пени (л. __)."
            ]},
            {"text": ""},
            {"text": "Генеральный директор _________________ [ФИО]"},
            {"text": "М.П."},
            {"text": ""},
            {"text": ""},
            {"text": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"},
            {"heading": "💡 Как использовать этот шаблон",
             "numbered": [
                 "Заполните все поля в квадратных скобках.",
                 "Проверьте соответствие сроков и сумм с договором и КС-2.",
                 "Отправьте заказным письмом с уведомлением о вручении и описью вложения.",
                 "Сохраните квитанцию об отправке - это доказательство направления.",
                 "Если заказчик не отвечает в течение 30 дней - готовьте претензию (см. раздел «Следующий шаг» ниже)."
             ]},
            {"heading": "🔗 Следующий шаг",
             "text": f"Этот шаблон - только первый шаг. {NEXT_TEXT}\n\nСтраница: {NEXT_URL}"},
        ]
    )

    create_next_steps_pdf(os.path.join(folder, "99-chto-dalshe.pdf"))


if __name__ == "__main__":
    build_free_01()
    print("\nГОТОВО: free-01")
