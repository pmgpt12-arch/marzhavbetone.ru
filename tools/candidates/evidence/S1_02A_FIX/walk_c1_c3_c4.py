"""Авторский прогон С-1, С-3, С-4 в Calc и Writer после исправлений S1-02А-FIX.
Данные сценариев — вымышленные, те же, что в независимой проверке #325
(evidence/S1_02A_BUYER/fill_*.py), с поправкой на новые колонки таблиц.
Комплект берётся из папки кандидата (её файлы побайтово равны записям
штатного архива, 06-zip-mvb_build_product_zip.txt). Всё — во временном
каталоге с отдельным профилем LibreOffice. Это НЕ независимая проверка."""
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import docx
import openpyxl
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import test_s1_candidate as T  # noqa: E402

K = T.C
D = lambda s: dt.datetime.strptime(s, "%d.%m.%Y")  # noqa: E731
money = lambda x: f"{x:,.2f}".replace(",", " ").replace(".", ",")  # noqa: E731
ACTS = [("А-1", "КС-2 № 1 от 14.04.2026", 400000, "14.04.2026", "14.05.2026"),
        ("А-2", "КС-2 № 2 от 19.05.2026", 300000, "19.05.2026", "18.06.2026"),
        ("А-3", "КС-2 № 3 от 16.06.2026", 200000, "16.06.2026", "16.07.2026")]
Q_YES = {"q1", "q2", "q11", "q12", "q15"}
SC = {
    "C1": dict(q={}, ctrl=[
        ("20.07.2026", "Приглашение на переговоры, исх. № 30", "24.07.2026", "Не вышел на переговоры"),
        ("27.07.2026", "Уведомление о просрочке, исх. № 31", "07.08.2026", "Молчание после срока"),
        ("10.08.2026", "Претензия, исх. № 35", "09.09.2026", "Молчание после срока")],
        acts08=[0, 1, 2], calc="10.08.2026", att={}),
    "C3": dict(q={"q14": "Да"}, ctrl=[
        ("01.07.2026", "Входящее: гарантийное письмо исх. № 118 — оплата до 31.07.2026", "31.07.2026", "Прислал гарантийное письмо без соглашения"),
        ("05.08.2026", "Протокол переговоров (обещание оплатить до 14.08.2026)", "14.08.2026", "Обещал оплатить в названную дату"),
        ("17.08.2026", "Претензия, исх. № 40", "16.09.2026", "Молчание после срока")],
        acts08=[0, 1, 2], calc="17.08.2026",
        att={19: ("исх. № 118 от 01.07.2026", 1, "Копия", "Да", "Да", "/Входящие/118", "Да")}),
    "C4": dict(q={"q6": "Да", "q17": "Да"}, ctrl=[
        ("20.07.2026", "Приглашение на переговоры, исх. № 30", "24.07.2026", "Не вышел на переговоры"),
        ("27.07.2026", "Уведомление о просрочке, исх. № 31", "07.08.2026", "Молчание после срока"),
        ("06.08.2026", "Входящее: возражения исх. № 131 (акт № 2 — объём; акт № 3 — 50 000 вне сметы)", "", "Возражает по сумме или вернул акт сверки с расхождением"),
        ("10.08.2026", "Претензия, исх. № 35 (только акт № 1)", "09.09.2026", "Молчание после срока")],
        acts08=[0], calc="10.08.2026",
        att={22: ("исх. № 131 от 05.08.2026", 2, "Копия", "Нет", "Да", "/Входящие/131", "Да")}),
}
COMMON = {"НАИМЕНОВАНИЕ_ЗАКАЗЧИКА": "ООО «Условный Генподряд» (вымышл.)", "НАИМЕНОВАНИЕ_СУБПОДРЯДЧИКА": "ООО «Тестовый Монтаж» (вымышл.)",
          "ИНН_ЗАКАЗЧИКА": "0000000002", "ОГРН_ЗАКАЗЧИКА": "0000000000002", "ИНН_СУБПОДРЯДЧИКА": "0000000001", "ОГРН_СУБПОДРЯДЧИКА": "0000000000001",
          "АДРЕС_ЗАКАЗЧИКА": "000002, г. Условный, ул. Примерная, д. 2", "АДРЕС_ПО_ДОГОВОРУ": "000002, г. Условный, а/я 2",
          "АДРЕС_СУБПОДРЯДЧИКА": "000001, г. Условный, ул. Тестовая, д. 1", "БАНКОВСКИЕ_РЕКВИЗИТЫ": "р/с 00000000000000000001, БИК 000000001",
          "НОМЕР_ДОГОВОРА": "СП-14/26", "ДАТА_ДОГОВОРА": "10.02.2026", "ПУНКТ_ДОГОВОРА_ОБ_ОПЛАТЕ": "4.3", "ДОЛЖНОСТЬ_ПОДПИСАНТА": "Генеральный директор",
          "ОСНОВАНИЕ_ПОЛНОМОЧИЙ": "действует на основании устава", "ФИО": "Тестов Т. Т.", "ПРЕДМЕТ_ДОГОВОРА": "монтажных работ",
          "ОБЪЕКТ": "«Условный жилой дом, корпус 1»", "СРОК_ОПЛАТЫ": "в течение 30 календарных дней с даты подписания акта обеими сторонами",
          "СРОК_ОТВЕТА": "10 рабочих дней"}


