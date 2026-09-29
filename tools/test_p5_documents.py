#!/usr/bin/env python3
"""Тексты 07, 08 и 10 в выдаче P5 — те, что прошли перечит Р-026.

MB001-R2-P5, документы. В покупательской выдаче P5 стояли три
формулировки, которые перечит Р-026 от 29.09.2026 не принял
(`tools/candidates/MB001_R026_P5_RECHECK.md`):

- `07-algoritm-proverki-uderzhaniy.pdf`, шаг 6: «Исковая давность: 3 года» —
  срок назван, а день начала его течения и особые сроки (ст. 200, 207,
  725 ГК РФ) нет;
- `08-tipovye-osnovaniya.docx`, «Общий принцип оспаривания»: условие
  «Соразмерно фактическому ущербу» для любого удержания и безусловный вывод
  «удержание неправомерно»;
- `10-konsultaciya-po-delu.docx`: «сэкономит время и повысит качество
  консультации» — обещание результата без замера.

Проверяется то, что скачивает покупатель: архив собирает
`mvb_build_product_zip('p5')` из `products-config.php` — та же функция, что
отдаёт файлы после оплаты, — затем текст PDF и DOCX читается из архива.
Нет PHP, ZipArchive или средства чтения PDF — это провал, а не пропуск:
без них проверять нечего, и зелёный результат ничего бы не значил.

Файл `tools/test_p5_claims.py` (START-HERE и страница) живёт в Draft PR #309;
эта ветка стоит на #298, где его нет, поэтому проверка документов — отдельным
файлом, чтобы два PR не спорили за один путь.

    python3 tools/test_p5_documents.py
    python3 -m pytest tools/test_p5_documents.py -q
    P5_PRODUCTS_DIR=/другое/дерево/products-storage python3 tools/test_p5_documents.py
"""
from __future__ import annotations

import functools
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

КОРЕНЬ = Path(__file__).resolve().parent.parent
МАСТЕРА = Path(os.environ.get("P5_PRODUCTS_DIR", КОРЕНЬ / "products-storage"))

PDF_07 = "07-algoritm-proverki-uderzhaniy.pdf"
DOCX_08 = "08-tipovye-osnovaniya.docx"
DOCX_10 = "10-konsultaciya-po-delu.docx"
ПРОВЕРЯЕМЫЕ = (PDF_07, DOCX_08, DOCX_10)

# Формулировки, которых быть не должно, — по файлам, как их разбирал
# перечит. Причина — рядом: вернуть фразу можно только с новым Р-026.
# «удержание неправомерно» ищется только в 08: в шаге 5 файла 07 стоит
# условное «Если удержание неправомерно — требуйте возврата», перечит его не
# разбирал, и эта проверка его не трогает.
ЗАПРЕЩЕНО = {
    PDF_07: {
        "Исковая давность: 3 года":
            "срок без дня начала течения и особых сроков (ст. 200, 207, 725 ГК РФ), G-1",
    },
    DOCX_10: {
        "сэкономит время": "обещание результата без замера, G-2",
        "повысит качество": "обещание результата без замера, G-2",
    },
    DOCX_08: {
        "удержание неправомерно": "безусловный правовой вывод, G-3",
        "Соразмерно фактическому ущербу":
            "смешивает убытки и неустойку: для неустойки убытки не доказываются "
            "(п. 1 ст. 330 ГК РФ), G-3",
    },
}

