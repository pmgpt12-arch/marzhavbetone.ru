import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Название, цена и адрес платного комплекта — из products-config.php, ключ p2.
# Здесь они повторены текстом; при расхождении верным считается config.
# До 16.09.2026 здесь стояла цена снятой линейки и строка-заглушка вместо
# адреса: файл уходил читателю с ценой, которой в кассе нет, и без ссылки,
# по которой её можно проверить.
PAID_KEY = "p2"
PAID_NAME = "Дополнительные работы: как получить оплату"
PAID_PRICE = "19 900 ₽"
PAID_URL = "https://marzhavbetone.ru/products/p2-dopolnitelnye-raboty.html"

thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
header_font = Font(color="FFFFFF", bold=True, size=11)


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
    
    wb.save(filepath)
    print(f"  [Excel] {filepath}")


def create_word_doc(filepath, title, sections):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)
    normal.font.color.rgb = RGBColor(54, 60, 65)
    normal.paragraph_format.space_after = Pt(6)
    for name, size, color in (("Title", 17, (41, 46, 51)),
                              ("Heading 1", 11, (41, 46, 51))):
        style = doc.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(*color)
        style.paragraph_format.space_before = Pt(11)
        style.paragraph_format.space_after = Pt(5)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run("МАРЖА В БЕТОНЕ  •  marzhavbetone.ru")
    run.font.name = "Arial"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(128, 111, 78)
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(title)
    title_run.font.name = "Arial"
    title_run.font.size = Pt(17)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(41, 46, 51)
    
    for section in sections:
        if "heading" in section:
            doc.add_heading(section["heading"], level=1)
        
        if section.get("text"):
            doc.add_paragraph(section["text"])
        
        if "bullet" in section:
            for item in section["bullet"]:
                doc.add_paragraph(item, style='List Bullet')
        
        if "table" in section:
            table_data = section["table"]
            if table_data:
                table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                table.style = 'Table Grid'
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                for i, row_data in enumerate(table_data):
                    for j, cell_text in enumerate(row_data):
                        table.cell(i, j).text = str(cell_text)
                doc.add_paragraph()
        
        if "numbered" in section:
            for item in section["numbered"]:
                doc.add_paragraph(item, style='List Number')
    
    doc.save(filepath)
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


