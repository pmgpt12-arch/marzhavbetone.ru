#!/usr/bin/env python3
"""T2: опись уходит второй стороне бумагой, а про проверку текстов выдача
и страница товара говорят одно и то же.

Две находки аудита выдачи (PR 300, T2-01 и T2-02; карточка #301).

T2-01. `03-opis-peredavaemogo-komplekta.xlsx` печатался на 19 страниц: на
первой 3 колонки из 9, подписи на четвёртой, и в печать уходили подсказки
продавца — дисклеймер, «жёлтые ячейки заполняете вы», «если принимающий
подписывать отказывается — почтой с описью вложения». Опись подписывает
принимающий; советы против него в подписываемом документе стоять не должны.

T2-02. Файлы утверждали «Тексты прошли вычитку юристом в типовой
редакции», страница — «вычитку юристом не проходили». Заключения юриста в
репозиториях нет, поэтому сняты оба утверждения, и во всех точках стоит одна
фраза — ФРАЗА ниже. Её источник — константа PROVERKA_T2 в
`ai-business-os/projects/marzha_v_betone/product/build/lib.js`.

Книга разбирается стандартной библиотекой (zipfile, ElementTree), без
openpyxl: гейт сайта его не ставит. Печать в PDF проверяется, только если в
окружении есть LibreOffice (`soffice`) и `pdftotext`; без них эта часть
пропускается с причиной, а остальные проверки идут.

Запуск без pytest: python3 tools/test_t2_opis_print.py
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parent.parent
ПАПКА = КОРЕНЬ / "products-storage" / "14-peredacha-id-pod-podpis"
ОПИСЬ = ПАПКА / "03-opis-peredavaemogo-komplekta.xlsx"
DOCX = ["01-slovar-poley.docx", "02-soprovoditelnoe-pismo-peredachi.docx",
        "04-akt-priema-peredachi-id.docx", "05-poryadok-peredachi-id.docx"]
СТРАНИЦА = КОРЕНЬ / "products" / "t2-peredacha-ispolnitelnoy-dokumentacii.html"

ФРАЗА = ("Письменного заключения юриста по этим текстам нет, нормативная "
         "сверка форм и порядка передачи по ним не проводилась.")

# Любое утверждение о вычитке — положительное или отрицательное — в T2
# больше не стоит нигде: подтвердить нечем ни то, ни другое
ВЫЧИТКА = re.compile(r"вычитк", re.I)

# Подсказки, которые до правки стояли на листе «Опись» (A2, A8, E4, H132,
# F133, A136). В книге они остаются — на листе «Как заполнять».
ПОДСКАЗКИ = [
    "Прочитайте до того, как заполнять",
    "Жёлтые ячейки заполняете вы",
    "Номер и дата описи переносятся",
    "Эти три числа переносятся",
    "целевое значение ноль",
    "Если принимающий подписывать отказывается",
]

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def сжать(текст: str) -> str:
    return " ".join(текст.split())


# ---------------------------------------------------------------- книга ---

def _книга(путь: Path) -> dict:
    """Имя листа → {ячейки: {адрес: текст}, xml: корень листа};
    плюс определённые имена книги."""
    with zipfile.ZipFile(путь) as z:
        общие = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{M}si"):
                общие.append("".join(t.text or "" for t in si.iter(f"{M}t")))
        книга = ET.fromstring(z.read("xl/workbook.xml"))
        связи = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        цели = {r.get("Id"): r.get("Target") for r in связи}
        листы = {}
        порядок = []
        for лист in книга.iter(f"{M}sheet"):
            цель = цели[лист.get(f"{R}id")].lstrip("/")
            цель = цель if цель.startswith("xl/") else "xl/" + цель
            корень = ET.fromstring(z.read(цель))
            ячейки = {}
            for c in корень.iter(f"{M}c"):
                v = c.find(f"{M}v")
                if c.get("t") == "s" and v is not None:
                    ячейки[c.get("r")] = общие[int(v.text)]
                elif c.get("t") == "inlineStr":
                    ячейки[c.get("r")] = "".join(t.text or "" for t in c.iter(f"{M}t"))
                elif c.find(f"{M}f") is not None:
                    ячейки[c.get("r")] = "=" + (c.find(f"{M}f").text or "")
            листы[лист.get("name")] = {"ячейки": ячейки, "xml": корень}
            порядок.append(лист.get("name"))
        имена = {}
        for dn in книга.iter(f"{M}definedName"):
            имена.setdefault(dn.get("name"), {})[порядок[int(dn.get("localSheetId", 0))]] = dn.text
    return {"листы": листы, "имена": имена}


def _адрес(адрес: str) -> tuple[int, int]:
    буквы, цифры = re.match(r"\$?([A-Z]+)\$?(\d+)", адрес).groups()
    колонка = 0
    for б in буквы:
        колонка = колонка * 26 + ord(б) - 64
    return колонка, int(цифры)


def _область(книга: dict) -> tuple[int, int, int, int]:
    область = книга["имена"].get("_xlnm.Print_Area", {}).get("Опись")
    assert область, "область печати листа «Опись» не задана"
    диапазон = область.split("!")[-1].split(",")[0]
    начало, конец = диапазон.split(":")
    (к1, с1), (к2, с2) = _адрес(начало), _адрес(конец)
    return к1, с1, к2, с2


def test_опись_печатается_альбомом_в_ширину_страницы():
    книга = _книга(ОПИСЬ)
    лист = книга["листы"]["Опись"]["xml"]
    настройка = лист.find(f"{M}pageSetup")
    assert настройка is not None, "у листа «Опись» нет параметров печати"
    assert настройка.get("orientation") == "landscape"
    assert настройка.get("paperSize") == "9", "не A4"
    assert настройка.get("fitToWidth") == "1"
    assert настройка.get("fitToHeight") == "0"
    свойства = лист.find(f"{M}sheetPr/{M}pageSetUpPr")
    assert свойства is not None and свойства.get("fitToPage") in ("1", "true")
    шапка = книга["имена"].get("_xlnm.Print_Titles", {}).get("Опись")
    assert шапка, "шапка таблицы не повторяется на страницах"


def test_область_печати_все_колонки_и_кончается_подписями():
    книга = _книга(ОПИСЬ)
    к1, с1, к2, с2 = _область(книга)
    assert (к1, с1) == (1, 1)
    assert к2 == 9, "в печать должны войти все девять колонок"
    ячейки = книга["листы"]["Опись"]["ячейки"]
    подписи = [_адрес(а)[1] for а, т in ячейки.items() if т in ("Передал", "Принял")]
    assert подписи and max(подписи) == с2, "область печати должна кончаться подписями"


def test_в_области_печати_нет_служебного_текста():
    книга = _книга(ОПИСЬ)
    к1, с1, к2, с2 = _область(книга)
    for адрес, текст in книга["листы"]["Опись"]["ячейки"].items():
        к, с = _адрес(адрес)
        if not (к1 <= к <= к2 and с1 <= с <= с2) or текст.startswith("="):
            continue
        for подсказка in ПОДСКАЗКИ:
            assert подсказка not in текст, f"{адрес}: {подсказка}"
        assert not ВЫЧИТКА.search(текст), адрес
        # Подпись поля короче подсказки: самая длинная — «должность, фамилия
        # и инициалы, подпись, дата, основание полномочий», 69 знаков
        assert len(текст) <= 80, f"{адрес}: похоже на подсказку: {текст[:60]}"


def test_подсказки_и_фраза_на_листе_как_заполнять():
    ячейки = _книга(ОПИСЬ)["листы"]["Как заполнять"]["ячейки"]
    текст = сжать(" ".join(ячейки.values()))
    for подсказка in ПОДСКАЗКИ:
        assert подсказка in текст, f"подсказка потерялась: {подсказка}"
    assert ФРАЗА in текст
    assert not ВЫЧИТКА.search(текст)


# --------------------------------------------------- фраза во всех точках ---

def _текст_docx(путь: Path) -> str:
    with zipfile.ZipFile(путь) as z:
        корень = ET.fromstring(z.read("word/document.xml"))
    абзацы = ["".join(t.text or "" for t in p.iter(f"{W}t")) for p in корень.iter(f"{W}p")]
    return сжать(" ".join(абзацы))


def _текст_страницы() -> str:
    сырой = СТРАНИЦА.read_text(encoding="utf-8")
    return сжать(html.unescape(re.sub(r"<[^>]+>", " ", сырой)))


def test_фраза_в_каждом_docx_и_нет_вычитки():
    for имя in DOCX:
        текст = _текст_docx(ПАПКА / имя)
        assert ФРАЗА in текст, f"{имя}: нет фразы о проверке"
        assert not ВЫЧИТКА.search(текст), f"{имя}: утверждение о вычитке"


def test_фраза_в_start_here():
    текст = сжать((ПАПКА / "00-START-HERE.txt").read_text(encoding="utf-8"))
    assert ФРАЗА in текст
    assert not ВЫЧИТКА.search(текст)


def test_страница_говорит_то_же_что_файлы():
    текст = _текст_страницы()
    # Тело страницы, FAQ и его разметка schema.org — три вхождения
    assert текст.count(ФРАЗА) == 3, текст.count(ФРАЗА)
    assert not ВЫЧИТКА.search(текст)


# ------------------------------------------------------------- печать PDF ---

def _pdf_описи(tmp: Path) -> Path | None:
    if not (shutil.which("soffice") and shutil.which("pdftotext")):
        return None
    копия = tmp / "opis.xlsx"
    shutil.copyfile(ОПИСЬ, копия)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", str(tmp), str(копия)],
                   check=True, capture_output=True, timeout=180)
    return tmp / "opis.pdf"


def test_pdf_описи_без_подсказок_и_без_разрыва_колонок():
    with tempfile.TemporaryDirectory() as tmp:
        pdf = _pdf_описи(Path(tmp))
        if pdf is None:
            print("  пропуск: нет soffice или pdftotext — печать не проверялась")
            return
        страницы = []
        номер = 1
        while True:
            вывод = subprocess.run(["pdftotext", "-f", str(номер), "-l", str(номер),
                                    "-layout", str(pdf), "-"],
                                   capture_output=True, text=True)
            if вывод.returncode != 0:
                break
            страницы.append(вывод.stdout)
            номер += 1
        # Лист «Опись» — страницы до первой страницы листа «Как заполнять»
        опись = []
        for текст in страницы:
            if "Как заполнять опись" in текст:
                break
            опись.append(текст)
        assert опись, "лист «Опись» не напечатан"
        assert len(опись) <= 4, f"опись печатается на {len(опись)} страниц"
        последняя_колонка = "Примечание"
        for i, текст in enumerate(опись, 1):
            assert "Вид документа" in текст and последняя_колонка in текст, \
                f"стр. {i}: шапка таблицы не целиком — колонки разорваны"
            for подсказка in ПОДСКАЗКИ:
                assert подсказка not in текст, f"стр. {i}: {подсказка}"
            assert not ВЫЧИТКА.search(текст), f"стр. {i}: вычитка"
        assert "Передал" in опись[-1] and "Принял" in опись[-1]
        assert "Итого позиций" in опись[-1], "подписи оторваны от таблицы"


def main() -> int:
    тесты = [(имя, ф) for имя, ф in globals().items()
             if имя.startswith("test_") and callable(ф)]
    упало = 0
    for имя, ф in тесты:
        try:
            ф()
            print(f"ok    {имя}")
        except AssertionError as e:
            упало += 1
            print(f"FAIL  {имя}: {e}")
    print(f"\n{len(тесты) - упало}/{len(тесты)} прошло")
    return 1 if упало else 0


if __name__ == "__main__":
    sys.exit(main())
