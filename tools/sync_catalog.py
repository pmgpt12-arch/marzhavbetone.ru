#!/usr/bin/env python3
"""Сверяет и приводит в порядок витрину главной и её разметку для поиска.

Замер 11.08.2026: на витрине 22 карточки, в `ItemList` — 15 позиций. Три
бесплатные позиции разметки названы именами, которых на витрине давно нет
(«Почему не платят по КС-2: 7 скрытых причин» и ещё две), и ведут на якорь
`#checklist`, тогда как материалов в `/materialy/` девять. Товар P10 стоит на
витрине, покупается на своей странице и в разметке отсутствует вовсе.

То есть поисковик видел каталог, которого нет: три несуществующих товара, шесть
недостающих бесплатных и один недостающий платный.

Разметка собирается из двух источников правды, а не пишется руками:
цены и названия платных — из `products-config.php`, откуда их берёт касса;
бесплатные — из карточек самой витрины. Разойтись молча они после этого не
могут: расхождение видно этой же проверкой.

    python3 tools/sync_catalog.py            # показать расхождения
    python3 tools/sync_catalog.py --write    # переписать ItemList
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
CONFIG = ROOT / "products-config.php"
SITE = "https://marzhavbetone.ru"

# Товары, которых на витрине быть не должно
HIDDEN = {"test1"}


def paid_products() -> dict[str, tuple[str, int]]:
    text = CONFIG.read_text(encoding="utf-8")
    out: dict[str, tuple[str, int]] = {}
    for match in re.finditer(
            r"'([a-z0-9]+)' => \[\s*'name'\s*=> '((?:[^']|\\')*)',\s*'price' => (\d+)", text):
        sku, name, price = match.group(1), match.group(2).replace("\\'", "'"), int(match.group(3))
        if sku not in HIDDEN:
            out[sku] = (name, price // 100)
    return out


def storefront(text: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Что стоит на витрине: sku платных и (адрес, заголовок, описание) бесплатных."""
    cards = re.findall(r'<article class="product-card[^"]*".*?</article>', text, flags=re.S)
    paid: list[str] = []
    free: list[tuple[str, str, str]] = []
    for card in cards:
        link = re.search(r'href="(products/([a-z0-9]+)-[^"]+)"', card)
        if link and "free" not in card[:60]:
            paid.append(link.group(2))
            continue
        material = re.search(r'href="(materialy/[^"]+)"', card)
        title = re.search(r"<h3><a[^>]*>(.*?)</a></h3>", card, flags=re.S)
        note = re.search(r"</h3>\s*<p>(.*?)</p>", card, flags=re.S)
        if material and title:
            free.append((material.group(1),
                         re.sub(r"<[^>]+>", "", title.group(1)).strip(),
                         re.sub(r"<[^>]+>", "", note.group(1)).strip() if note else ""))
    return paid, free


def item(position: int, name: str, description: str, url: str, price: str) -> dict:
    return {
        "@type": "ListItem",
        "position": position,
        "item": {
            "@type": "Product",
            "name": name,
            "description": description,
            "brand": {"@id": f"{SITE}/#organization"},
            "offers": {
                "@type": "Offer",
                "url": url,
                "price": price,
                "priceCurrency": "RUB",
                "availability": "https://schema.org/InStock",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    text = INDEX.read_text(encoding="utf-8")
    products = paid_products()
    shown_paid, shown_free = storefront(text)

    problems: list[str] = []
    for sku in shown_paid:
        if sku not in products:
            problems.append(f"на витрине есть {sku}, в products-config.php его нет")
    for sku in products:
        if sku not in shown_paid:
            problems.append(f"в кассе есть {sku}, на витрине его нет")

    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, flags=re.S)
    if not block:
        print("на главной нет блока разметки — сверять нечего")
        return 1
    graph = json.loads(block.group(1))
    lists = [node for node in graph["@graph"] if node.get("@type") == "ItemList"]
    if not lists:
        print("в разметке главной нет ItemList")
        return 1
    old = lists[0]["itemListElement"]

    # Собираем заново: сначала платные в порядке витрины, следом бесплатные
    fresh: list[dict] = []
    position = 0
    for sku in shown_paid:
        name, price = products[sku]
        page = re.search(rf'href="(products/{sku}-[^"]+)"', text)
        position += 1
        # Описание берём из прежней разметки, если оно там было: это текст,
        # написанный руками, и переписывать его скриптом нельзя.
        previous = next((x["item"].get("description", "") for x in old
                         if f"/{sku}-" in x["item"]["offers"]["url"]), "")
        fresh.append(item(position, name, previous or name,
                          f"{SITE}/{page.group(1)}" if page else f"{SITE}/#catalog", str(price)))
    for url, title, note in shown_free:
        position += 1
        fresh.append(item(position, title, note or title, f"{SITE}/{url}", "0"))

    was = {x["item"]["offers"]["url"] for x in old}
    now = {x["item"]["offers"]["url"] for x in fresh}
    print(f"Позиций в разметке: было {len(old)}, стало {len(fresh)} "
          f"(платных {len(shown_paid)}, бесплатных {len(shown_free)})")
    for url in sorted(was - now):
        print(f"  убрано, на витрине этого нет: {url}")
    for url in sorted(now - was):
        print(f"  добавлено: {url}")

    for problem in problems:
        print(f"  РАСХОЖДЕНИЕ: {problem}")

    if fresh != old:
        lists[0]["itemListElement"] = fresh
        if args.write:
            updated = json.dumps(graph, ensure_ascii=False, indent=2)
            text = text[:block.start(1)] + "\n" + updated + "\n  " + text[block.end(1):]
            INDEX.write_text(text, encoding="utf-8")
            print("Разметка переписана.")
        else:
            print("Это показ. Записать: --write")
    else:
        print("Разметка совпадает с витриной.")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
