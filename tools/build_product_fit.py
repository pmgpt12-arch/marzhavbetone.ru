#!/usr/bin/env python3
"""Блок «Кому подойдёт / Когда применять» на страницах товаров.

Замер 15.08.2026: дословный блок «Кому подойдёт» стоял на одной странице
из восемнадцати, и текст в нём был общий — «Субподрядчики», «ПТО и
прорабы», «Руководители компаний». «Когда применять» не было нигде.
Покупатель, попавший на страницу товара, до состава комплекта должен
узнать свою ситуацию; общий текст сообщает об этом ровно столько же,
сколько его отсутствие.

Блок ставится в первый экран — сразу под ценой и кнопкой, внутри той же
секции, что заголовок и лид. Ниже он не работает: до него доходят те, кто
уже решил.

Источник текста — `data/sales/product-fit.yaml`, по одной записи на SKU.
Руками в HTML блок не правится: восемнадцать независимых кусков разметки
разойдутся с каталогом на первой же правке линейки, и разойдутся молча.

    python3 tools/build_product_fit.py            # что изменится
    python3 tools/build_product_fit.py --write    # записать
    python3 tools/build_product_fit.py --check    # расхождение — код 1
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "sales" / "product-fit.yaml"
PRODUCTS = ROOT / "products"

# Куда встаёт блок: сразу за героем — фото, цена, кнопка, — в той же
# секции, что заголовок и лид. Якорь ловит закрытие самого героя, а не
# закрытие секции: между ними может стоять уже поставленный блок, и тогда
# «до конца секции» уводит вставку в следующую секцию. Так и случилось на
# первом же повторном прогоне — блок уехал в «Что входит».
#
# Ранее поставленный блок захватывается тем же выражением и заменяется
# целиком: прогон обязан быть повторяемым, иначе он не проверка, а правка.
ANCHOR = re.compile(
    r'(<div class="product-hero">.*?\n      </div>\n)'
    r'(?:\n      <div class="product-fit">.*?\n      </div>\n)?', re.S)
EXISTING = re.compile(r'\n      <div class="product-fit">\n', re.S)
# Прежняя общая врезка «Кому подойдёт этот комплект» с отраслями вместо
# признаков. Она снимается вместе с постановкой нового блока: два блока с
# одним заголовком на странице — хуже, чем ни одного.
GENERIC = re.compile(
    r'\n    <section class="section">\n'
    r'      <h2>Кому подойд[её]т[^<]*</h2>\n'
    r'      <div class="audience-grid">.*?</div>\n'
    r'    </section>\n', re.S)


def esc(text: str) -> str:
    return html.escape(" ".join(str(text).split()), quote=False)


def block(entry: dict) -> str:
    signs = "".join(f"\n            <li>{esc(s)}</li>" for s in entry["fit"])
    return (
        '\n      <div class="product-fit">'
        '\n        <div class="fit-col">'
        '\n          <h2>Когда применять</h2>'
        f'\n          <p>{esc(entry["when"])}</p>'
        f'\n          <p class="fit-result"><strong>На выходе.</strong> {esc(entry["result"])}</p>'
        '\n        </div>'
        '\n        <div class="fit-col">'
        '\n          <h2>Кому подойдёт</h2>'
        f'\n          <ul class="fit-signs">{signs}'
        '\n          </ul>'
        '\n        </div>'
        '\n      </div>\n')


def sku_of(text: str) -> str | None:
    found = re.search(r'data-sku="([^"]+)"', text)
    return found.group(1) if found else None


def render(path: Path, entries: dict) -> tuple[str, str]:
    """Возвращает (новый текст, что сделано)."""
    text = path.read_text(encoding="utf-8")
    sku = sku_of(text)
    if sku is None:
        return text, "нет data-sku — пропущена"
    entry = entries.get(sku)
    if entry is None:
        return text, f"{sku} не описан в {SOURCE.name}"

    dropped = GENERIC.search(text) is not None
    new = GENERIC.sub("", text)
    if not ANCHOR.search(new):
        return text, "не найден якорь product-hero — пропущена"
    new = ANCHOR.sub(lambda m: m.group(1) + block(entry), new, count=1)

    if new == text:
        return text, ""
    what = "блок поставлен"
    if EXISTING.search(text):
        what = "блок обновлён"
    if dropped:
        what += ", общая врезка снята"
    return new, what


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    entries = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["products"]
    pages = sorted(PRODUCTS.glob("*.html"))

    changed, problems = [], []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        new, what = render(path, entries)
        if what.endswith("пропущена") or "не описан" in what:
            problems.append(f"{path.name}: {what}")
            continue
        if new != text:
            changed.append((path, new, what))
            if args.write:
                path.write_text(new, encoding="utf-8")

    described = set(entries)
    on_pages = {sku_of(p.read_text(encoding="utf-8")) for p in pages}
    for extra in sorted(described - on_pages):
        problems.append(f"{extra} описан в {SOURCE.name}, но страницы товара нет")

    print(f"Страниц товаров: {len(pages)}, описано в {SOURCE.name}: {len(entries)}")
    for path, _new, what in changed:
        print(f"   {'записано' if args.write else 'изменится'}: {path.name} — {what}")
    for line in problems:
        print(f"   ДЕФЕКТ {line}")
    if not changed and not problems:
        print("   расхождений нет")

    if problems:
        return 1
    if args.check and changed:
        print("Разметка разошлась с источником: "
              "python3 tools/build_product_fit.py --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
