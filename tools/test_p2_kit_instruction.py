#!/usr/bin/env python3
"""Инструкция P2 описывает P2: его имя, его файлы, его два случая.

Дефект P2-01 из отчёта PR #300 (issue #305). `00-START-HERE.txt` велит
открыть первым `00-INSTRUKCIYA.pdf` и обещает, что она «разводит два
случая: работы ещё не начаты … и работы уже выполнены без бумаг». В
архиве же лежал общий шаблон линейки: заголовок «Пакет «Допработы без
потерь»» — прежнее имя товара, состав 01–10 без допсоглашений 11 и 12,
разделы, дословно совпадающие с инструкцией P7, и ни одного из двух
обещанных случаев. Проверка состава при этом была зелёной: она считает
файлы, а не читает первый из них.

Что здесь проверяется — только то, что уходит покупателю P2:

1. Инструкция (DOCX и PDF) называет товар текущим именем из
   `products-config.php`, а не прежним, и не несёт фраз общего шаблона.
2. Инструкция перечисляет каждый файл архива.
3. Каждый файл, названный в инструкции или в START-HERE — полным именем
   или номером в скобках, — лежит в архиве. Ссылка на файл, которого
   покупатель не получит, — тот же дефект, что пропущенный файл.
4. Случаи, которые START-HERE §2 обещает найти в инструкции, названы в
   ней заголовками — и в DOCX, и в PDF.
5. PDF не отстал от DOCX: заголовки совпадают.
6. Страница товара, называя число файлов и их форматы, не опускает формат,
   который в архиве есть.

Архив собирается на сервере из папки `products-storage/<dir>` без
служебных файлов (`mvb_build_product_zip`), поэтому «файлы архива» здесь —
та же папка за вычетом того же списка исключений.

PDF читается `pdftotext` (poppler-utils). Без него проверка PDF падает с
пометкой BLOCKED, а не проходит молча.

Запуск: python3 tools/test_p2_kit_instruction.py
    или python3 -m pytest tools/test_p2_kit_instruction.py
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_packages as cp                              # noqa: E402

SITE = cp.STORAGE.parent
SKU = "p2"
KIT = cp.STORAGE / cp.catalog()[SKU]
PAGE = SITE / "products" / "p2-dopolnitelnye-raboty.html"
НЕ_ВЫДАЁТСЯ = cp.NOT_DELIVERED | cp.NOT_LISTED
ИНСТРУКЦИЯ_DOCX = KIT / "00-INSTRUKCIYA.docx"
ИНСТРУКЦИЯ_PDF = KIT / "00-INSTRUKCIYA.pdf"
START_HERE = KIT / "00-START-HERE.txt"

# Прежние имена товара: заголовок инструкции, служебное письмо, манифест
ПРЕЖНИЕ_ИМЕНА = ("Допработы без потерь", "Допы не в подарок")
# Фразы общего шаблона — дословно из инструкции P2 на main b89f081, они же
# стоят в инструкции P7. Каждая про чужую ситуацию или ни про какую.
ОБЩИЙ_ШАБЛОН = (
    "Как внедрить пакет",
    "Быстрый запуск за 60 минут",
    "Если заказчик отказывается подписывать",
    "Проведите один текущий объём по всей цепочке",
    "Комплект передают без реестра",
    "Назначьте владельца каждого реестра",
)

ИМЯ_ФАЙЛА = re.compile(r"\b\d{2}-[A-Za-z0-9-]+\.(?:docx|xlsx|pdf|txt)\b")
# «(10)», «(01–03)», «(11, 12)» — ссылка на файл номером
НОМЕРА_В_СКОБКАХ = re.compile(r"\((\d{2}(?:\s*[–,-]\s*\d{2})*)\)")
ФОРМАТЫ = {".docx": "Word", ".xlsx": "Excel", ".pdf": "PDF"}


# --- чтение ----------------------------------------------------------------

def выдаваемые() -> set[str]:
    return {f.name for f in KIT.iterdir()
            if f.is_file() and f.name not in НЕ_ВЫДАЁТСЯ}


def имя_товара() -> str:
    """«Дополнительные работы: как получить оплату» — из products-config.php."""
    текст = (SITE / "products-config.php").read_text(encoding="utf-8")
    m = re.search(r"'%s'\s*=>\s*\[\s*'name'\s*=>\s*'Комплект «([^»]+)»'" % SKU,
                  текст)
    assert m, f"products-config.php: имя {SKU} не найдено"
    return m.group(1)


def абзацы_docx(путь: Path) -> list[tuple[str, str]]:
    """(стиль, текст) по порядку: абзацы тела, затем ячейки таблиц."""
    with zipfile.ZipFile(путь) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for абзац in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        стиль = re.search(r'<w:pStyle w:val="([^"]+)"', абзац)
        текст = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", абзац))
        if текст.strip():
            out.append((стиль.group(1) if стиль else "", html.unescape(текст)))
    return out


def текст_docx(путь: Path) -> str:
    return "\n".join(t for _, t in абзацы_docx(путь))


def заголовки_docx(путь: Path) -> list[str]:
    return [t.strip() for s, t in абзацы_docx(путь)
            if s.startswith("Heading") or s == "Title"]


def текст_pdf(путь: Path) -> str:
    if not shutil.which("pdftotext"):
        raise AssertionError(
            "BLOCKED: нет pdftotext (poppler-utils) — PDF не прочитан")
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(путь), "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout


def плоско(текст: str) -> str:
    """Переносы строк и повторные пробелы PDF сводятся к одному пробелу."""
    return re.sub(r"\s+", " ", текст.replace("­", "")).strip()


def тексты_инструкции() -> dict[str, str]:
    return {ИНСТРУКЦИЯ_DOCX.name: текст_docx(ИНСТРУКЦИЯ_DOCX),
            ИНСТРУКЦИЯ_PDF.name: текст_pdf(ИНСТРУКЦИЯ_PDF)}


def раздел_start_here(номер: int) -> str:
    текст = START_HERE.read_text(encoding="utf-8")
    m = re.search(r"^%d\.\s.*?(?=^\d+\.\s|\Z)" % номер, текст, re.S | re.M)
    assert m, f"{START_HERE.name}: нет раздела {номер}"
    return m.group(0)


# --- детектор ссылок: отдельно, чтобы проверить его на подложенном тексте --

def ссылки_мимо_архива(текст: str, архив: set[str]) -> list[str]:
    """Имена и номера файлов из текста, которых в архиве нет."""
    номера = {имя[:2] for имя in архив}
    мимо = [имя for имя in ИМЯ_ФАЙЛА.findall(текст) if имя not in архив]
    for группа in НОМЕРА_В_СКОБКАХ.findall(текст):
        for часть in re.split(r"\s*,\s*", группа):
            концы = [int(x) for x in re.split(r"\s*[–-]\s*", часть)]
            for n in range(концы[0], концы[-1] + 1):
                if f"{n:02d}" not in номера:
                    мимо.append(f"({n:02d})")
    return мимо


# --- проверки ----------------------------------------------------------------

def test_detector_catches_reference_to_missing_file():
    """Детектор не пропускает файл, которого нет, и не ругает тот, что есть."""
    архив = {"01-prikaz-na-dopobem.docx", "10-algoritm-doprabot.pdf"}
    assert ссылки_мимо_архива("Откройте 13-akt-priemki.docx", архив) == [
        "13-akt-priemki.docx"]
    assert ссылки_мимо_архива("Алгоритм (10) и приказ (01)", архив) == []
    assert ссылки_мимо_архива("Допсоглашения (11, 12)", архив) == [
        "(11)", "(12)"]
    assert ссылки_мимо_архива("Формы (01–03)", архив) == ["(02)", "(03)"]


def test_instruction_names_current_product_not_old_template():
    имя = имя_товара()
    for файл, текст in тексты_инструкции().items():
        плоский = плоско(текст)
        assert имя in плоский, (
            f"{файл}: нет текущего имени товара «{имя}»")
        старые = [s for s in ПРЕЖНИЕ_ИМЕНА if s in плоский]
        assert not старые, f"{файл}: прежнее имя товара {старые}"
        шаблон = [s for s in ОБЩИЙ_ШАБЛОН if s in плоский]
        assert not шаблон, f"{файл}: фразы общего шаблона {шаблон}"


def test_instruction_lists_every_file_of_archive():
    архив = выдаваемые()
    for файл, текст in тексты_инструкции().items():
        плоский = плоско(текст)
        нет = sorted(имя for имя in архив if имя not in плоский)
        assert not нет, f"{файл}: не названы файлы архива {нет}"


def test_every_mentioned_file_is_in_archive():
    архив = выдаваемые()
    тексты = dict(тексты_инструкции())
    тексты[START_HERE.name] = START_HERE.read_text(encoding="utf-8")
    for файл, текст in тексты.items():
        мимо = ссылки_мимо_архива(плоско(текст), архив)
        assert not мимо, f"{файл}: ссылки на файлы не из архива {мимо}"


def test_cases_promised_by_start_here_are_headings_of_instruction():
    раздел = раздел_start_here(2)
    assert "00-INSTRUKCIYA" in раздел, (
        "START-HERE §2 больше не отправляет к инструкции — проверка устарела")
    случаи = re.findall(r"«([^»]+)»", плоско(раздел))
    assert len(случаи) >= 2, (
        "START-HERE §2 обещает два случая, но не называет их так, чтобы их "
        f"можно было найти в инструкции: {плоско(раздел)!r}")
    заголовки = заголовки_docx(ИНСТРУКЦИЯ_DOCX)
    pdf = плоско(текст_pdf(ИНСТРУКЦИЯ_PDF))
    for случай in случаи:
        assert any(случай in h for h in заголовки), (
            f"{ИНСТРУКЦИЯ_DOCX.name}: нет заголовка случая «{случай}»; "
            f"заголовки: {заголовки}")
        assert случай in pdf, f"{ИНСТРУКЦИЯ_PDF.name}: нет случая «{случай}»"


def test_pdf_instruction_matches_docx():
    pdf = плоско(текст_pdf(ИНСТРУКЦИЯ_PDF))
    нет = [h for h in заголовки_docx(ИНСТРУКЦИЯ_DOCX) if плоско(h) not in pdf]
    assert not нет, f"{ИНСТРУКЦИЯ_PDF.name} отстал от DOCX: нет заголовков {нет}"


def test_page_names_every_format_of_archive():
    """«15 файлов в Word и Excel» при трёх PDF в архиве — неполный состав."""
    есть = {ФОРМАТЫ[Path(f).suffix] for f in выдаваемые()
            if Path(f).suffix in ФОРМАТЫ}
    текст = PAGE.read_text(encoding="utf-8")
    фразы = re.findall(r"\d+\s+(?:готовых\s+)?файл\w*[^.<\"]*?Word[^.<\"]*",
                       текст)
    assert фразы, f"{PAGE.name}: не найдено ни одной фразы о составе"
    for фраза in фразы:
        нет = sorted(ф for ф in есть if ф not in фраза)
        assert not нет, f"{PAGE.name}: «{фраза.strip()}» — не назван {нет}"


def main() -> int:
    провал = 0
    for имя, проверка in sorted(globals().items()):
        if not имя.startswith("test_"):
            continue
        try:
            проверка()
        except AssertionError as ошибка:
            провал += 1
            print(f"ПРОВАЛ  {имя}\n{ошибка}")
        else:
            print(f"ок  {имя}")
    return 1 if провал else 0


if __name__ == "__main__":
    sys.exit(main())