def walk(el, parent):
    for ch in el.iterchildren():
        tag = ch.tag.split("}")[1]
        if tag == "p":
            yield Paragraph(ch, parent)
        elif tag == "tbl":
            t, seen = Table(ch, parent), set()
            for r in t.rows:
                for c in r.cells:
                    if id(c._tc) not in seen:
                        seen.add(id(c._tc))
                        yield from walk(c._tc, c)


def fill_docx(src, dst, vals, tables=None):
    d = docx.Document(src)
    счёт = {}

    def rep(m):
        k = m.group(1)
        v = vals.get(k, COMMON.get(k))
        if v is None:
            return m.group(0)
        if isinstance(v, list):
            i = счёт.get(k, 0)
            счёт[k] = i + 1
            return v[min(i, len(v) - 1)]
        return v
    for p in walk(d.element.body, d):
        if "{{" in p.text or "[с учётом" in p.text or "[Если" in p.text:
            t = re.sub(r"\[с учётом дополнительного соглашения[^\]]*\]\s*", "", p.text)
            t = re.sub(r"\[Если претензия на них ссылается\]\s*", "", t)
            if p.runs:
                p.runs[0].text = re.sub(r"\{\{([^}]*)\}\}", rep, t)
                for r in p.runs[1:]:
                    r.text = ""
    for ti, rows in (tables or {}).items():
        for ri, row in enumerate(rows):
            for ci, val in enumerate(row):
                c = d.tables[ti].rows[1 + ri].cells[ci]
                (c.paragraphs[0].runs[0].__setattr__("text", str(val)) if c.paragraphs[0].runs
                 else c.paragraphs[0].add_run(str(val)))
    d.save(dst)
    return [m for p in walk(d.element.body, d) for m in re.findall(r"\{\{[^}]*\}\}", p.text)]


def soffice(tmp, fmt, outdir, files):
    subprocess.run(["soffice", f"-env:UserInstallation=file://{tmp}/profile", "--headless", "--norestore",
                    "--convert-to", fmt, "--outdir", str(outdir), *map(str, files)],
                   check=True, capture_output=True, timeout=600)


