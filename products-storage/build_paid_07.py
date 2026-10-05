import io
import hashlib
from pathlib import Path
import os
import re
import zipfile

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
header_font = Font(color="FFFFFF", bold=True, size=11)

# Excel не принимает имя листа длиннее 31 символа: Calc при сохранении его
# обрезает, Excel предлагает «восстановить» книгу.
ПРЕДЕЛ_ИМЕНИ_ЛИСТА = 31

# openpyxl пишет в книгу время сборки (docProps/core.xml и даты записей
# zip), поэтому две сборки подряд различались побайтно. Время заменяется
# постоянным — одинаковый исходник даёт одинаковый файл.
ДАТА_СБОРКИ = (2026, 9, 28, 0, 0, 0)
_W3CDTF = "%04d-%02d-%02dT%02d:%02d:%02dZ" % ДАТА_СБОРКИ
_ВРЕМЯ_В_CORE = re.compile(
    r"(<dcterms:(?:created|modified)\b[^>]*>)[^<]*(</dcterms:(?:created|modified)>)")


def save_workbook(wb, filepath):
    """Сохраняет книгу без меток времени сборки."""
    for ws in wb.worksheets:
        if len(ws.title) > ПРЕДЕЛ_ИМЕНИ_ЛИСТА:
            raise ValueError(
                f"{os.path.basename(filepath)}: имя листа «{ws.title}» — "
                f"{len(ws.title)} символов, Excel допускает {ПРЕДЕЛ_ИМЕНИ_ЛИСТА}")
    buf = io.BytesIO()
    wb.save(buf)
    with zipfile.ZipFile(buf) as src, \
            zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "docProps/core.xml":
                data = _ВРЕМЯ_В_CORE.sub(
                    lambda m: m.group(1) + _W3CDTF + m.group(2),
                    data.decode("utf-8")).encode("utf-8")
            info = zipfile.ZipInfo(item.filename, date_time=ДАТА_СБОРКИ)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            dst.writestr(info, data)



# Owner approved these exact native Excel layouts on 05.10.2026. Reading
# with openpyxl is semantic verification only; native bytes are never saved
# through it. A future formula change must update/reapprove the template.
P5_OWNER_TEMPLATES = Path(BASE_DIR).parent / "tools" / "templates" / "p5-owner-excel"
P5_OWNER_SHA256 = {
    "04-raschet-ubytkov.xlsx": "20165a12e04cf37dee98ac8d528cb78026d5a342e24231f69a09bd70c6bedc31",
    "05-reestr-uderzhaniy.xlsx": "db0d99f745e460b29654c3079483103e1bcc39d65ad9e8c36d002288ed5df9ae",
}


