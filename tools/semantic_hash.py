#!/usr/bin/env python3
"""Смысловой хеш юридического документа: меняется от содержания, не от сборки.

Зачем не sha256 файла. Пересборка DOCX и XLSX меняет байты всегда: в
контейнере Office лежат отметки времени, порядок записей и служебные
свойства. Замер 15.08.2026 в задаче D-06: файл
`13-uvedomlenie-o-prosrochke-oplaty.docx` был пересобран без единой правки
текста, и побайтово отличался от лежавшего в main. Хеш по файлу краснел бы
на каждой сборке, а привязка нормативного результата к версии документа
требует обратного: хеш обязан молчать на пересборке и меняться на правке
смысла.

Отсюда хеш считается по типу файла, а не по контейнеру.

**DOCX** — весь текст `word/document.xml` в порядке документа. Узлы `w:t`
покрывают и абзацы, и ячейки таблиц: в OOXML таблица состоит из тех же
текстовых узлов. Стили, шрифты, ширины колонок, `docProps` и отметки
времени в хеш не входят — юридического содержания в них нет.

**XLSX** — по каждому листу: имя листа, координата ячейки и то, что в ней
объявлено. Для ячейки с формулой берётся сама формула, а не её кэшированное
значение: значение зависит от того, пересчитывал ли редактор книгу, а
формула — это и есть заявленный порядок расчёта. Для ячейки без формулы
берётся значение, потому что подписи, инструкции и оговорки листа живут
именно там. Так изменение формулы расчёта процентов меняет хеш, а открытие
и сохранение книги — нет.

Только стандартная библиотека: проверка живёт в гейте
`.github/workflows/checks.yml`, а он объявлен набором без сети и без
установки пакетов сверх `pillow` и `pyyaml`.

    python3 tools/semantic_hash.py <файл> [<файл> ...]
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


class UnsupportedType(ValueError):
    """Тип файла, для которого смыслового хеша не объявлено."""


def _norm(text: str) -> str:
    """Пробелы схлопываются: перенос строки в разметке смысла не меняет."""
    return re.sub(r"\s+", " ", text).strip()


def docx_parts(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    # itertext() не годится: он склеит текст соседних узлов без границы, и
    # два разных документа могли бы дать одну строку. Границей служит сам
    # перечень узлов.
    return [_norm(node.text or "") for node in root.iter(f"{W}t")]


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.iter(f"{S}si"):
        out.append(_norm("".join(t.text or "" for t in si.iter(f"{S}t"))))
    return out


def _sheet_targets(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    """(имя листа, путь к xml) в порядке книги.

    Порядок берётся из `workbook.xml`, а путь — из его связей: имя файла
    `sheet1.xml` порядку не соответствует и совпадает с ним не всегда.
    """
    book = ElementTree.fromstring(z.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    by_id = {r.get("Id"): r.get("Target") for r in rels}
    out = []
    for sheet in book.iter(f"{S}sheet"):
        target = by_id.get(sheet.get(f"{R}id"), "")
        target = target[1:] if target.startswith("/") else "xl/" + target.lstrip("/")
        out.append((sheet.get("name") or "", target.replace("xl/xl/", "xl/")))
    return out


def xlsx_parts(path: Path) -> list[str]:
    parts: list[str] = []
    with zipfile.ZipFile(path) as z:
        shared = _shared_strings(z)
        names = set(z.namelist())
        for name, target in _sheet_targets(z):
            if target not in names:
                continue
            parts.append(f"[лист] {name}")
            root = ElementTree.fromstring(z.read(target))
            for cell in root.iter(f"{S}c"):
                ref = cell.get("r") or ""
                formula = cell.find(f"{S}f")
                if formula is not None:
                    parts.append(f"{ref}={_norm(formula.text or '')}")
                    continue
                if cell.get("t") == "inlineStr":
                    inline = "".join(t.text or "" for t in cell.iter(f"{S}t"))
                    parts.append(f"{ref}:{_norm(inline)}")
                    continue
                value = cell.find(f"{S}v")
                if value is None:
                    continue
                raw = value.text or ""
                if cell.get("t") == "s":
                    idx = int(raw) if raw.isdigit() else -1
                    raw = shared[idx] if 0 <= idx < len(shared) else ""
                parts.append(f"{ref}:{_norm(raw)}")
    return parts


def semantic_hash(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        parts = docx_parts(path)
    elif suffix == ".xlsx":
        parts = xlsx_parts(path)
    else:
        raise UnsupportedType(
            f"{path.name}: смысловой хеш объявлен для .docx и .xlsx. "
            "Молча хешировать байтами нельзя — это дало бы красный гейт на "
            "каждой пересборке и приучило бы его обходить.")
    body = "\n".join(parts).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2
    code = 0
    for arg in argv:
        try:
            print(f"{semantic_hash(arg)}  {arg}")
        except (UnsupportedType, OSError, zipfile.BadZipFile, KeyError) as e:
            print(f"НЕ ПОСЧИТАН  {arg}: {e}")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
