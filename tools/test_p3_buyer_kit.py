#!/usr/bin/env python3
"""P3 «КС-2 без возврата»: в купленном комплекте формы, а не их описания.

Дефект, ради которого написан тест (аудит MB001, PR #289 — P3-03…P3-07;
issue #304). Файл `03-akt-skrytyh-rabot.docx` назывался «5 типовых форм
АОСР», а вместо каждой формы стояла строка `[Шаблон акта с полями: …]` и
утверждение «все обязательные реквизиты по СП 48.13330.2019». Рядом лежала
продающая таблица «Бесплатный материал vs Полный комплект» с «50+ пунктов»,
«15+ ошибок», снижением возвратов «с 30-40% до 5-10%» и «окупаемостью»,
а типовые ошибки отсылали к снятому с продажи «полному комплекту».
`check_packages` видел, что файлы на месте, `build_preview` — что первые
строки совпадают со страницей. Что внутри формы, не смотрел никто.

Проверяется то, что уходит покупателю: папка выдачи P3 без служебных файлов
(`mvb_build_product_zip` исключает MANIFEST.md, .htaccess и письмо после
покупки). Разбор .docx — zip и XML стандартной библиотеки, без python-docx:
тест должен идти там же, где идут остальные проверки.

Запуск: python3 -m pytest tools/test_p3_buyer_kit.py
"""
from __future__ import annotations

import filecmp
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"
KIT = STORAGE / "05-ks-bez-vozvrata"
SERVICE = {"MANIFEST.md", ".htaccess", "00-PISMO-POSLE-POKUPKI.txt"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def delivered() -> list[Path]:
    return sorted(p for p in KIT.iterdir() if p.is_file() and p.name not in SERVICE)


def body(path: Path) -> list[ET.Element]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return list(root.find(f"{W}body"))


def text_of(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.iter(f"{W}t"))


def cells(table: ET.Element) -> list[list[str]]:
    return [[text_of(tc).strip() for tc in tr.findall(f"{W}tc")]
            for tr in table.findall(f"{W}tr")]


def buyer_text(path: Path) -> str:
    if path.suffix == ".docx":
        return "\n".join(text_of(node) for node in body(path))
    if path.suffix == ".xlsx":
        with zipfile.ZipFile(path) as archive:
            return "\n".join(archive.read(n).decode("utf-8", "replace")
                             for n in archive.namelist() if n.startswith("xl/"))
    if path.suffix == ".txt":
        return path.read_text(encoding="utf-8")
    return ""          # PDF: текст сжат; алгоритм 08 этим заходом не менялся


def forms() -> list[list[ET.Element]]:
    """Тело файла 03, нарезанное по заголовкам «Форма N. …»."""
    found, current = [], None
    for node in body(KIT / "03-akt-skrytyh-rabot.docx"):
        line = text_of(node).strip()
        if node.tag == f"{W}p" and re.match(r"Форма \d\. Акт освидетельствования", line):
            current = []
            found.append(current)
            continue
        if node.tag == f"{W}p" and line == "Как пользоваться формами":
            current = None
        if current is not None:
            current.append(node)
    return found


# Строки, которые покупатель P3 читать не должен. Каждая взята из файла,
# который лежал в выдаче до 28.09.2026.
STUBS = [r"\[Шаблон", r"\[Универсальный шаблон"]
FALSE_PROMISES = [
    r"50\+", r"15\+", r"[Оо]купаем", r"30-40\s*%", r"5-10\s*%",
    r"снижает количество возвратов", r"[Пп]олн(ый|ом|ого|ому) комплект",
    r"Бесплатный материал vs", r"все обязательные реквизиты",
]


@pytest.mark.parametrize("path", delivered(), ids=lambda p: p.name)
def test_no_stubs_or_false_promises(path):
    text = buyer_text(path)
    hits = [pat for pat in STUBS + FALSE_PROMISES if re.search(pat, text)]
    assert not hits, f"{path.name}: {hits}"


def test_five_forms_not_descriptions():
    found = forms()
    assert len(found) == 5, f"форм найдено: {len(found)}"
    for number, nodes in enumerate(found, 1):
        tables = [cells(n) for n in nodes if n.tag == f"{W}tbl"]
        prose = "\n".join(text_of(n) for n in nodes)
        assert len(tables) >= 7, f"форма {number}: таблиц {len(tables)}"
        blanks = sum(1 for t in tables for row in t for c in row if not c)
        assert blanks >= 40, f"форма {number}: пустых полей {blanks}"

        signatures = [t for t in tables if t[0][:3] == ["Участник", "Должность, Ф. И. О.", "Подпись"]]
        assert signatures and len(signatures[0]) >= 5, f"форма {number}: нет таблицы подписей"
        attachments = [t for t in tables if t[0] and t[0][-1] == "Листов"]
        assert attachments and len(attachments[0]) >= 4, f"форма {number}: нет перечня приложений"
        materials = [t for t in tables if t[0] and t[0][1:2] == ["Партия"]]
        assert materials, f"форма {number}: нет таблицы материалов"

        for required in ("АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ",
                         "Разрешается производство последующих работ",
                         "Работы к закрытию не допускаются",
                         "Акт составлен в"):
            assert required in prose, f"форма {number}: нет «{required}»"


def test_forms_do_not_claim_normative_compliance():
    text = buyer_text(KIT / "03-akt-skrytyh-rabot.docx")
    assert "СП 48.13330" not in text
    assert "не воспроизводят и соответствие ему не утверждают" in text


def test_comparison_table_is_not_a_sales_page():
    text = buyer_text(KIT / "10-sravnitelnaya-tablica.docx")
    assert "₽" not in text and "Стоимость" not in text
    assert "Приёмку таблица не гарантирует" in text


def test_start_here_lists_what_is_delivered():
    start = (KIT / "00-START-HERE.txt").read_text(encoding="utf-8")
    archive = start[start.index("4. ЧТО В АРХИВЕ"):start.index("5. ЗАДАЧА")]
    listed = re.findall(r"^   (\d\d-[^\s]+)", archive, re.M)
    assert listed == [p.name for p in delivered()]
    assert f"файлов в архиве: {len(delivered())}" in start
    assert "формы актов освидетельствования скрытых работ (03)" in start.replace("\n   ", " ").lower()


def test_build_all_has_no_second_p3_source():
    source = (STORAGE / "build_all.py").read_text(encoding="utf-8")
    block = source[source.index("def build_paid_05"):source.index("def build_paid_06")]
    assert "build_paid_05.py" in block
    assert "create_word_doc" not in block and "ТИПОВЫХ ФОРМ" not in block


def test_generator_reproduces_delivered_files(tmp_path):
    for module in ("docx", "openpyxl", "reportlab"):
        pytest.importorskip(module)
    shutil.copy(STORAGE / "build_paid_05.py", tmp_path)
    (tmp_path / KIT.name).mkdir()
    subprocess.run([sys.executable, "build_paid_05.py"], cwd=tmp_path, check=True,
                   capture_output=True)
    built = sorted(p.name for p in (tmp_path / KIT.name).iterdir())
    assert built, "генератор ничего не собрал"
    differ = [n for n in built if not filecmp.cmp(tmp_path / KIT.name / n, KIT / n, shallow=False)]
    assert not differ, f"собранное генератором расходится с выдачей: {differ}"