def write_owner_p5_workbook(generated, filepath):
    """Publish owner OOXML only if current generated business cells agree."""
    output = Path(filepath)
    native = (P5_OWNER_TEMPLATES / output.name).read_bytes()
    if hashlib.sha256(native).hexdigest() != P5_OWNER_SHA256[output.name]:
        raise ValueError("P5 owner template hash mismatch: " + output.name)
    approved = openpyxl.load_workbook(io.BytesIO(native))
    if generated.sheetnames != approved.sheetnames:
        raise ValueError("P5 owner sheet mismatch: " + output.name)
    for name in generated.sheetnames:
        actual, expected = generated[name], approved[name]
        for coordinate in set(actual._cells) | set(expected._cells):
            a, e = actual.cell(*coordinate), expected.cell(*coordinate)
            if (None if a.value == "" else a.value) != (None if e.value == "" else e.value):
                raise ValueError(f"P5 owner semantic mismatch: {output.name}/{name}!{a.coordinate}")
        if set(map(str, actual.merged_cells.ranges)) != set(map(str, expected.merged_cells.ranges)):
            raise ValueError("P5 owner merged-cell mismatch: " + output.name)
        if {k: v.attr_text for k, v in actual.defined_names.items()} != {k: v.attr_text for k, v in expected.defined_names.items()}:
            raise ValueError("P5 owner sheet-defined-name mismatch: " + output.name + "/" + name)
        # Both approved P5 books have no input validation rules. Stop if
        # rules are introduced rather than silently dropping native rules.
        if actual.data_validations.dataValidation or expected.data_validations.dataValidation:
            raise ValueError("P5 owner validation mismatch: explicit integration required")
    with zipfile.ZipFile(io.BytesIO(native)) as archive:
        if any(b"dataValidation" in archive.read(n) for n in archive.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml")):
            raise ValueError("P5 owner native validation mismatch: explicit integration required")
    if {k: v.attr_text for k, v in generated.defined_names.items()} != {k: v.attr_text for k, v in approved.defined_names.items()}:
        raise ValueError("P5 owner defined-name mismatch: " + output.name)
    temporary = output.with_name(output.name + ".approved.tmp")
    try:
        temporary.write_bytes(native)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def create_excel(filepath, sheet_name="Лист1", headers=None, rows=None, col_widths=None, defer_save=False):
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
    
    if not defer_save:
        save_workbook(wb, filepath)
        print(f"  [Excel] {filepath}")
    return wb


def _print_setup(ws, area, landscape=False, title_rows=None):
    """Печать в ширину одного листа A4: столбцы не уходят на соседние
    страницы (приёмка #322, Кс-2 — книги резались на 2–3 листа)."""
    ws.print_area = area
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    if title_rows:
        ws.print_title_rows = title_rows


input_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
section_font = Font(bold=True, size=11)
ФОРМАТ_РУБ = "#,##0.00"
ФОРМАТ_СТАВКИ = "0.00##"
ФОРМАТ_ДАТЫ = "DD.MM.YYYY"
СТРОК_ПЕРИОДОВ = 5


def build_raschet_04(filepath):
    """04 — расчёт сумм требования к заказчику.

    Прежняя книга считала неустойку `=B8*B9` — «%/день × дни» без базы, и
    складывала проценты с рублями: 1,95 вместо 4 680,00 (приёмка #322,
    К-1). Теперь каждая строка названа по виду начисления и единицам:
    штраф в твёрдой сумме, штраф в процентах от базы, пени по периодам
    (база × % в день / 100 × дни). Ставки — входные ячейки, а не
    константы: норма отсылает к ставке «в соответствующие периоды»
    (сверка Р-026, Н-6 в normative-check-p5-2026-08-14.md).

    Ввод проверяется в столбце H «Проверка»: окончание раньше начала,
    отрицательные суммы и ставки, незаполненное поле строки, текст вместо
    числа, ставка числом вместо набора и ставка ниже порога (#333 Н-1,
    #357 §4). При ошибке
    ячейка суммы пуста, а итог раздела не считается — неверный ввод не даёт
    суммы в рублях.

    Сводка показывает неоплаченную сумму целиком и без удержания с
    ненаступившим сроком возврата, каждый вид неустойки и проценты по
    ст. 395 отдельно и не складывает их: можно ли требовать их вместе и
    от какой суммы — вопрос Р-026 (В-1 в #322). Проценты по ст. 395
    считаются, как и прежде: база × ставка / 100 / 365 × дни.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Расчёт требования"
    ws.column_dimensions["A"].width = 6
    for col, w in zip("BCDEFGH", (12, 12, 7, 15, 14, 16, 34)):
        ws.column_dimensions[col].width = w

    def проверка(r, формула):
        c = ws.cell(row=r, column=8, value=формула)
        c.font = Font(color="C00000", bold=True)
        c.alignment = Alignment(wrap_text=True, vertical="center")

    def строка(r, подпись, формула=None, формат=ФОРМАТ_РУБ, h=None):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.cell(row=r, column=1, value=подпись).alignment = Alignment(wrap_text=True, vertical="center")
        g = ws.cell(row=r, column=7, value=формула)
        g.number_format = формат
        g.border = thin_border
        if формула is None:
            g.fill = input_fill
        else:
            g.font = Font(bold=True)
        if h:
            проверка(r, h)

    def раздел(r, текст):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        ws.cell(row=r, column=1, value=текст).font = section_font

    def одно_число(ячейка):
        """Сообщение для необязательной суммы: пусто — нет ошибки."""
        return (f'=IF({ячейка}="","",IF(NOT(ISNUMBER({ячейка})),"Введите сумму числом",'
                f'IF({ячейка}<0,"Сумма меньше нуля — проверьте ввод","")))')

    def ставка(f):
        """Ставка из текстовой ячейки `f`: без пробелов, знака %, апострофа;
        точка — как запятая. Набор «1%» и «1» дают одно число — 1 (% в день
        или годовых, по шапке). Разделители заданы явно, а не берутся из
        локали."""
        текст = (f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({f}," ",""),'
                 f'"%",""),"\'",""),".",",")')
        return текст, f'_xlfn.NUMBERVALUE({текст},","," ")'

    def таблица_периодов(r0, шапка_ставки, формула_суммы, порог, о_пороге):
        """Ставка F — текстовая ячейка (#357 §4). Числовая ячейка хранит
        набор «1%» как 0,01, и отличить его от ставки 0,01 по величине нельзя:
        «1%» в день давал 1 162,50 вместо 116 250,00 без сообщения. В
        текстовой ячейке набор остаётся строкой, знак % виден и снимается
        в `ставка`. Число в F (вставка из другой таблицы, формула) знака уже
        не хранит — такая строка не считается, в «Проверке» сообщение.
        `порог` — ставка ниже него не считается (заявленное ограничение
        FIX-2), сообщение `о_пороге`."""
        for col, h in enumerate(["№", "Начало", "Окончание", "Дней", "База, руб.",
                                 шапка_ставки, "Сумма, руб.", "Проверка"], 1):
            c = ws.cell(row=r0, column=col, value=h)
            c.fill, c.font, c.border = header_fill, header_font, thin_border
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        строки = range(r0 + 1, r0 + 1 + СТРОК_ПЕРИОДОВ)
        for i, r in enumerate(строки, 1):
            b, c_, e, f, h = f"B{r}", f"C{r}", f"E{r}", f"F{r}", f"H{r}"
            текст, ст = ставка(f)
            h_ф = (f'=IF(AND({b}="",{c_}="",{e}="",{f}=""),"",'
                   f'IF(OR({b}="",{c_}="",{e}="",{f}=""),'
                   f'"Заполните все поля строки: начало, окончание, базу и ставку",'
                   f'IF(OR(NOT(ISNUMBER({b})),NOT(ISNUMBER({c_})),NOT(ISNUMBER({e}))),'
                   f'"Даты и суммы вводятся числом, даты — ДД.ММ.ГГГГ",'
                   f'IF(ISNUMBER({f}),"Ставка вставлена числом — не видно, был ли знак %. '
                   f'Наберите её заново с апострофом впереди: \'0,1 или \'0,1%",'
                   f'IF(OR(NOT(ISTEXT({f})),{текст}="",ISERROR({ст})),'
                   f'"Ставка не распознана — наберите число, например 0,1 или 0,1%",'
                   f'IF({c_}<{b},"Окончание раньше начала — проверьте даты",'
                   f'IF(OR({e}<0,{ст}<0),"База или ставка меньше нуля — проверьте ввод",'
                   f'IF(AND({ст}>0,{ст}<{порог}),"{о_пороге}",""))))))))')
            значения = [i, None, None,
                        f'=IF(OR({h}<>"",{b}=""),"",{c_}-{b}+1)',
                        None, None,
                        f'=IF(OR({h}<>"",{b}=""),"",{формула_суммы.format(r=r, ст=ст)})',
                        h_ф]
            форматы = ["0", ФОРМАТ_ДАТЫ, ФОРМАТ_ДАТЫ, "0", ФОРМАТ_РУБ, "@", ФОРМАТ_РУБ, "@"]
            for col, (v, fmt) in enumerate(zip(значения, форматы), 1):
                c = ws.cell(row=r, column=col, value=v)
                c.number_format, c.border = fmt, thin_border
                if col in (2, 3, 5, 6):
                    c.fill = input_fill
            проверка(r, h_ф)
        return строки[0], строки[-1]

    def итог_таблицы(r, подпись, п0, п1):
        ошибки = f"SUMPRODUCT(--(LEN(H{п0}:H{п1})>0))>0"
        строка(r, подпись, f'=IF({ошибки},"",SUM(G{п0}:G{п1}))',
               h=f'=IF({ошибки},"Итог не считается: исправьте строки с сообщением","")')

    ws.merge_cells("A1:H1")
    ws["A1"] = "РАСЧЁТ СУММ ТРЕБОВАНИЯ К ЗАКАЗЧИКУ"
    ws["A1"].font = Font(bold=True, size=13)
    ws.merge_cells("A2:H2")
    ws["A2"] = ("Вводите данные только в жёлтые ячейки. Суммы — в рублях. "
                "Ставку в таблицах пеней и ст. 395 набирайте с клавиатуры: ячейка "
                "текстовая, 0,05 и 0,05% — это 0,05 % в день, 16 и 16% — 16 % "
                "годовых. Если в ячейке ставки число (вставка из другой таблицы, "
                "формула), знак % по нему не виден — строка не считается; наберите "
                "ставку заново с апострофом впереди: '0,05. Ставка пеней меньше "
                "0,01 % в день и ключевая ставка меньше 1 % годовых не считаются. "
                "Процент штрафа в п. 2.2 — числом без знака %: 5 % — как 5. "
                "Даты — ДД.ММ.ГГГГ; первый и последний "
                "день периода входят в число дней. Период с другой базой или "
                "ставкой — отдельной строкой. Если в столбце «Проверка» есть "
                "сообщение, сумма по этой строке и итог раздела не считаются.")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 106

    раздел(4, "1. НЕОПЛАЧЕННАЯ СУММА")
    строка(5, "Сумма по КС-2 (по всем актам спора), руб.")
    строка(6, "Фактически оплачено, руб.")
    h7 = ('=IF(AND(G5="",G6=""),"",IF(OR(G5="",G6=""),"Заполните обе суммы: по КС-2 и оплату",'
          'IF(OR(NOT(ISNUMBER(G5)),NOT(ISNUMBER(G6))),"Введите суммы числом",'
          'IF(OR(G5<0,G6<0),"Сумма меньше нуля — проверьте ввод",'
          'IF(G6>G5,"Оплачено больше суммы по КС-2 — проверьте ввод","")))))')
    строка(7, "Неоплачено по КС-2, руб.", '=IF(OR(H7<>"",G5=""),"",G5-G6)', h=h7)
    h8 = ('=IF(G8="","",IF(NOT(ISNUMBER(G8)),"Введите сумму числом",'
          'IF(G8<0,"Сумма меньше нуля — проверьте ввод",'
          'IF(AND(ISNUMBER(G7),G8>G7),"Удержание больше неоплаченной суммы — проверьте ввод",""))))')
    строка(8, "из них удержание, срок возврата которого по договору ещё не наступил, руб. "
              "(если такого нет — оставьте пустым)", h=h8)
    строка(9, "Неоплачено без такого удержания, руб.",
           '=IF(OR(NOT(ISNUMBER(G7)),H8<>""),"",G7-IF(G8="",0,G8))')

    раздел(11, "2. НЕУСТОЙКА ПО ДОГОВОРУ — заполните тот вид, который записан в договоре")
    строка(12, "2.1. Штраф в твёрдой сумме, руб.", h=одно_число("G12"))
    строка(13, "2.2. Штраф в процентах от суммы (разовый): сумма, от которой он считается, руб.")
    строка(14, "процент штрафа, % (5 % вводится как 5)", формат=ФОРМАТ_СТАВКИ)
    h15 = ('=IF(AND(G13="",G14=""),"",IF(OR(G13="",G14=""),"Заполните сумму и процент штрафа",'
           'IF(OR(NOT(ISNUMBER(G13)),NOT(ISNUMBER(G14))),"Введите сумму и процент числом",'
           'IF(OR(G13<0,G14<0),"Сумма или процент меньше нуля — проверьте ввод",""))))')
    строка(15, "сумма штрафа, руб.", '=IF(OR(H15<>"",G13=""),"",G13*G14/100)', h=h15)
    раздел(16, "2.3. Пени за каждый день просрочки: база × ставка в день / 100 × дни")
    п0, п1 = таблица_периодов(
        17, "Ставка, % в день (0,05 или 0,05%)", "E{r}*{ст}/100*D{r}", "0.01",
        "Ставка меньше 0,01 % в день — книга такую ставку не считает")
    r_пени = п1 + 1
    итог_таблицы(r_пени, "Итого пени, руб.", п0, п1)

    r = r_пени + 2
    раздел(r, "3. ПРОЦЕНТЫ ПО СТ. 395 ГК РФ: база × ключевая ставка / 100 / 365 × дни")
    к0, к1 = таблица_периодов(
        r + 1, "Ключевая ставка, % годовых (16 или 16%)", "E{r}*{ст}/100/365*D{r}", "1",
        "Ставка меньше 1 % годовых — книга такую ставку не считает")
    r_проц = к1 + 1
    итог_таблицы(r_проц, "Итого проценты, руб.", к0, к1)

    r = r_проц + 2
    раздел(r, "4. СВОДКА — суммы показаны раздельно")
    ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=8)
    ws.cell(row=r + 1, column=1, value=(
        "Общая сумма этих строк не выводится: какие из них и от какой суммы "
        "включать в требование, определяется договором и законом. Перенесите "
        "в претензию только те строки, основание которых проверено."
    )).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r + 1].height = 32
    ошибка = '"Ошибка ввода — см. раздел {n}"'
    сводка = [
        ("Неоплачено по КС-2, руб.", '=IF(ISNUMBER(G7),G7,"")', 'H7<>""', 1),
        ("из них удержание, срок возврата которого по договору ещё не наступил, руб.",
         '=IF(AND(ISNUMBER(G7),H8=""),IF(G8="",0,G8),"")', 'OR(H7<>"",H8<>"")', 1),
        ("Неоплачено без такого удержания, руб.", '=IF(ISNUMBER(G9),G9,"")', 'OR(H7<>"",H8<>"")', 1),
        ("Штраф в твёрдой сумме, руб.", '=IF(OR(G12="",H12<>""),"",G12)', 'H12<>""', 2),
        ("Штраф в процентах, руб.", '=IF(ISNUMBER(G15),G15,"")', 'H15<>""', 2),
        ("Пени, руб.", f'=IF(ISNUMBER(G{r_пени}),G{r_пени},"")', f'H{r_пени}<>""', 2),
        ("Проценты по ст. 395 ГК РФ, руб.", f'=IF(ISNUMBER(G{r_проц}),G{r_проц},"")', f'H{r_проц}<>""', 3),
    ]
    for i, (подпись, формула, условие, n) in enumerate(сводка, r + 2):
        строка(i, подпись, формула, h=f'=IF({условие},{ошибка.format(n=n)},"")')
    last = r + 1 + len(сводка)

    _print_setup(ws, f"A1:H{last}")
    write_owner_p5_workbook(wb, filepath)


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
    
    doc.save(filepath)
    print(f"  [Word]  {filepath}")


# Кириллица в PDF: стандартные шрифты reportlab (Helvetica и прочие из
# «стандартных четырнадцати») кодируются WinAnsi и кириллических глифов не
# содержат — c.drawString() отрабатывает молча и не рисует ничего. Так и
# получился файл 07-algoritm-proverki-uderzhaniy.pdf: 2 432 байта при
# 85–91 КБ у PDF соседних комплектов, на месте русского текста — ряды «n»,
# ни одной ошибки при сборке. Регистрируем шрифт со славянским набором.
#
# Дефект и лечение те же, что у 08-*.pdf комплектов P3 и P4 (правка
# 16.09.2026): helper дословно повторяет build_paid_05.py и build_paid_06.py,
# чтобы третий комплект не разошёлся с двумя исправленными.
_ШРИФТЫ = (
    ("MVBSans", "MVBSans-Bold",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("MVBSans", "MVBSans-Bold",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def _register_cyrillic_font():
    """Имена шрифтов для основного текста и заголовка.

    Возвращает стандартные Helvetica только если ни один файл шрифта не
    нашёлся. Это не тихий откат: вызывающий обязан проверить, что в
    собранном PDF есть текст, — проверка в отчёте о правке.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for обычный, жирный, файл_о, файл_ж in _ШРИФТЫ:
        if not (os.path.exists(файл_о) and os.path.exists(файл_ж)):
            continue
        if обычный not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(обычный, файл_о))
            pdfmetrics.registerFont(TTFont(жирный, файл_ж))
        return обычный, жирный
    return "Helvetica", "Helvetica-Bold"


def _wrap(line, шрифт, кегль, поле):
    """Режет строку по ширине поля, не меняя ни одного слова.

    Нужно ровно из-за одной строки этого комплекта — про претензионный срок
    по ч. 5 ст. 4 АПК РФ, 193 знака. drawString переносов не делает: строка
    уходит за правый край листа, и на бумаге предложение обрывается на
    полуслове. У соседних комплектов P3 и P4 длинных строк нет вовсе, и до
    встроенного шрифта обрыв был не виден — текст не рисовался совсем.

    Продолжение выравнивается по отступу исходной строки: перечисления вида
    «   - …» остаются перечислениями.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    if stringWidth(line, шрифт, кегль) <= поле:
        return [line]

    отступ = " " * (len(line) - len(line.lstrip(" ")))
    продолжение = отступ + "  "
    строки, текущая = [], отступ
    for слово in line.split():
        проба = (текущая + " " + слово) if текущая.strip() else (текущая + слово)
        if текущая.strip() and stringWidth(проба, шрифт, кегль) > поле:
            строки.append(текущая)
            текущая = продолжение + слово
        else:
            текущая = проба
    if текущая.strip():
        строки.append(текущая)
    return строки


def create_pdf_simple(filepath, title, lines):
    обычный, жирный = _register_cyrillic_font()
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    поле = width - 2 * 2*cm
    
    c.setFont(жирный, 16)
    c.drawCentredString(width/2, height - 2*cm, title)
    
    c.setFont(обычный, 11)
    y = height - 3.5*cm
    for line in lines:
        for кусок in _wrap(line, обычный, 11, поле):
            if y < 2*cm:
                c.showPage()
                y = height - 2*cm
                c.setFont(обычный, 11)
            c.drawString(2*cm, y, кусок)
            y -= 0.6*cm
    
    c.save()
    print(f"  [PDF]   {filepath}")


# ==================== PAID 07 ====================
def build_paid_07():
    folder = os.path.join(BASE_DIR, "07-uderzhaniya-shtrafy-zachety")
    print(f"\n[BUILD] {folder}")
    
    create_word_doc(
        os.path.join(folder, "01-pretenziya-na-uderzhanie.docx"),
        "ПРЕТЕНЗИЯ на неправомерное удержание сумм по договору подряда",
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
            {"text": "ПРЕТЕНЗИЯ"},
            {"text": "о взыскании неправомерно удержанных сумм"},
            {"text": ""},
            {"text": "Уважаемый [ФИО]!"},
            {"text": ""},
            {"text": "Настоящим сообщаем, что в нарушение п. [номер] договора подряда № [номер] от [дата] (далее - Договор) Заказчиком неправомерно удержаны средства в размере [сумма] руб."},
            {"text": ""},
            {"text": "1. ОБСТОЯТЕЛЬСТВА ДЕЛА:"},
            {"text": "   - КС-2 № _____ от _____ на сумму _____ руб. подписана обеими сторонами."},
            {"text": "   - Крайний срок оплаты: _____."},
            {"text": "   - Фактически оплачено: _____ руб."},
            {"text": "   - Удержано без согласования: _____ руб."},
            {"text": "   - Основание удержания (со слов Заказчика): _______________________________"},
            {"text": ""},
            {"text": "2. ПРАВОВОЕ ОБОСНОВАНИЕ:"},
            {"text": "   Согласно ст. 310 ГК РФ односторонний отказ от исполнения обязательства и одностороннее изменение его условий не допускаются, за исключением случаев, предусмотренных законом."},
            {"text": ""},
            {"text": "   Согласно п. 1 ст. 711 ГК РФ заказчик обязан уплатить подрядчику обусловленную цену после окончательной сдачи результатов работы при условии, что работа выполнена надлежащим образом и в согласованный срок. Порядок оплаты работ по договору строительного подряда установлен ст. 746 ГК РФ."},
            {"text": ""},
            {"text": "   Удержание сумм без письменного согласования подрядчика является нарушением Договора и правомерных интересов Подрядчика."},
            {"text": ""},
            {"text": "3. ТРЕБОВАНИЯ:"},
            {"text": "   В срок до [дата] произвести оплату удержанной суммы в размере [сумма] руб."},
            {"text": ""},
            {"text": "   В случае неудовлетворения претензии оставляем за собой право обратиться в арбитражный суд с исковым требованием о взыскании:"},
            {"bullet": [
                "удержанной суммы - [сумма] руб.,",
                "неустойки по договору - [сумма] руб.,",
                "процентов по ст. 395 ГК РФ - [сумма] руб.,",
                "судебных расходов."
            ]},
            {"text": ""},
            {"text": "4. ПРИЛОЖЕНИЯ:"},
            {"bullet": [
                "Копия договора подряда (л. __)",
                "Копия КС-2 (л. __)",
                "Копия КС-3 (л. __)",
                "Выписка из банка об удержании (л. __)",
                "Расчет удержанной суммы (л. __)."
            ]},
            {"text": ""},
            {"text": "Генеральный директор _________________ [ФИО]"},
            {"text": "М.П."},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "02-pretenziya-na-shtraf.docx"),
        "ПРЕТЕНЗИЯ на необоснованный штраф (неустойку)",
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
            {"text": "ПРЕТЕНЗИЯ"},
            {"text": "о признании штрафа (неустойки) необоснованным и возврате удержанных сумм"},
            {"text": ""},
            {"text": "Уважаемый [ФИО]!"},
            {"text": ""},
            {"text": "В соответствии с п. [номер] договора подряда № [номер] от [дата] (далее - Договор) Заказчик удержал с Подрядчика штраф (неустойку) в размере [сумма] руб. по основанию: [указать основание]."},
            {"text": ""},
            {"text": "1. ОБСТОЯТЕЛЬСТВА:"},
            {"text": "   - Дата наложения штрафа: _____."},
            {"text": "   - Основание (письмо, акт, приказ): _____."},
            {"text": "   - Сумма штрафа: _____ руб."},
            {"text": "   - Фактические обстоятельства: [описать, почему штраф необоснован]"},
            {"text": ""},
            {"text": "2. ПРАВОВОЕ ОБОСНОВАНИЕ:"},
            {"text": "   Согласно ст. 333 ГК РФ, если подлежащая уплате неустойка явно несоразмерна последствиям нарушения обязательства, суд вправе уменьшить неустойку. Если обязательство нарушено лицом, осуществляющим предпринимательскую деятельность, суд вправе уменьшить неустойку при условии заявления должника о таком уменьшении (п. 1 ст. 333 ГК РФ)."},
            {"text": ""},
            {"text": "   Согласно п. 2 ст. 333 ГК РФ уменьшение неустойки, определённой договором и подлежащей уплате лицом, осуществляющим предпринимательскую деятельность, допускается в исключительных случаях, если будет доказано, что взыскание неустойки в предусмотренном договором размере может привести к получению кредитором необоснованной выгоды."},
            {"text": ""},
            {"text": "   [Если штраф вообще не предусмотрен договором - указать:] Штраф не предусмотрен Договором и взимается вне рамок согласованных сторонами условий."},
            {"text": ""},
            {"text": "3. ТРЕБОВАНИЯ:"},
            {"text": "   - Признать штраф необоснованным."},
            {"text": "   - Вернуть удержанную сумму в размере [сумма] руб."},
            {"text": "   - [Или:] Уменьшить размер штрафа до [сумма] руб. и вернуть разницу в размере [сумма] руб., поскольку штраф явно несоразмерен последствиям нарушения и его взыскание в договорном размере может привести к получению Заказчиком необоснованной выгоды: [указать обстоятельства со ссылкой на документы, например, что возможные убытки Заказчика от нарушения значительно ниже суммы штрафа]."},
            {"text": ""},
            {"text": "Генеральный директор _________________ [ФИО]"},
            {"text": "М.П."},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "03-vozrazhenie-na-zachet.docx"),
        "ВОЗРАЖЕНИЕ на односторонний зачёт встречных требований",
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
            {"text": "ВОЗРАЖЕНИЕ"},
            {"text": "на односторонний зачет встречных требований"},
            {"text": ""},
            {"text": "Уважаемый [ФИО]!"},
            {"text": ""},
            {"text": "Настоящим сообщаем, что односторонний зачет, произведенный Заказчиком [дата] в размере [сумма] руб., является неправомерным по следующим основаниям."},
            {"text": ""},
            {"text": "1. Зачет произведен без письменного согласования с Подрядчиком."},
            {"text": "   Согласно ст. 410 ГК РФ зачет встречных однородных требований допускается при заявлении одной стороны. Однако в договоре подряда стороны могут ограничить или исключить такое право (ст. 411 ГК РФ: зачёт не допускается в случаях, предусмотренных законом или договором)."},
            {"text": ""},
            {"text": "2. Требование Заказчика, на которое произведен зачет, является необоснованным / оспариваемым / не подтвержденным доказательствами."},
            {"text": "   [Описать: в чем именно претензия заказчика и почему она необоснованна]"},
            {"text": ""},
            {"text": "3. [Выбрать применимое, остальное удалить:]"},
            {"text": "   - Размер зачёта превышает размер встречного требования Заказчика, определённый договором и подтверждённый документами: [указать, какое требование заявлено к зачёту (убытки, неустойка, иное), его размер по расчёту Заказчика и размер, который Подрядчик считает обоснованным, со ссылкой на документы]."},
            {"text": "   - Срок исполнения встречного требования Заказчика не наступил (ст. 410 ГК РФ)."},
            {"text": "   - [Только если встречное требование Заказчика не денежное (например, о передаче вещи или о безвозмездном устранении недостатков) и оставалось таким на дату заявления о зачёте; к неустойке, процентам и убыткам не применяется:] Встречное требование Заказчика не однородно с денежным требованием Подрядчика (ст. 410 ГК РФ)."},
            {"text": "   - Зачёт не допускается договором (п. [номер] Договора) или по встречному требованию Заказчика истёк срок исковой давности (ст. 411, п. 3 ст. 199 ГК РФ)."},
            {"text": ""},
            {"text": "ТРЕБОВАНИЯ:"},
            {"text": "   - Признать зачет неправомерным."},
            {"text": "   - Вернуть незаконно зачтенную сумму [сумма] руб."},
            {"text": "   - [Или:] Произвести зачет в согласованном с Подрядчиком размере [сумма] руб."},
            {"text": ""},
            {"text": "Генеральный директор _________________ [ФИО]"},
            {"text": "М.П."},
        ]
    )
    
    build_raschet_04(os.path.join(folder, "04-raschet-ubytkov.xlsx"))
    print(f"  [Excel] {os.path.join(folder, '04-raschet-ubytkov.xlsx')}")

    # Поля учёта отправки (дата, способ, подтверждение, срок ответа и его
    # основание) — по приёмке #322, К-2 и З-4. Срок ответа не подставляется:
    # универсального срока нет, основание покупатель выписывает сам.
    # «Сумма» остаётся в E: на ней стоит итог SUM(E2:E20).
    reestr = os.path.join(folder, "05-reestr-uderzhaniy.xlsx")
    wb = create_excel(
        reestr,
        "Реестр удержаний и штрафов",
        headers=["№", "Дата", "Тип", "Основание", "Сумма", "Статус",
                 "Дата отправки", "Способ отправки", "Подтверждение отправки",
                 "Срок ответа", "Основание срока", "Ответ", "Результат"],
        # Итог стоит под диапазоном E2:E20, а не внутри него: строка итога в
        # пятой строке суммировала саму себя (Calc: Err:522). Строки 5–20 —
        # пустые, под новые удержания.
        rows=[
            [1, "", "Удержание", "", 0, "Оспаривается", "", "", "", "", "", "Претензия направлена", ""],
            [2, "", "Штраф", "", 0, "Оспаривается", "", "", "", "", "", "", ""],
            [3, "", "Зачет", "", 0, "Оспаривается", "", "", "", "", "", "", ""],
        ] + [[None] * 13 for _ in range(5, 21)] + [
            ["", "", "", "Сумма записей (не размер требования):", "=SUM(E2:E20)",
             "", "", "", "", "", "", "", ""],
        ],
        col_widths=[5, 11, 12, 24, 12, 13, 11, 15, 18, 11, 18, 18, 16],
        defer_save=True
    )
    ws = wb.active
    for r in range(2, 21):
        ws.cell(row=r, column=2).number_format = "DD.MM.YYYY"
        ws.cell(row=r, column=5).number_format = "#,##0.00"
        ws.cell(row=r, column=7).number_format = "DD.MM.YYYY"
        # «Срок ответа» — тоже дата: без формата Calc показывал набор как
        # ДД.ММ.ГГ, а дату из файла печатал «###» (#333, Н-2).
        ws.cell(row=r, column=10).number_format = "DD.MM.YYYY"
    ws.cell(row=21, column=5).number_format = "#,##0.00"
    # Одна сумма может стоять в реестре несколько раз: штраф, удержанный из
    # оплаты, и зачёт этого же штрафа — две строки. Итог складывает строки,
    # поэтому подписан как сумма записей, а не размер требования (#323).
    ws.merge_cells("A22:M22")
    ws["A22"] = ("Одна и та же сумма может стоять в реестре несколько раз — например, "
                 "штраф, удержанный из оплаты, и зачёт этого же штрафа. Итог складывает "
                 "строки и размером требования не является.")
    ws["A22"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[22].height = 30
    ws.freeze_panes = "A2"
    _print_setup(ws, "A1:M22", landscape=True, title_rows="1:1")
    write_owner_p5_workbook(wb, reestr)

    create_excel(
        os.path.join(folder, "06-grafik-vozmeshcheniya.xlsx"),
        "График возмещения",
        headers=["№", "Платеж", "Дата", "Сумма", "Способ", "Подтверждение", "Статус"],
        # Итог под диапазоном D2:D10, а не внутри него (было: D4 в D2:D10).
        # Строки 4–10 — пустые, под следующие платежи.
        rows=[
            [1, "Первая часть", "", 0, "Банковский перевод", "", "Ожидается"],
            [2, "Вторая часть", "", 0, "Банковский перевод", "", "Ожидается"],
        ] + [[None] * 7 for _ in range(4, 11)] + [
            ["", "", "ИТОГО:", "=SUM(D2:D10)", "", "", ""],
        ],
        col_widths=[6, 16, 14, 14, 20, 18, 14]
    )
    
    create_pdf_simple(
        os.path.join(folder, "07-algoritm-proverki-uderzhaniy.pdf"),
        "АЛГОРИТМ ПРОВЕРКИ ОБОСНОВАННОСТИ УДЕРЖАНИЙ",
        [
            "ШАГ 1. Зафиксируйте факт удержания",
            "   - Дата удержания",
            "   - Сумма",
            "   - Основание (письмо, акт, устное сообщение)",
            "   - Кто уполномочен принять решение об удержании",
            "",
            "ШАГ 2. Проверьте договор",
            "   - Предусмотрено ли удержание в договоре?",
            "   - Какие условия должны быть соблюдены?",
            "   - Требуется ли письменное согласование?",
            "",
            "ШАГ 3. Проверьте документы заказчика",
            "   - Есть ли акт с фиксацией недостатков?",
            "   - Есть ли расчет ущерба?",
            "   - Подписан ли акт ПОДРЯДЧИКОМ?",
            "",
            "ШАГ 4. Оцените обоснованность",
            "   - Если удерживают убытки (например, расходы на другого подрядчика): подтверждены ли расчётом их размер и связь с вашим нарушением (ст. 15, 393 ГК РФ)?",
            "   - Если удерживают неустойку (штраф, пени): предусмотрена ли она договором и начислена ли за нарушение, за которое вы отвечаете (п. 2 ст. 330 ГК РФ)? Доказывать убытки для неустойки заказчик не обязан (п. 1 ст. 330 ГК РФ).",
            "   - Уменьшить неустойку вправе суд, если она явно несоразмерна последствиям нарушения; если нарушитель — предприниматель, только по его заявлению, а договорную неустойку — лишь в исключительных случаях, когда доказано, что взыскание в договорном размере может привести к необоснованной выгоде заказчика (ст. 333 ГК РФ). Подробнее — файл 08, «Общий принцип оспаривания».",
            "",
            "ШАГ 5. Составьте претензию",
            "   - Если удержание неправомерно - требуйте возврата",
            "   - Если сумма завышена - требуйте пересчета",
            "   - Если документы отсутствуют - требуйте их предоставления",
            "",
            "ШАГ 6. Отслеживайте сроки",
            "   - Претензия: иск — по истечении 30 календарных дней со дня её направления, если иные срок или порядок не установлены договором (ч. 5 ст. 4 АПК РФ). Проверьте претензионный срок в договоре.",
            "   - После отказа - иск в суд",
            "   - Исковая давность: проверьте срок и день начала его течения по ст. 196 и 200 ГК РФ; для пеней и процентов — также ст. 207 ГК РФ, для требований заказчика о качестве работ — ст. 725 ГК РФ",
            "",
            "ШАГ 7. Рассчитайте полную сумму требований",
            "   - Удержанная сумма",
            "   + Пени по договору",
            "   + Проценты по ст. 395 ГК РФ",
            "   + Судебные расходы",
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "08-tipovye-osnovaniya.docx"),
        "ТИПОВЫЕ ОСНОВАНИЯ ДЛЯ УДЕРЖАНИЙ и как их оспорить",
        [
            {"heading": "Основание 1. 'Нарушение сроков выполнения работ'",
             "text": "ЗАКАЗЧИК ГОВОРИТ: 'Вы просрочили сдачу на 10 дней, удерживаем штраф 500 000 руб.'\n\nВАШИ ДОВОДЫ:\n- Просрочка возникла по причинам заказчика (недопоставка материалов, задержка согласования).\n- Были оформлены акты о простое.\n- Заказчик не направил претензию в срок.\n\nДОКАЗАТЕЛЬСТВА: акты простоя, переписка, сметы на допработы."},
            {"heading": "Основание 2. 'Некачественное выполнение работ'",
             "text": "ЗАКАЗЧИК ГОВОРИТ: 'Качество бетона не соответствует проекту, удерживаем 1 000 000 руб.'\n\nВАШИ ДОВОДЫ:\n- Работы приняты по акту приемки без замечаний.\n- Претензия предъявлена после истечения гарантийного срока.\n- Дефекты возникли из-за эксплуатации, а не строительства.\n\nДОКАЗАТЕЛЬСТВА: акт приемки, экспертное заключение, переписка."},
            {"heading": "Основание 3. 'Неустранение недостатков в гарантийный срок'",
             "text": "ЗАКАЗЧИК ГОВОРИТ: 'Вы не устранили течь кровли, наняли другого подрядчика, удерживаем 800 000 руб.'\n\nВАШИ ДОВОДЫ:\n- Заказчик не направил письменное требование об устранении.\n- Другой подрядчик выполнил работы без согласования стоимости.\n- Стоимость работ завышена.\n\nДОКАЗАТЕЛЬСТВА: переписка, сметы, сравнительный анализ цен."},
            {"heading": "Основание 4. 'Не предоставлена исполнительная документация'",
             "text": "ЗАКАЗЧИК ГОВОРИТ: 'Нет КС-2, КС-3, удерживаем 100% стоимости.'\n\nВАШИ ДОВОДЫ:\n- ИД передана, акт приемки подписан.\n- Заказчик неявкой препятствовал подписанию.\n- КС-2 направлена заказным письмом.\n\nДОКАЗАТЕЛЬСТВА: акт передачи, почтовые квитанции, уведомления."},
            # Текст блока принят нормативным перечитом Р-026 от 29.09.2026
            # (tools/candidates/MB001_R026_P5_RECHECK.md). Сокращать и
            # перефразировать без нового перечита нельзя; проверка —
            # tools/test_p5_documents.py.
            {"heading": "Общий принцип оспаривания",
             "text": "Проверьте каждое удержание по шести вопросам:\n"
                     "1. Предусмотрено ли оно договором или законом.\n"
                     "2. Подтверждено ли оно документами: актом, расчётом, перепиской.\n"
                     "3. Если удерживают убытки (например, расходы на другого подрядчика) — подтверждены ли расчётом их размер и связь с вашим нарушением (ст. 15, 393 ГК РФ).\n"
                     "4. Если удерживают неустойку (штраф, пени) — предусмотрена ли она договором и начислена ли за нарушение, за которое вы отвечаете (п. 2 ст. 330 ГК РФ). Доказывать убытки для неустойки заказчик не обязан (п. 1 ст. 330 ГК РФ). Уменьшить неустойку вправе суд, если она явно несоразмерна последствиям нарушения; если нарушитель — предприниматель, только по его заявлению, а договорную неустойку — лишь в исключительных случаях, когда доказано, что взыскание в договорном размере может привести к необоснованной выгоде заказчика (ст. 333 ГК РФ).\n"
                     "5. Если удержание заявлено как зачёт — однородно ли встречное требование заказчика, наступил ли срок его исполнения и не запрещён ли зачёт законом или договором (ст. 410, 411 ГК РФ). По требованию с истёкшей исковой давностью зачёт не допускается (ст. 411, п. 3 ст. 199 ГК РФ); на какую дату проверять давность, уточните у юриста.\n"
                     "6. Требует ли договор согласовать удержание с вами и было ли оно согласовано.\n"
                     "Если хотя бы по одному вопросу ответ не в пользу заказчика — это довод против удержания. Исход спора зависит от договора и документов по объекту."},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "09-sravnitelnaya-tablica.docx"),
        "СРАВНИТЕЛЬНАЯ ТАБЛИЦА: Бесплатно vs Полный комплект",
        [
            {"heading": "Сравнение",
             "table": [
                 ["Возможность", "Бесплатно", "Полный комплект", "Почему это важно"],
                 ["Алгоритм проверки удержаний", "Краткий (7 шагов)", "Детальный с контрольными точками", "Не пропускаете сроки"],
                 ["Претензия на удержание", "Нет", "Юридически выверенная", "Профессиональный документ"],
                 ["Претензия на штраф", "Нет", "С обоснованием по ст. 333 ГК РФ", "Снижаете штраф в суде"],
                 ["Возражение на зачет", "Нет", "С ссылками на ст. 410 ГК РФ", "Оспариваете односторонний зачет"],
                 ["Калькулятор убытков", "Нет", "С автоматическим расчетом", "Точная сумма требований"],
                 ["Реестр удержаний", "Нет", "С автоподсчетом", "Видите полную картину"],
                 ["График возмещения", "Нет", "С отслеживанием платежей", "Контролируете исполнение"],
                 ["Типовые основания", "Нет", "4 сценария + доводы + доказательства", "Готовые аргументы"],
                 ["Консультация юриста", "Нет", "Форма подготовки к консультации", "Экономите время и деньги"],
             ]},
            {"text": "\nУдержания, штрафы и зачеты - самая болезненная тема для подрядчика. Один неправомерный штраф в 500 000 ₽ может 'съесть' всю маржу объекта."},
            {"text": "\nСтоимость полного комплекта: 19 900 - 24 900 ₽\nСтоимость одного неоспоренного штрафа: от 100 000 ₽ до нескольких миллионов.\nОкупаемость: с первого же спорного случая."},
        ]
    )
    
    create_word_doc(
        os.path.join(folder, "10-konsultaciya-po-delu.docx"),
        "ФОРМА ПОДГОТОВКИ К КОНСУЛЬТАЦИИ С ЮРИСТОМ",
        [
            {"text": "ФОРМА ПОДГОТОВКИ К КОНСУЛЬТАЦИИ С ЮРИСТОМ"},
            {"text": "по спору об удержаниях / штрафах / зачетах"},
            {"text": ""},
            {"text": "Заполните эту форму до встречи с юристом: сведения о договоре и споре, суммы, хронология и перечень документов будут собраны в одном месте."},
            {"text": ""},
            {"heading": "1. ОБЩИЕ СВЕДЕНИЯ",
             "table": [
                 ["Параметр", "Значение"],
                 ["Наименование подрядчика", ""],
                 ["Наименование заказчика", ""],
                 ["Номер договора", ""],
                 ["Дата договора", ""],
                 ["Предмет договора (кратко)", ""],
                 ["Сумма договора", ""],
             ]},
            {"heading": "2. СУТЬ СПОРА",
             "table": [
                 ["Параметр", "Значение"],
                 ["Тип спора", "☐ Удержание  ☐ Штраф  ☐ Зачет  ☐ Другое: _______"],
                 ["Сумма спора", ""],
                 ["Дата возникновения спора", ""],
                 ["Основание (со слов заказчика)", ""],
                 ["Ваша позиция", ""],
             ]},
            {"heading": "3. ДОКУМЕНТЫ (отметьте наличие)",
             "table": [
                 ["Документ", "Наличие", "Где хранится"],
                 ["Договор подряда", "☐", ""],
                 ["КС-2", "☐", ""],
                 ["КС-3", "☐", ""],
                 ["Акт приемки работ", "☐", ""],
                 ["Претензия заказчика", "☐", ""],
                 ["Ваш ответ на претензию", "☐", ""],
                 ["Выписка из банка об удержании", "☐", ""],
                 ["Переписка с заказчиком", "☐", ""],
                 ["Акты о простое", "☐", ""],
                 ["Допсоглашения", "☐", ""],
             ]},
            {"heading": "4. ХРОНОЛОГИЯ (кратко, в формате 'дата - событие')",
             "text": "\n[Заполните]:\n\n\n\n"},
            {"heading": "5. ВОПРОСЫ К ЮРИСТУ",
             "text": "\n1. \n2. \n3. \n"},
            {"heading": "6. ЖЕЛАЕМЫЙ РЕЗУЛЬТАТ",
             "text": "☐ Возврат удержанной суммы\n☐ Уменьшение штрафа\n☐ Признание зачета неправомерным\n☐ Подготовка иска\n☐ Консультация по стратегии\n☐ Другое: _________________________________"},
        ]
    )

    # 11: требование о возврате по наступившему сроку. Отдельный жанр, не
    # претензия: спора ещё нет — событие возврата по договору наступило, и
    # подрядчик требует исполнения условия, а не оспаривает нарушение.
    # Добавлен 14.08.2026 решением владельца: манифест бесплатного материала
    # обещает этот документ «за границей бесплатного», разбор кластера
    # «Удержания» показал, что в комплекте его нет.
    create_word_doc(
        os.path.join(folder, "11-trebovanie-o-vozvrate-uderzhaniya.docx"),
        "ТРЕБОВАНИЕ о возврате гарантийного удержания по наступившему сроку",
        [
            {"text": "[На бланке организации]"},
            {"text": ""},
            {"text": "Исх. № _____ от '___' ___________ 20___ г."},
            {"text": ""},
            {"text": "Генеральному директору"},
            {"text": "[Наименование заказчика / генподрядчика]"},
            {"text": "[ФИО руководителя]"},
            {"text": ""},
            {"text": "От [Наименование подрядчика]"},
            {"text": ""},
            {"text": "ТРЕБОВАНИЕ"},
            {"text": "о возврате гарантийного удержания"},
            {"text": ""},
            {"text": "Уважаемый [ФИО]!"},
            {"text": ""},
            {"text": "Между [Наименование заказчика] и [Наименование подрядчика] заключён договор подряда № [номер] от [дата] (далее — Договор)."},
            {"text": ""},
            {"text": "1. ОСНОВАНИЕ УДЕРЖАНИЯ И ЕГО РАЗМЕР:"},
            {"text": "   - Пунктом [номер] Договора предусмотрено гарантийное удержание в размере [доля/порядок расчёта по Договору] от стоимости выполненных работ."},
            {"text": "   - Работы выполнены и приняты: КС-2 № _____ от _____, КС-3 № _____ от _____ [перечислить все закрытые периоды или сослаться на прилагаемый реестр]."},
            {"text": "   - Сумма удержанного по принятым работам: [сумма] руб. [расчёт — в прилагаемом реестре удержаний]."},
            {"text": ""},
            {"text": "2. СОБЫТИЕ ВОЗВРАТА НАСТУПИЛО:"},
            {"text": "   - Пунктом [номер] Договора возврат удержания обусловлен: [событие по Договору — подписание акта приёмки законченного объекта / ввод объекта в эксплуатацию / истечение гарантийного срока / иное]."},
            {"text": "   - Указанное событие наступило: [дата], что подтверждается: [документ — акт, разрешение на ввод, иное]."},
            {"text": "   - Срок возврата по пункту [номер] Договора: [срок]. Он истёк / истекает: [дата]."},
            {"text": "   - Заявленных в установленном Договором порядке зачётов, удержаний и претензий по качеству, уменьшающих сумму к возврату, на дату настоящего требования не имеется. [Если такие заявления есть — указать их и сумму, которую они затрагивают; несогласие с ними оформляется отдельным возражением на зачёт — файл 03 комплекта.]"},
            {"text": ""},
            {"text": "3. ПРАВОВОЕ ОБОСНОВАНИЕ:"},
            {"text": "   Согласно ст. 309 ГК РФ обязательства должны исполняться надлежащим образом в соответствии с их условиями. Согласно ст. 310 ГК РФ односторонний отказ от исполнения обязательства не допускается, за исключением случаев, предусмотренных законом или иными правовыми актами; Договором такое право Заказчика в отношении возврата гарантийного удержания не предусмотрено."},
            {"text": "   Обязанность возвратить сумму гарантийного удержания при наступлении согласованного события следует из пункта [номер] Договора."},
            {"text": ""},
            {"text": "4. ТРЕБОВАНИЕ:"},
            {"text": "   В срок, установленный пунктом [номер] Договора [если срок Договором не установлен — в срок, предусмотренный п. 2 ст. 314 ГК РФ], перечислить сумму гарантийного удержания [сумма] руб. по реквизитам: [реквизиты]."},
            {"text": ""},
            {"text": "   При неисполнении настоящего требования оставляем за собой право потребовать также уплаты процентов по ст. 395 ГК РФ и обратиться в арбитражный суд."},
            {"text": ""},
            {"text": "5. ПРИЛОЖЕНИЯ:"},
            {"bullet": [
                "Реестр удержаний по объекту (л. __)",
                "Копии КС-2, КС-3 по закрытым периодам (л. __)",
                "Документ о наступлении события возврата (л. __)",
                "Расчёт суммы к возврату (л. __).",
            ]},
            {"text": ""},
            {"text": "Генеральный директор _________________ [ФИО]"},
            {"text": "М.П."},
        ]
    )


if __name__ == "__main__":
    build_paid_07()
    print("\nГОТОВО: paid-07")