def pdf_pages(p: Path) -> int:
    out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="s1-walk-"))
    try:
        for name, sc in SC.items():
            o = tmp / name
            o.mkdir()
            print(f"##### {name}")
            # 02: детальная проверка по ответам сценария, последний день оплаты, контроль ответа
            wb = openpyxl.load_workbook(K / "02-proverka-i-kontrol-otveta.xlsx")
            ws = wb["Маршрут"]
            import build_s1_candidate as B
            for i, (q, _) in enumerate(B.QUESTIONS):
                ws[f"C{5 + i}"] = sc["q"].get(q, "Да" if q in Q_YES else "Нет")
            ws["C27"] = D("14.05.2026")
            ws = wb["Контроль ответа"]
            for i, (b, c, d_, f) in enumerate(sc["ctrl"]):
                r = 5 + i
                ws[f"B{r}"], ws[f"C{r}"], ws[f"F{r}"] = D(b), c, f
                ws[f"D{r}"] = D(d_) if d_ else None
            wb.save(o / "02.xlsx")
            # 04: три акта начислением, сроки по актам, входящие в реестре приложений
            wb = openpyxl.load_workbook(K / "04-uchet-raschetov-i-otpravok.xlsx")
            vz, da = wb["Взаиморасчёты"], wb["Долг по актам"]
            for i, (aid, doc_, s, signed, last) in enumerate(ACTS):
                r = 5 + i
                vz[f"B{r}"], vz[f"C{r}"], vz[f"D{r}"], vz[f"E{r}"], vz[f"F{r}"] = D(signed), "Начисление по акту", doc_, s, aid
                da[f"B{r}"], da[f"C{r}"], da[f"D{r}"] = aid, doc_, D(last)
            pr = wb["Реестр приложений"]
            for r, v in sc["att"].items():
                for col, x in zip("CDEFGHI", v):
                    pr[f"{col}{r}"] = x
            wb.save(o / "04.xlsx")
            # 08 на дату претензии (тестовая ставка 20 % — только арифметика, не ставка ЦБ)
            wb = openpyxl.load_workbook(K / "08-raschet-procentov-395.xlsx")
            wb["Ввод"]["B4"], wb["Ввод"]["A12"], wb["Ввод"]["B12"] = D(sc["calc"]), D("01.01.2026"), 20
            for j, i in enumerate(sc["acts08"]):
                aid, doc_, s, _, last = ACTS[i]
                r = 5 + j
                a = wb["Акты"]
                a[f"B{r}"], a[f"C{r}"], a[f"D{r}"], a[f"E{r}"], a[f"F{r}"] = aid, doc_, s, D(last) + dt.timedelta(1), s
            wb.save(o / "08.xlsx")
            r = T.пересчитать({"02": o / "02.xlsx", "04": o / "04.xlsx", "08": o / "08.xlsx"}, tmp / f"lo-{name}")
            m = openpyxl.load_workbook(r["02"], data_only=True)
            mr = m["Маршрут"]
            print("02 Маршрут: ИТОГ =", mr["C23"].value, "| Ещё границы =", mr["C26"].value or "—", "| первый день просрочки =", mr["C28"].value)
            print("   Следующий шаг =", mr["C24"].value)
            ko = m["Контроль ответа"]
            for i in range(len(sc["ctrl"])):
                print(f"02 КО стр. {i + 1}: «{ko[f'F{5 + i}'].value}» → {ko[f'G{5 + i}'].value}")
            w4 = openpyxl.load_workbook(r["04"], data_only=True)
            vz = w4["Взаиморасчёты"]
            print("04 Взаиморасчёты: J5..J7 =", [vz[f"J{i}"].value for i in (5, 6, 7)], "| J8..J504 пусто:",
                  all(vz[f"J{i}"].value in (None, "") for i in range(8, 505)), "| M10 =", vz["M10"].value)
            da = w4["Долг по актам"]
            print("04 Долг по актам H/K/L:", [(da[f"H{i}"].value, da[f"K{i}"].value, da[f"L{i}"].value) for i in (5, 6, 7)])
            ош = [(w.title, c.coordinate) for w in w4.worksheets for row in w.iter_rows() for c in row
                  if isinstance(c.value, str) and c.value.startswith("#")]
            print("04 ячеек с ошибкой #:", len(ош))
            w8 = openpyxl.load_workbook(r["08"], data_only=True)["Расчёт"]
            pct = w8["D3"].value
            print("08 Расчёт:", w8["D2"].value, "| Проценты итого =", pct)
            # документы: 06 (С-1, С-4), 09 (все), 05 раздел А (С-3), 10 (С-1 иск, С-4 опись)
            idx = sc["acts08"]
            debt = sum(ACTS[i][2] for i in idx)
            docs = {}
            if name in ("C1", "C4"):
                docs["06"] = fill_docx(K / "06-uvedomlenie-o-prosrochke.docx", o / "06.docx",
                                       {"ИСХОДЯЩИЙ_НОМЕР": "31", "ДАТА_ДОКУМЕНТА": "27.07.2026", "СУММА_ДОЛГА": money(900000),
                                        "ДАТА": ["07.08.2026", "27.07.2026"]},
                                       {0: [[n, a[1], money(a[2]), a[4], "0,00", money(a[2])] for n, a in enumerate(ACTS, 1)]})
            docs["09"] = fill_docx(K / "09-pretenziya.docx", o / "09.docx",
                                   {"ИСХОДЯЩИЙ_НОМЕР": "35", "ДАТА_ДОКУМЕНТА": sc["calc"], "СУММА_ДОЛГА": money(debt),
                                    "СУММА_ПРОЦЕНТОВ": money(pct), "ДАТА_РАСЧЁТА": sc["calc"]},
                                   {0: [[n, ACTS[i][1], ACTS[i][3], money(ACTS[i][2]), ACTS[i][3], ACTS[i][4]] for n, i in enumerate(idx, 1)],
                                    1: [["—", "оплат не было", "—", "0,00"]]})
            if name == "C3":
                docs["05"] = fill_docx(K / "05-peregovory-i-perenos-sroka.docx", o / "05.docx", {"ДАТА": "05.08.2026"},
                                       {1: [[1, "Заказчик оплатит 900 000 руб.", "до 14.08.2026", "Условнов У. У."]]})
            if name == "C1":
                docs["10"] = fill_docx(K / "10-obrashchenie-v-sud.docx", o / "10.docx",
                                       {"НАИМЕНОВАНИЕ_СУДА": "Условной области", "ИНН": ["0000000001", "0000000002"],
                                        "ОГРН": ["0000000000001", "0000000000002"], "АДРЕС": ["г. Условный, ул. Тестовая, д. 1", "г. Условный, ул. Примерная, д. 2"],
                                        "ТЕЛЕФОН": "+7 000 000-00-01", "EMAIL": "test@example.test", "ЦЕНА_ИСКА": "[долг + проценты на дату иска]",
                                        "ГОСПОШЛИНА": "[по калькулятору]", "СУММА_ПО_АКТАМ": money(900000),
                                        "ПЕРЕЧЕНЬ_АКТОВ": "КС-2 № 1, № 2, № 3", "ПУНКТ": "4.3", "ОПЛАЧЕНО": "0,00", "СУММА_ДОЛГА": money(900000),
                                        "ДАТА_ПО": "30.09.2026", "СУММА_ПРОЦЕНТОВ": "[на дату иска, файл 08]", "НОМЕР": "35",
                                        "ДАТА": ["10.08.2026", "30.09.2026"], "ДАТА_НАПРАВЛЕНИЯ": "10.08.2026", "СПОСОБ": "ценным письмом с описью",
                                        "ТРЕК": "ТРЕК-ТЕСТ-0002", "ОТВЕТ_НЕ_ПОЛУЧЕН / ПОЛУЧЕН_ОТКАЗ_БЕЗ_МОТИВОВ": "ответ не получен",
                                        "ДОЛЖНОСТЬ": "Генеральный директор"})
            pdf = o / "pdf"
            soffice(tmp / f"lo-{name}", "pdf", pdf, [o / f"{k}.docx" for k in docs])
            for k, left in docs.items():
                txt = subprocess.run(["pdftotext", str(pdf / f"{k}.pdf"), "-"], capture_output=True, text=True).stdout
                print(f"{k}.docx → PDF {pdf_pages(pdf / f'{k}.pdf')} стр.; незаполненных полей: {len(left)} {sorted(set(left))[:6]}")
                if k == "09":
                    п2 = re.search(r"2\. Согласно.*?руб\.", txt.replace("\n", " "))
                    print("   п. 2:", п2.group(0) if п2 else "не найден")
            if name == "C1":
                soffice(tmp / f"lo-{name}", "pdf", pdf, [r["04"]])
                print("04 книга учёта → PDF", pdf_pages(pdf / f"{Path(r['04']).stem}.pdf"), "стр.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


main()