# Тексты, принятые Р-026. Сверяются дословно, с точностью до пробелов и
# переносов строки: сокращать и перефразировать их без нового перечита нельзя.
ТРЕБУЕТСЯ = {
    PDF_07: [
        "Исковая давность: проверьте срок и день начала его течения по ст. 196 и 200 ГК РФ; "
        "для пеней и процентов — также ст. 207 ГК РФ, для требований заказчика о качестве "
        "работ — ст. 725 ГК РФ",
    ],
    DOCX_10: [
        "Заполните эту форму до встречи с юристом: сведения о договоре и споре, суммы, "
        "хронология и перечень документов будут собраны в одном месте.",
    ],
    DOCX_08: [
        "Общий принцип оспаривания",
        "Проверьте каждое удержание по шести вопросам:\n"
        "1. Предусмотрено ли оно договором или законом.\n"
        "2. Подтверждено ли оно документами: актом, расчётом, перепиской.\n"
        "3. Если удерживают убытки (например, расходы на другого подрядчика) — подтверждены ли "
        "расчётом их размер и связь с вашим нарушением (ст. 15, 393 ГК РФ).\n"
        "4. Если удерживают неустойку (штраф, пени) — предусмотрена ли она договором и начислена "
        "ли за нарушение, за которое вы отвечаете (п. 2 ст. 330 ГК РФ). Доказывать убытки для "
        "неустойки заказчик не обязан (п. 1 ст. 330 ГК РФ). Уменьшить неустойку вправе суд, если "
        "она явно несоразмерна последствиям нарушения; если нарушитель — предприниматель, только "
        "по его заявлению, а договорную неустойку — лишь в исключительных случаях, когда доказано, "
        "что взыскание в договорном размере может привести к необоснованной выгоде заказчика "
        "(ст. 333 ГК РФ).\n"
        "5. Если удержание заявлено как зачёт — однородно ли встречное требование заказчика, "
        "наступил ли срок его исполнения и не запрещён ли зачёт законом или договором "
        "(ст. 410, 411 ГК РФ). По требованию с истёкшей исковой давностью зачёт не допускается "
        "(ст. 411, п. 3 ст. 199 ГК РФ); на какую дату проверять давность, уточните у юриста.\n"
        "6. Требует ли договор согласовать удержание с вами и было ли оно согласовано.\n"
        "Если хотя бы по одному вопросу ответ не в пользу заказчика — это довод против удержания. "
        "Исход спора зависит от договора и документов по объекту.",
    ],
}

# Минимальный набор констант, без которого products-config.php не
# загружается; каталоги заказов и выдачи — временные, мастера — настоящие.
_PHP = r"""<?php
declare(strict_types=1);
[$_, $root, $tmp, $masters] = $argv;
foreach ([
    'ORDERS_DIR' => $tmp,
    'DELIVERY_DIR' => $tmp . '/delivery',
    'PRODUCTS_DIR' => $masters,
    'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'a@example.invalid',
    'YOOKASSA_SHOP_ID' => 't',
    'YOOKASSA_SECRET_KEY' => 't',
    'YOOKASSA_API_URL' => 'https://example.invalid',
    'YOOKASSA_MODE' => 'test',
] as $name => $value) {
    define($name, $value);
}
require $root . '/products-config.php';
if (!class_exists('ZipArchive')) {
    fwrite(STDERR, "нет расширения ZipArchive\n");
    exit(3);
}
$path = mvb_build_product_zip('p5');
if ($path === null) {
    fwrite(STDERR, "mvb_build_product_zip('p5') вернула null\n");
    exit(4);
}
echo $path;
"""