# ==================== FREE 02 ====================
def build_free_02():
    folder = os.path.join(BASE_DIR, "00-free-dopy-ne-v-podarok")
    print(f"\n[BUILD] {folder}")
    
    create_word_doc(
        os.path.join(folder, "01-checklist-do-nachala-doprabot.docx"),
        "ЧЕК-ЛИСТ: Что проверить ДО начала допработ",
        [
            {"heading": "Перед началом любых допработ ответьте на 7 вопросов",
             "numbered": [
                 "Есть ли письменное поручение заказчика на допобъем? (приказ, письмо, протокол совещания)",
                 "Подписано ли соглашение об изменении объемов / сроков / стоимости?",
                 "Есть ли письменное подтверждение цены за единицу допработ?",
                 "Фиксированы ли сроки выполнения допработ?",
                 "Понятно, кто оплачивает материалы для допработ?",
                 "Есть ли запись в журнале работ о допобъеме?",
                 "Сделаны ли фотофиксации 'до' начала допработ?"
             ]},
            {"heading": "Если ответ 'НЕТ' хотя бы на один вопрос",
             "text": "Риск неоплаты допработ резко возрастает. Рекомендуем остановиться и зафиксировать условия в письменном виде. Используйте схему фиксации поручения и форму уведомления из этого комплекта."},
            {"heading": "Следующий шаг — оформить условия",
             "bullet": [
                 "Зафиксируйте поручение и согласуйте конкретный объём работ.",
                 "Рассчитайте стоимость и отразите влияние на сроки.",
                 "Сохраните переписку, фото и документы передачи результата."
             ]},
            {"heading": "🔗 Переход к полному комплекту",
             "text": f"Комплект «{PAID_NAME}» включает: формы поручения, согласования объёма, расчёт стоимости, журнал и соглашения о цене и сроке.\n\nСтоимость: {PAID_PRICE}\nСтраница комплекта: {PAID_URL}"},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "02-shema-fiksacii-porucheniya.docx"),
        "СХЕМА: Как зафиксировать устное поручение на допработу",
        [
            {"heading": "Ситуация",
             "text": "Заказчик устно просит доделать лестничную клетку, увеличить площадь отмостки или заменить материал. Вы начинаете работу - а потом заказчик говорит: 'Я такого не говорил' или 'Это в договоре включено'."},
            {"heading": "Алгоритм фиксации (выполняйте СРАЗУ)",
             "numbered": [
                 "ПЕРЕПИСКА. Напишите в мессенджер / email: 'Подтверждаю получение поручения на [что именно]. Ожидаю письменное подтверждение сроков и цены. Без подтверждения работы не начинаю.' Сохраните скриншоты.",
                 "СЛУЖЕБНАЯ ЗАПИСКА. В тот же день составьте служебную записку руководителю объекта с описанием: кто, когда, что просил, в каком присутствии. Подпишите у руководителя.",
                 "ЖУРНАЛ РАБОТ. Внесите запись в общий журнал работ: 'Получено устное поручение от [ФИО] на [описание работ]. Ожидается письменное подтверждение.'",
                 "ФОТОФИКСАЦИЯ. Сделайте фото состояния объекта ДО начала допработ с привязкой к дате (включите геолокацию на телефоне).",
                 "УВЕДОМЛЕНИЕ. Направьте заказчику официальное письмо с уведомлением о получении поручения (форма — в этом наборе)."
             ]},
            {"heading": "Что НЕЛЬЗЯ делать",
             "bullet": [
                 "Начинать работу без письменного подтверждения стоимости",
                 "Принимать устные обещания 'потом все подпишем'",
                 "Работать 'в надежде' - надежда не является доказательством в суде",
                 "Отправлять КС-2 по допработам до подписания соглашения об изменении цены"
             ]},
            {"heading": "Когда устное поручение уже выполнено, а документов нет",
             "text": "Ситуация сложная, но не безнадежная. Соберите сохранившуюся переписку и документы по фактически выполненному объёму. Комплект помогает систематизировать материалы и оформить дальнейшее согласование."},
            {"heading": "🔗 Переход к полному комплекту",
             "text": f"Комплект «{PAID_NAME}» включает: формы поручения, уведомления, расчёт стоимости, журнал и соглашения о цене и сроке.\n\nСтоимость: {PAID_PRICE}\nСтраница комплекта: {PAID_URL}"},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "03-shablon-uvedomleniya.docx"),
        "ФОРМА УВЕДОМЛЕНИЯ о получении поручения на дополнительные работы",
        [
            {"text": "[На бланке организации]"},
            {"text": ""},
            {"text": "Исх. № _____ от '___' ___________ 20___ г."},
            {"text": ""},
            {"text": "[Должность, ФИО представителя заказчика]"},
            {"text": "[Наименование заказчика]"},
            {"text": ""},
            {"text": "От [Наименование подрядчика]"},
            {"text": ""},
            {"text": "УВЕДОМЛЕНИЕ"},
            {"text": "о получении поручения на выполнение дополнительных работ"},
            {"text": ""},
            {"text": "Уважаемый [ФИО]!"},
            {"text": ""},
            {"text": "Настоящим уведомляем, что [дата, время] в ходе [совещания / телефонного разговора / переписки] нам было сообщено о необходимости выполнения дополнительных работ в рамках договора подряда № [номер] от [дата] (далее - Договор)."},
            {"text": ""},
            {"text": "Содержание поручения:"},
            {"bullet": [
                "[Описание работ]",
                "[Локация / этаж / участок]",
                "[Предполагаемые объемы]"
            ]},
            {"text": ""},
            {"text": "В соответствии с п. [номер] Договора изменение объемов работ, сроков и цены допускается только по соглашению сторон в письменной форме."},
            {"text": ""},
            {"text": "Просим в срок до [дата] направить нам письменное подтверждение поручения с указанием:"},
            {"bullet": [
                "конкретных объемов дополнительных работ,",
                "сроков выполнения,",
                "утвержденной цены за единицу работ,",
                "порядка оплаты."
            ]},
            {"text": ""},
            {"text": "До согласования условий просим подтвердить порядок дальнейших действий. Начало работ и уведомление о возможной приостановке оформляются с учётом договора и фактических обстоятельств."},
            {"text": ""},
            {"text": "Если ответ не поступит в указанный срок, повторно согласуем с вами порядок выполнения, цену и влияние на сроки основного договора."},
            {"text": ""},
            {"text": "Генеральный директор _________________ [ФИО]"},
            {"text": "М.П."},
            {"text": ""},
            {"text": ""},
            {"heading": "Как направить уведомление",
             "text": "Направьте по согласованному в договоре каналу связи и сохраните подтверждение отправки и получения. При необходимости используйте также бумажное письмо."
            },
            {"heading": "🔗 Переход к полному комплекту",
             "text": f"Комплект «{PAID_NAME}» включает: формы фиксации поручения и объёма, расчёт стоимости, журнал и соглашения о цене и сроке.\n\nСтоимость: {PAID_PRICE}\nСтраница комплекта: {PAID_URL}"},
        ]
    )
    
    create_excel(
        os.path.join(folder, "04-reestr-doprabot.xlsx"),
        "Реестр допработ",
        headers=["№ п/п", "Дата поручения", "Описание работ", "Объем", "Ед. изм.", "Цена за ед.", "Сумма", "Дата согласования", "Статус", "Примечание"],
        rows=[
            [1, "", "Пример: Устройство отмостки", "150", "м2", "850", "=G2*D2", "", "Согласовано", ""],
            [2, "", "", "", "", "", "", "", "", ""],
            [3, "", "", "", "", "", "", "", "", ""],
            ["", "", "", "", "", "ИТОГО:", "=SUM(G2:G10)", "", "", ""],
        ],
        col_widths=[8, 14, 30, 10, 10, 12, 12, 16, 14, 20]
    )


if __name__ == "__main__":
    build_free_02()
    print("\nГОТОВО: free-02")
