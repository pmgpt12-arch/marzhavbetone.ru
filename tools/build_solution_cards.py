#!/usr/bin/env python3
"""Карточки главной: что получишь и про тебя ли это, вместо имён файлов.

Замер 15.08.2026 на 390px по шести карточкам главной. Карточка говорила про
документы трижды подряд и ни разу — про покупателя:

    ДОГОВОР ЕЩЁ НЕ ПОДПИСАН
    Договор субподряда
    Всё, что решается до подписания: договор с приложениями,
    допсоглашения, протокол разногласий. 12 файлов.
    · Договор субподряда
    · Перечень работ
    · Календарный план
    2 490 ₽   [Добавить в корзину]

Первый пункт списка дословно повторяет заголовок карточки — те же два
слова в двухстах пикселях друг от друга. Класс при этом называется
`solution-result`, а результата в нём нет: там перечень вложений.

Что ставится взамен, из `data/sales/product-fit.yaml` — того же файла, из
которого собран первый экран страницы товара:

    `result`  →  `.solution-result`  — что окажется на руках;
    `fit`     →  `.solution-points`  — признаки, по которым человек узнаёт
                                       свою ситуацию.

Источник один на карточку и на страницу товара намеренно: два описания
одного комплекта расходятся на первой же правке линейки, и расходятся
молча. Строка «ситуация» (`.solution-when`) остаётся как написана — она
короткая, стоит эйбрау и в источнике не дублируется.

    python3 tools/build_solution_cards.py            # что изменится
    python3 tools/build_solution_cards.py --write    # записать
    python3 tools/build_solution_cards.py --check    # расхождение — код 1
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
PAGE = ROOT / "index.html"

# Сколько признаков ситуации показывать в карточке. Три — столько же строк,
# сколько занимал перечень файлов: карточка не должна вырасти вдвое ради
# правки текста.
POINTS = 3

CARD = re.compile(r'<article class="solution-card">.*?</article>', re.S)
RESULT = re.compile(r'(<p class="solution-result">)(.*?)(</p>)', re.S)
POINTS_BLOCK = re.compile(r'(<ul class="solution-points">)(.*?)(</ul>)', re.S)
SKU = re.compile(r'data-sku="([^"]+)"')


def esc(text: str) -> str:
    return html.escape(" ".join(str(text).split()), quote=False)


def rebuild(card: str, entries: dict, problems: list[str]) -> str:
    found = SKU.search(card)
    if not found:
        problems.append("карточка без data-sku")
        return card
    sku = found.group(1)
    entry = entries.get(sku)
    if entry is None:
        problems.append(f"{sku}: нет записи в {SOURCE.name}")
        return card
    if not RESULT.search(card) or not POINTS_BLOCK.search(card):
        problems.append(f"{sku}: в карточке нет .solution-result "
                        f"или .solution-points")
        return card

    signs = entry.get("fit") or []
    if len(signs) < POINTS:
        problems.append(f"{sku}: признаков ситуации {len(signs)}, "
                        f"нужно хотя бы {POINTS}")
        return card

    card = RESULT.sub(lambda m: m.group(1) + esc(entry["result"]) + m.group(3),
                      card, count=1)
    items = "".join(f"<li>{esc(s)}</li>" for s in signs[:POINTS])
    card = POINTS_BLOCK.sub(lambda m: m.group(1) + items + m.group(3),
                            card, count=1)
    return card


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    entries = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["products"]
    text = PAGE.read_text(encoding="utf-8")
    problems: list[str] = []

    cards = CARD.findall(text)
    if not cards:
        print(f"Карточек .solution-card на {PAGE.name} нет — проверять нечего")
        return 1

    new = CARD.sub(lambda m: rebuild(m.group(0), entries, problems), text)

    changed = new != text
    print(f"Карточек на {PAGE.name}: {len(cards)}; "
          f"признаков ситуации в каждой: {POINTS}")
    if changed:
        print(f"   {'записано' if args.write else 'изменится'}: "
              f"результат и признаки собраны из {SOURCE.name}")
        if args.write:
            PAGE.write_text(new, encoding="utf-8")
    for line in problems:
        print(f"   ДЕФЕКТ {line}")

    if problems:
        return 1
    if args.check and changed:
        print("Карточки разошлись с источником: "
              "python3 tools/build_solution_cards.py --write")
        return 1
    if not changed:
        print("   расхождений нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
