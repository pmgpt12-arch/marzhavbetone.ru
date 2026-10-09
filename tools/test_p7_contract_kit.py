#!/usr/bin/env python3
"""P7 отдаёт договор и протокол, а не их оглавление.

Замер 28.09.2026 (#293 строка p7, #300 P7-01, #302): в комплекте
«Договор субподряда: образец, красные флаги, протокол разногласий»
договор был 199 словами тезисов («Цена: твёрдая / приблизительная / по
единичным расценкам»), протокол разногласий — одной позицией на 72 слова, а
`00-START-HERE.txt` отправлял первым открыть инструкцию, которая «говорит, с
чего начинать в двух случаях», — двух случаев в ней не было, и называла она
комплект прежним именем.

Проверяется ровно это:
1. `01` — сквозной договор: четырнадцать разделов, пункты, приложения,
   подписной блок; прежних тезисов нет.
2. `10` — рабочая форма протокола: преамбула со сторонами, таблица
   «Редакция Заказчика / Редакция Подрядчика» больше чем на одну позицию,
   подписи; каждая позиция ссылается на пункт, который есть в `01`.
   Фразы об автоматическом последствии подписи без отметки нет (Н-1 из
   Normative_Check_Avans_Landing_2026-08-11).
3. START-HERE и инструкция говорят одно: два случая из §2 названы в
   инструкции, перечень §4 и «файлов в архиве: N» совпадают с тем, что
   действительно уходит покупателю.
4. В документах для второй стороны нет марки продавца (#300 P7-02, X-06).
5. Файлы в выдаче — продукт генератора `products-storage/build_paid_03.py`:
   два прогона дают одинаковые байты, и они совпадают с лежащими в
   репозитории.

Запуск без pytest: python3 tools/test_p7_contract_kit.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_packages as cp                              # noqa: E402
from docx_text import paragraphs                         # noqa: E402

KIT = cp.STORAGE / "03-dogovor-podryada"
GENERATOR = cp.STORAGE / "build_paid_03.py"
CONFIG = cp.ROOT / "products-config.php"

CONTRACT = KIT / "01-dogovor-subpodryada.docx"
PROTOCOL = KIT / "10-protokol-raznoglasiy.docx"
INSTRUCTION = KIT / "00-INSTRUKCIYA.docx"
START = KIT / "00-START-HERE.txt"

# Двух случаев, которые START-HERE §2 обещает найти в инструкции
CASES = ("Вам прислали договор на подпись", "Договор предлагаете вы")

SECTIONS = (
    "ПРЕДМЕТ ДОГОВОРА", "СТОИМОСТЬ РАБОТ И ПОРЯДОК РАСЧЕТОВ",
    "СРОКИ ВЫПОЛНЕНИЯ РАБОТ", "ОБЯЗАННОСТИ ПОДРЯДЧИКА",
    "ОБЯЗАННОСТИ ЗАКАЗЧИКА", "СДАЧА И ПРИЕМКА ВЫПОЛНЕННЫХ РАБОТ",
    "БЕЗОПАСНОСТЬ РАБОТ И ОХРАНА ТРУДА",
    "ГАРАНТИЙНЫЕ ОБЯЗАТЕЛЬСТВА ПОДРЯДЧИКА", "ОТВЕТСТВЕННОСТЬ СТОРОН",
    "ПОРЯДОК РАЗРЕШЕНИЯ СПОРОВ", "ПОРЯДОК ИЗМЕНЕНИЯ И ДОПОЛНЕНИЯ ДОГОВОРА",
    "КОНТРОЛЬ И НАДЗОР ЗА РЕАЛИЗАЦИЕЙ ДОГОВОРА", "ПРОЧИЕ УСЛОВИЯ",
    "АДРЕСА, БАНКОВСКИЕ РЕКВИЗИТЫ И ПОДПИСИ СТОРОН",
)
SELLER_MARKS = ("МАРЖА В БЕТОНЕ", "РАБОЧИЙ ШАБЛОН", "marzhavbetone.ru")
CLAUSE = re.compile(r"^(?:П\.\s*)?(\d{1,2}(?:\.\d{1,2}){1,2})\.?(?:\s|$)")


def words(path: Path) -> int:
    return sum(len(p.split()) for p in paragraphs(path))


def xml_parts(path: Path, prefix: str) -> str:
    import zipfile
    with zipfile.ZipFile(path) as archive:
        return "".join(archive.read(n).decode("utf-8", "replace")
                       for n in archive.namelist()
                       if n.startswith(prefix) and n.endswith(".xml"))


def tables(path: Path) -> list[list[list[str]]]:
    """Таблицы документа — строками, строка — текстом ячеек."""
    xml = xml_parts(path, "word/document.xml")
    out = []
    for table in re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S):
        rows = []
        for row in re.findall(r"<w:tr[ >].*?</w:tr>", table, re.S):
            cells = []
            for cell in re.findall(r"<w:tc>.*?</w:tc>", row, re.S):
                text = " ".join(
                    "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p))
                    for p in re.findall(r"<w:p[ >].*?</w:p>", cell, re.S))
                cells.append(re.sub(r"\s+", " ", text).strip())
            rows.append(cells)
        out.append(rows)
    return out


def positions(path: Path) -> list[list[str]]:
    """Таблица позиций протокола — та, у которой шапка из двух редакций."""
    for rows in tables(path):
        if rows and [c.lower() for c in rows[0]] == [
                "редакция заказчика", "редакция подрядчика"]:
            return rows
    return []


def clause_numbers(path: Path) -> set[str]:
    return {m.group(1) for line in paragraphs(path)
            if (m := CLAUSE.match(line))}


def delivered_names() -> list[str]:
    return sorted(cp.delivered(KIT))


def start_here_section(text: str, number: int) -> str:
    match = re.search(rf"\n{number}\. [^\n]+\n(.*?)(?=\n\d\. [А-ЯЁ]|\n-{{10,}})",
                      text, re.S)
    return match.group(1) if match else ""


def test_договор_сквозной_текст_а_не_тезисы() -> None:
    text = "\n".join(paragraphs(CONTRACT))
    assert "твёрдая / приблизительная / по единичным расценкам" not in text, \
        "в 01 остались прежние тезисы о цене"
    assert words(CONTRACT) >= 4000, (
        f"01: {words(CONTRACT)} слов — это не договор, а оглавление")
    missing = [s for s in SECTIONS if s not in text]
    assert not missing, f"01: нет разделов {missing}"
    for clause in ("1.1", "2.7", "6.8", "8.4", "9.6", "11.4", "13.7"):
        assert clause in clause_numbers(CONTRACT), f"01: нет пункта {clause}"
    assert "Приложение № 1" in text and "Приложение № 2" in text, \
        "01: приложения не названы"
    assert "{{НАИМЕНОВАНИЕ_ЗАКАЗЧИКА}}" in text and \
        "{{НАИМЕНОВАНИЕ_ПОДРЯДЧИКА}}" in text, "01: нет полей сторон"


def test_протокол_рабочая_форма_а_не_одна_строка() -> None:
    rows = positions(PROTOCOL)
    assert rows, ("10: нет таблицы позиций с шапкой «Редакция Заказчика / "
                  "Редакция Подрядчика»")
    body = rows[1:]
    assert len(body) >= 20, f"10: позиций {len(body)} — это не протокол"
    text = "\n".join(paragraphs(PROTOCOL))
    assert words(PROTOCOL) >= 1500, f"10: {words(PROTOCOL)} слов"
    assert "ПРОТОКОЛ РАЗНОГЛАСИЙ" in text
    assert "заключили настоящий протокол разногласий" in text, \
        "10: нет преамбулы"
    assert "{{НОМЕР_ДОГОВОРА}}" in text and "{{ФИО_ПОДПИСАНТА}}" in text, \
        "10: нет полей договора и подписанта"
    assert "считается подписанным в редакции" not in text, (
        "10: автоматизм подписи без отметки — расхождение Н-1")


def test_позиции_протокола_ссылаются_на_пункты_договора() -> None:
    contract = clause_numbers(CONTRACT)
    new = {"3.5", "4.1.8", "4.1.9"}          # пункты, которых в договоре нет
    orphans = []
    body = positions(PROTOCOL)[1:]
    assert body, "10: позиций нет — сверять не с чем"
    for left, right in (r[:2] for r in body):
        match = CLAUSE.match(left) or CLAUSE.match(right)
        assert match, f"10: позиция без номера пункта: {left[:60]!r}"
        number = match.group(1)
        if number not in contract and number not in new:
            orphans.append(number)
    assert not orphans, f"10: пунктов {orphans} нет в договоре 01"


def test_start_here_и_инструкция_говорят_одно() -> None:
    start = START.read_text(encoding="utf-8")
    first = start_here_section(start, 2)
    instruction = "\n".join(paragraphs(INSTRUCTION))
    for case in CASES:
        assert case in first, f"START-HERE §2 не называет случай «{case}»"
        assert case in instruction, f"инструкция не разбирает случай «{case}»"
    opened = re.findall(r"\b(\d\d-[A-Za-z-]+\.(?:pdf|docx|xlsx|txt))", first)
    assert opened and all(n in delivered_names() for n in opened), (
        f"START-HERE §2 отправляет к файлу, которого нет в архиве: {opened}")
    name = re.search(r"'p7'\s*=>\s*\[\s*'name'\s*=>\s*'([^']+)'",
                     CONFIG.read_text(encoding="utf-8")).group(1)
    assert name in instruction, "инструкция называет комплект не его именем"
    assert "«Договор подряда»" not in instruction, \
        "в инструкции прежнее имя пакета"
    for file in delivered_names():
        assert file in instruction, f"инструкция не называет файл {file}"


def test_start_here_перечисляет_то_что_уходит_покупателю() -> None:
    start = START.read_text(encoding="utf-8")
    listed = sorted(re.findall(r"^\s{3}(\d\d-[A-Za-z0-9-]+\.[a-z]+)",
                               start_here_section(start, 4), re.M))
    assert listed == delivered_names(), (
        f"START-HERE §4 {listed} ≠ архив {delivered_names()}")
    count = re.search(r"файлов в архиве: (\d+)", start)
    assert count and int(count.group(1)) == len(delivered_names()), (
        "START-HERE: число файлов не совпадает с архивом")


def test_pdf_инструкции_собран_из_того_же_текста() -> None:
    if not shutil.which("pdftotext"):
        print("  pdftotext нет — сверка PDF не запускалась")
        return
    pdf = subprocess.run(["pdftotext", "-layout", str(KIT / "00-INSTRUKCIYA.pdf"),
                          "-"], capture_output=True, text=True).stdout
    flat = re.sub(r"\s+", " ", pdf)
    for case in CASES:
        assert case in flat, f"00-INSTRUKCIYA.pdf отстал от .docx: нет «{case}»"


def test_в_документах_для_второй_стороны_нет_марки_продавца() -> None:
    for path in (CONTRACT, PROTOCOL):
        marks = xml_parts(path, "word/header") + xml_parts(path, "word/footer") \
            + "\n".join(paragraphs(path))
        found = [m for m in SELLER_MARKS if m in marks]
        assert not found, f"{path.name}: марка продавца {found}"


def load_generator():
    assert GENERATOR.is_file(), f"нет генератора {GENERATOR.name}"
    spec = importlib.util.spec_from_file_location("build_paid_03", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digests(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.iterdir())
            if p.suffix in (".docx", ".txt") and p.name.startswith(("00-", "01-", "10-"))}


def test_генератор_воспроизводит_выдачу_побайтово() -> None:
    generator = load_generator()
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        generator.build(Path(a), pdf=False)
        generator.build(Path(b), pdf=False)
        first, second = digests(Path(a)), digests(Path(b))
    assert first, "генератор ничего не записал"
    assert first == second, "два прогона генератора дали разные байты"
    repo = {k: v for k, v in digests(KIT).items() if k in first}
    assert repo == first, (
        "файлы P7 в репозитории не совпадают с выходом генератора: "
        f"{sorted(k for k in first if repo.get(k) != first[k])}")


def main() -> int:
    провал = 0
    for имя, проверка in sorted(globals().items()):
        if not имя.startswith("test_"):
            continue
        try:
            проверка()
            print(f"ok      {имя}")
        except AssertionError as ошибка:
            провал += 1
            print(f"ПРОВАЛ  {имя}: {ошибка}")
    return 1 if провал else 0




def test_protocol_column_headers_repeat_on_printed_pages() -> None:
    from docx import Document
    from docx.oxml.ns import qn
    tables = [t for t in Document(PROTOCOL).tables
              if [c.text.strip() for c in t.rows[0].cells] ==
              ["Редакция Заказчика", "Редакция Подрядчика"]]
    assert len(tables) == 1, "protocol column header table missing or ambiguous"
    assert tables[0].rows[0]._tr.find("./" + qn("w:trPr") + "/" + qn("w:tblHeader")) is not None, "protocol first row must repeat on printed pages"

if __name__ == "__main__":
    sys.exit(main())