@functools.lru_cache(maxsize=None)
def архив_выдачи() -> dict[str, bytes]:
    """Архив P5 так, как его получает покупатель: имя файла → содержимое."""
    php = shutil.which("php")
    assert php, "PHP не найден: выдачу P5 собирает PHP, без него проверять нечего"
    with tempfile.TemporaryDirectory(prefix="mvb-p5-") as tmp:
        скрипт = Path(tmp) / "build.php"
        скрипт.write_text(_PHP, encoding="utf-8")
        заказы = Path(tmp) / "orders"
        (заказы / "delivery").mkdir(parents=True)
        r = subprocess.run([php, str(скрипт), str(КОРЕНЬ), str(заказы), str(МАСТЕРА)],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"PHP-сборка P5: код {r.returncode}\n{r.stderr}{r.stdout}"
        путь = Path(r.stdout.strip())
        assert путь.is_file(), f"PHP вернул путь без файла: {путь}"
        with zipfile.ZipFile(путь) as z:
            return {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}


def текст_pdf(данные: bytes) -> str:
    try:
        import pymupdf
    except ImportError:
        pymupdf = None
    if pymupdf is not None:
        with pymupdf.open(stream=данные, filetype="pdf") as doc:
            return "\n".join(стр.get_text() for стр in doc)
    pdftotext = shutil.which("pdftotext")
    assert pdftotext, "нечем прочитать PDF: нужен pymupdf или pdftotext (poppler-utils)"
    r = subprocess.run([pdftotext, "-layout", "-", "-"], input=данные,
                       capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode(errors="replace")
    return r.stdout.decode("utf-8")


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def текст_docx(данные: bytes) -> str:
    """Текст абзацев и ячеек таблиц; <w:br/> — перенос строки.

    Только стандартная библиотека: python-docx нужен генератору, но
    проверке выдачи — нет.
    """
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(io.BytesIO(данные)) as z:
        корень = ET.fromstring(z.read("word/document.xml"))
    абзацы = []
    for п in корень.iter(_W + "p"):
        части = []
        for эл in п.iter():
            if эл.tag == _W + "t":
                части.append(эл.text or "")
            elif эл.tag in (_W + "br", _W + "cr"):
                части.append("\n")
            elif эл.tag == _W + "tab":
                части.append("\t")
        абзацы.append("".join(части))
    return "\n".join(абзацы)


def текст_файла(имя: str) -> str:
    архив = архив_выдачи()
    assert имя in архив, f"в выдаче P5 нет {имя}; состав: {sorted(архив)}"
    данные = архив[имя]
    return текст_pdf(данные) if имя.endswith(".pdf") else текст_docx(данные)


def норм(текст: str) -> str:
    """Пробелы, переносы и отступы продолжения строки PDF — один пробел."""
    return re.sub(r"\s+", " ", текст).strip()


def запрещённое(текст: str, имя: str) -> list[str]:
    t = норм(текст).casefold()
    return [f"«{фраза}» — {почему}" for фраза, почему in ЗАПРЕЩЕНО[имя].items()
            if норм(фраза).casefold() in t]


def недостающее(текст: str, нужное: list[str]) -> list[str]:
    t = норм(текст)
    return [f"нет принятого текста: «{норм(н)[:70]}…»" for н in нужное if норм(н) not in t]


# ─────────────────────────────── проверки ───────────────────────────────

def test_выдача_p5_содержит_проверяемые_файлы() -> None:
    нет = [имя for имя in ПРОВЕРЯЕМЫЕ if имя not in архив_выдачи()]
    assert not нет, f"в выдаче P5 нет {нет}: проверка текста была бы пустой"


def test_07_pdf_шаг_6() -> None:
    текст = текст_файла(PDF_07)
    проблемы = запрещённое(текст, PDF_07) + недостающее(текст, ТРЕБУЕТСЯ[PDF_07])
    assert not проблемы, f"{PDF_07}:\n  " + "\n  ".join(проблемы)


def test_08_общий_принцип() -> None:
    текст = текст_файла(DOCX_08)
    проблемы = запрещённое(текст, DOCX_08) + недостающее(текст, ТРЕБУЕТСЯ[DOCX_08])
    assert not проблемы, f"{DOCX_08}:\n  " + "\n  ".join(проблемы)


def test_10_без_обещания_результата() -> None:
    текст = текст_файла(DOCX_10)
    проблемы = запрещённое(текст, DOCX_10) + недостающее(текст, ТРЕБУЕТСЯ[DOCX_10])
    assert not проблемы, f"{DOCX_10}:\n  " + "\n  ".join(проблемы)


def test_детекторы_различают_случаи() -> None:
    """Сторож самой проверки: иначе зелёный результат ничего не значит."""
    assert запрещённое("   - Исковая давность:\n     3 года", PDF_07)
    assert len(запрещённое("Это сэкономит время и повысит качество консультации.", DOCX_10)) == 2
    assert запрещённое("Если хотя бы одно условие не соблюдено - удержание неправомерно.", DOCX_08)
    assert запрещённое("3. Соразмерно фактическому ущербу.", DOCX_08)
    assert not запрещённое("о взыскании неправомерно удержанных сумм", DOCX_08)
    for имя, нужное in ТРЕБУЕТСЯ.items():
        assert not запрещённое("\n".join(нужное), имя)
        assert not недостающее("\n".join(нужное), нужное)
        # Перефразированный текст — провал, а не совпадение по смыслу.
        assert недостающее("\n".join(нужное).replace("ГК РФ", "ГК"), нужное) or \
            "ГК РФ" not in "".join(нужное)
    assert недостающее("", ТРЕБУЕТСЯ[DOCX_10])


if __name__ == "__main__":
    провалы = 0
    тесты = [(имя, f) for имя, f in list(globals().items())
             if имя.startswith("test_") and callable(f)]
    for имя, f in тесты:
        try:
            f()
            print(f"ок      {имя}")
        except AssertionError as e:
            провалы += 1
            print(f"ПРОВАЛ  {имя}\n  {e}")
    print(f"\n{len(тесты) - провалы}/{len(тесты)} прошли")
    sys.exit(1 if провалы else 0)
