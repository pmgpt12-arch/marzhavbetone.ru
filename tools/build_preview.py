#!/usr/bin/env python3
"""Предпросмотр комплекта: три фрагмента из настоящих файлов.

Замер 15.08.2026: посмотреть, что внутри, можно было на четырёх страницах
товаров из восемнадцати — там, где есть демо-страница. На остальных
покупатель видел перечень названий файлов и должен был поверить, что за
названиями что-то есть.

Фрагменты не пишутся для витрины. Они читаются из `.docx` комплекта в
`products-storage/` при каждой сборке: заголовок документа и первая
содержательная строка — та, которой документ сам себя объясняет. Отсюда
главное свойство проверки: показанное на странице совпадает с тем, что
покупатель получит, — иначе прогон краснеет. Придуманный предпросмотр
здесь невозможен по устройству, а не по договорённости.

Что не показывается: тело шаблона, формулировки требований, расчёты —
то, ради чего комплект и покупают. Берутся первые две строки файла и
обрезаются по длине.

Порядок файлов: словари полей уходят в конец. Документ «Как заполнять»
нужен покупателю после покупки, а на витрине он рассказывает про
подстановки вместо того, ради чего комплект берут.

    python3 tools/build_preview.py            # что изменится
    python3 tools/build_preview.py --write    # записать
    python3 tools/build_preview.py --check    # расхождение — код 1
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_text import paragraphs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"
CONFIG = ROOT / "products-config.php"
PRODUCTS = ROOT / "products"

FRAGMENTS = 3
# Сколько первых абзацев файла просматривать. Дальше начинается тело
# шаблона — то, ради чего комплект и покупают.
LOOK_AHEAD = 8
MAX_CHARS = 190

# Служебные строки, одинаковые во всех файлах комплекта. Показывать их как
# «вот что внутри» — то же самое, что показывать пустое место.
BOILERPLATE = (
    "заполните поля в квадратных скобках",
    "важно, прочитайте до использования",
    "[на бланке организации]",
    "исх. №",
)
# Файлы, которые не ведут витрину: письмо после покупки — служебное,
# инструкция по внедрению рассказывает про папку, а не про работу.
SKIP_FILES = ("PISMO-POSLE-POKUPKI", "INSTRUKCIYA")
# Словарь подстановок нужен после покупки, а не до неё.
LAST = ("как заполнять", "словарь полей")

BEGIN = '      <div class="kit-preview">'
BLOCK = re.compile(r'\n      <div class="kit-preview">.*?\n      </div>\n', re.S)
ANCHOR = re.compile(r'(<h2>Что входит[^<]*</h2>\n.*?\n      </div>\n)', re.S)


def catalog() -> dict[str, str]:
    """SKU → каталог комплекта в products-storage."""
    text = CONFIG.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(
        r"'([a-z0-9]+)'\s*=>\s*\[\s*'name'.*?'dir'\s*=>\s*'([^']+)'", text, re.S)}


def informative(lines: list[str], title: str) -> str:
    """Первая строка, которая что-то сообщает.

    Отсеиваются три вида пустышек, и все три нашлись живым прогоном, а не
    придумались: служебные строки бланка, поля формы в квадратных скобках
    («[Наименование заказчика]») и продолжение самого заголовка — у актов
    первая строка тела повторяет шапку по частям.
    """
    head = title.lower()
    for line in lines[:LOOK_AHEAD]:
        low = line.lower()
        if any(low.startswith(b) for b in BOILERPLATE):
            continue
        # Поле бланка, а не текст: подстановка в скобках, линейка под
        # подпись, исходящий номер, дата. Такая строка на витрине говорит
        # ровно то же, что пустое место, и выглядит как недоделка.
        if re.search(r"[\[\]_]{1,}|\{\{|№|\d{2}___|20___", line):
            continue
        # Доля о мире без выборки на страницу не выносится. Строка
        # «Типовые замечания (встречаются в 80% случаев)» — настоящая, она
        # действительно есть в файле комплекта, и это ничего не меняет:
        # внутри документа она обобщение опыта, на витрине становится
        # утверждением сайта. Прогон `check_evidence.py` поймал её на p4 в
        # первой же сборке — здесь она отсекается на входе.
        if "%" in line:
            continue
        if low in head or head.endswith(low) or low in head.replace(":", ""):
            continue
        if len(line) < 40 or len(line.split()) < 5:
            continue
        return line
    return ""


def clip(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    cut = text[:MAX_CHARS].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return cut + "…"


def fragments(folder: Path) -> list[dict]:
    files = [p for p in sorted(folder.glob("*.docx"))
             if not any(s in p.name for s in SKIP_FILES)]

    def order(path: Path) -> tuple[int, str]:
        try:
            head = (paragraphs(path) or [""])[0].lower()
        except Exception:
            return (2, path.name)
        return (1 if any(head.startswith(x) for x in LAST) else 0, path.name)

    out = []
    for path in sorted(files, key=order):
        lines = paragraphs(path)
        if not lines:
            continue
        title = lines[0]
        body = informative(lines[1:], title)
        if not body:
            continue
        out.append({"file": path.name, "title": clip(title), "body": clip(body)})
        if len(out) == FRAGMENTS:
            break
    return out


def block(items: list[dict], count: int) -> str:
    rows = "".join(
        '\n        <article class="preview-item">'
        f'\n          <p class="preview-file">{html.escape(i["file"])}</p>'
        f'\n          <h3>{html.escape(i["title"])}</h3>'
        f'\n          <p>{html.escape(i["body"])}</p>'
        '\n        </article>' for i in items)
    tail = (f"Здесь {len(items)} документа из {count}" if count > len(items)
            else f"Здесь все {count} документа комплекта")
    return (
        '\n      <div class="kit-preview">'
        '\n        <h3 class="preview-head">Как это выглядит внутри</h3>'
        '\n        <p class="preview-note">Первые строки самих файлов комплекта — '
        'заголовок документа и строка, которой он себя объясняет. Не описание '
        f'для витрины: текст читается из файлов при сборке страницы. {tail}; '
        'тело шаблонов, формулировки требований и расчёты открываются после '
        'покупки.</p>'
        f'{rows}'
        '\n      </div>\n')


def render(path: Path, dirs: dict[str, str]) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    found = re.search(r'data-sku="([^"]+)"', text)
    if not found:
        return text, "нет data-sku"
    sku = found.group(1)
    folder = STORAGE / dirs.get(sku, "")
    if not dirs.get(sku) or not folder.is_dir():
        return text, f"{sku}: каталога комплекта нет в products-storage"

    items = fragments(folder)
    if len(items) < 2:
        return text, (f"{sku}: пригодных фрагментов {len(items)} — "
                      f"нужно хотя бы два")
    count = len([p for p in folder.glob("*.docx")
                 if not any(s in p.name for s in SKIP_FILES)])

    new = BLOCK.sub("", text)
    if not ANCHOR.search(new):
        return text, f"{sku}: не найден раздел «Что входит»"
    new = ANCHOR.sub(lambda m: m.group(1) + block(items, count), new, count=1)
    if new == text:
        return text, ""
    return new, ("предпросмотр обновлён" if BEGIN in text else "предпросмотр поставлен")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    dirs = catalog()
    pages = sorted(PRODUCTS.glob("*.html"))
    changed, problems = [], []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        new, what = render(path, dirs)
        if what and new == text:
            problems.append(f"{path.name}: {what}")
            continue
        if new != text:
            changed.append((path.name, what))
            if args.write:
                path.write_text(new, encoding="utf-8")

    with_preview = sum(1 for p in pages
                       if BEGIN in p.read_text(encoding="utf-8")) if args.write else \
        sum(1 for p in pages if BEGIN in p.read_text(encoding="utf-8"))
    print(f"Страниц товаров: {len(pages)}; с предпросмотром: {with_preview}")
    for name, what in changed:
        print(f"   {'записано' if args.write else 'изменится'}: {name} — {what}")
    for line in problems:
        print(f"   ДЕФЕКТ {line}")

    if problems:
        return 1
    if args.check and changed:
        print("Предпросмотр разошёлся с файлами комплектов: "
              "python3 tools/build_preview.py --write")
        return 1
    if not changed:
        print("   расхождений нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
