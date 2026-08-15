#!/usr/bin/env python3
"""Возражения покупателя — рядом с ценой, а не на четвёртом экране.

Замер 15.08.2026: ответы на возражения на страницах товаров были, но
лежали в разделе «Вопросы до покупки» ниже состава и ниже «чего здесь
нет». Человек, засомневавшийся у цены, туда не доходит: он закрывает
вкладку там же, где засомневался.

Блок ставится сразу за «когда применять / кому подойдёт», то есть в
первых экранах. Строк четыре: три общих факта продажи и одно возражение
именно про этот комплект. Развёрнутые ответы остаются внизу — это не
второй FAQ, а то, что снимает сомнение на месте.

Источник — `data/sales/objections.yaml`. Руками в HTML не правится.

    python3 tools/build_objections.py            # что изменится
    python3 tools/build_objections.py --write    # записать
    python3 tools/build_objections.py --check    # расхождение — код 1
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "sales" / "objections.yaml"
PRODUCTS = ROOT / "products"

# Блок идёт следом за «когда применять / кому подойдёт»: сначала человек
# узнаёт свою ситуацию, потом снимает сомнение. Обратный порядок отвечал
# бы на возражение того, кто ещё не понял, о чём товар.
ANCHOR = re.compile(
    r'(\n      <div class="product-fit">.*?\n      </div>\n)'
    r'(?:\n      <div class="objections">.*?\n      </div>\n)?', re.S)
EXISTING = '\n      <div class="objections">\n'
# Внутри ответов допускается ровно одна ссылка — на страницу возврата.
# Остальное экранируется: текст приходит из данных, и открывать данным
# дорогу в разметку нельзя.
LINK = re.compile(r'&lt;a href="(/[a-z0-9./-]+)"&gt;(.*?)&lt;/a&gt;')


def esc(text: str) -> str:
    out = html.escape(" ".join(str(text).split()), quote=False)
    return LINK.sub(r'<a href="\1">\2</a>', out)


def block(common: list[dict], own: dict) -> str:
    items = list(common) + ([own] if own else [])
    rows = "".join(
        '\n        <details>'
        f'\n          <summary>{esc(i["q"])}</summary>'
        f'\n          <p>{esc(i["a"])}</p>'
        '\n        </details>' for i in items)
    return (
        '\n      <div class="objections">'
        '\n        <h2>Что обычно останавливает</h2>'
        f'{rows}'
        '\n      </div>\n')


def render(path: Path, data: dict) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    found = re.search(r'data-sku="([^"]+)"', text)
    if not found:
        return text, "нет data-sku"
    sku = found.group(1)
    own = (data.get("products") or {}).get(sku)
    if own is None:
        return text, f"{sku} не описан в {SOURCE.name}"
    if not ANCHOR.search(text):
        return text, (f"{sku}: не найден блок «когда применять» — "
                      f"сначала tools/build_product_fit.py --write")

    new = ANCHOR.sub(
        lambda m: m.group(1) + block(data.get("common") or [], own),
        text, count=1)
    if new == text:
        return text, ""
    return new, ("возражения обновлены" if EXISTING in text
                 else "возражения поставлены")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    pages = sorted(PRODUCTS.glob("*.html"))
    changed, problems = [], []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        new, what = render(path, data)
        if what and new == text:
            problems.append(f"{path.name}: {what}")
            continue
        if new != text:
            changed.append((path.name, what))
            if args.write:
                path.write_text(new, encoding="utf-8")

    described = set(data.get("products") or {})
    on_pages = {re.search(r'data-sku="([^"]+)"', p.read_text(encoding="utf-8")).group(1)
                for p in pages if re.search(r'data-sku="([^"]+)"',
                                            p.read_text(encoding="utf-8"))}
    for extra in sorted(described - on_pages):
        problems.append(f"{extra} описан в {SOURCE.name}, но страницы товара нет")

    lines = len(data.get("common") or []) + 1
    print(f"Страниц товаров: {len(pages)}; строк у цены: {lines}")
    for name, what in changed:
        print(f"   {'записано' if args.write else 'изменится'}: {name} — {what}")
    for line in problems:
        print(f"   ДЕФЕКТ {line}")

    if problems:
        return 1
    if args.check and changed:
        print("Возражения разошлись с источником: "
              "python3 tools/build_objections.py --write")
        return 1
    if not changed:
        print("   расхождений нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
