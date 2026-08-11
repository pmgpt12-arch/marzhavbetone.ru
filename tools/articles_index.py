#!/usr/bin/env python3
"""Витрина разборов — с фильтром по темам вместо ленты из 36 карточек.

Замер 11.08.2026 на 390px (playwright, viewport 390×844, страница по http):
витрина `articles/index.html` — 20 638px, 24,5 экрана, 36 карточек подряд.
Ни фильтра, ни группировки, ни счётчика: чтобы понять, есть ли на сайте
разбор про удержания, надо пролистать всю ленту и запомнить, что видел.

Что делает инструмент. Проставляет каждой карточке `data-cluster` из карты
кластеров `tools/link_audit.py` — той же, по которой считается связность
сайта, чтобы вторая карта тем не завелась, — и ставит перед сеткой полосу
тем со счётчиками. Фильтрацию и показ по частям делает `attribution.js`.

Карта кластеров одна на репозиторий. Разбор, не попавший ни в один
кластер, получает `data-cluster="prochee"` и называется вслух: молча
спрятать материал из фильтра дороже, чем показать его в «прочем».

    python3 tools/articles_index.py           # показать, что изменится
    python3 tools/articles_index.py --write   # проставить

Повторный прогон ничего не дублирует: полоса тем и атрибуты переписываются
целиком, а не дописываются.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_audit import CLUSTERS  # noqa: E402  единственная карта тем

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "articles", "index.html")

CARD = re.compile(r'<a class="showcase-card"(?P<attrs>[^>]*)href="(?P<href>[^"]+)"')
HAS_CLUSTER = re.compile(r'\s*data-cluster="[^"]*"')
# Полосу снимаем вместе с отступом до и после неё, а затем ставим сетку на
# заведомо известный отступ. Иначе повторный прогон копит пустые строки:
# снятие забирает один отступ, вставка приносит свой.
FILTER = re.compile(r'[ \t]*<nav class="topic-filter".*?</nav>\n?', re.S)
GRID = re.compile(r'\n[ \t]*<div class="showcase-grid">')

# Короткие подписи для полосы: полное название кластера в чипсе не помещается
# на 390px, а обрезка многоточием прячет как раз различающую часть.
SHORT = {
    "исполнительная документация": "Исполнительная",
    "банкротство и реестр кредиторов": "Банкротство",
    "неоплата и закрытие работ": "Неоплата",
    "передача площадки и входной контроль": "Передача площадки",
    "гарантийное удержание": "Удержание",
    "договор субподряда": "Договор",
}


def slug(name: str) -> str:
    table = str.maketrans(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя ",
        "abvgdeejzijklmnoprstufhccss_y_eua-")
    return name.translate(table).replace("--", "-")


def main() -> int:
    write = "--write" in sys.argv
    with open(PAGE, encoding="utf-8") as fh:
        text = fh.read()

    of_file = {}
    for name, members in CLUSTERS.items():
        for member in members:
            of_file[member] = name

    counts: dict = {}
    unassigned = []

    def stamp(m: re.Match) -> str:
        href = m.group("href").split("/")[-1]
        name = of_file.get(href)
        if name is None:
            unassigned.append(href)
            name = "прочее"
        counts[name] = counts.get(name, 0) + 1
        attrs = HAS_CLUSTER.sub("", m.group("attrs"))
        return (f'<a class="showcase-card" data-cluster="{slug(name)}"'
                f'{attrs}href="{m.group("href")}"')

    updated = CARD.sub(stamp, text)

    order = [n for n in CLUSTERS if n in counts] + (
        ["прочее"] if "прочее" in counts else [])
    chips = [f'<button type="button" class="is-active" data-cluster="">'
             f'Все<span>{sum(counts.values())}</span></button>']
    chips += [f'<button type="button" data-cluster="{slug(n)}">'
              f'{SHORT.get(n, n[0].upper() + n[1:])}<span>{counts[n]}</span>'
              f'</button>' for n in order]
    bar = ('\n    <nav class="topic-filter" aria-label="Темы разборов">'
           + "".join("\n      " + c for c in chips)
           + '\n    </nav>')

    updated = FILTER.sub("", updated)
    updated = GRID.sub(bar + '\n    <div class="showcase-grid">',
                       updated, count=1)

    if unassigned:
        print("вне карты кластеров, ушли в «прочее»: "
              + ", ".join(sorted(set(unassigned))))
    print(f"карточек {sum(counts.values())}, тем в полосе {len(chips)}")

    if updated == text:
        print("разметка уже такая, менять нечего")
        return 0
    if not write:
        print("прогон без изменений; чтобы записать — --write")
        return 0
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(updated)
    print("записано")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
