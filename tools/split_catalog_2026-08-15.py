#!/usr/bin/env python3
"""Разовый перенос: полный каталог с главной на свою страницу.

Замер 15.08.2026 (`tools/check_desktop.py`, рендер на 1366/1440/1920):

    главная уходит вбок          1399px против 1366px, 1472px против 1440px
    длина главной                33,2 экрана на 1366, 22,5 на 1920
    цепочка переполнения         .product-grid → .product-card → h3 → a
    заголовок шире своей коробки на 64px

Причина обеих поломок одна: на главной стоит весь каталог — 25 карточек в
шести группах. Он же даёт длину, он же распирает страницу вбок, потому что
названия комплектов идут в h3 размером clamp(34px,4vw,54px) и в сетке без
`min-width:0` колонка не может стать уже своего самого длинного слова.

Что делает скрипт:

  · переносит секцию каталога в новую страницу `katalog.html` целиком —
    вместе с полосой переходов, группами и всеми карточками;
  · переносит туда же разметку `ItemList`: она описывает каталог, и её
    место там, где каталог;
  · ставит на главную короткий блок решений — шесть комплектов по числу
    ситуаций, которые уже названы в блоке «Что происходит на вашем
    объекте», и ссылку на полный каталог.

Идентификатор `id="catalog"` на главной сохраняется. Это не косметика: на
якорь `#catalog` ссылаются 91 раз из 74 файлов, и снятие идентификатора
увело бы все эти ссылки в никуда.

Содержимое коротких карточек не сочиняется. Ситуация берётся из блока
`#situations`, название — из имени комплекта до двоеточия, результат — из
лида карточки каталога, пункты — первые три строки её же перечня
документов. Имя в `data-product` переносится дословно: корзина сверяет
товар по нему (`app.js`, `item.name === button.dataset.product`), и любая
правка этой строки тихо ломает покупку.

Скрипт разовый и повторного прогона не предполагает: после него каталог
живёт в `katalog.html`, и туда же переведены `catalog_groups.py` и
`sync_catalog.py`.

    python3 tools/split_catalog_2026-08-15.py           # показать, что будет
    python3 tools/split_catalog_2026-08-15.py --write   # перенести
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
KATALOG = ROOT / "katalog.html"

# Шесть комплектов по числу ситуаций блока #situations. Порядок — порядок
# ситуаций: от «договор ещё не подписан» до «у заказчика деньги кончились».
# Седьмой комплект линейки (p4, исполнительная документация) в блоке
# ситуаций отсутствует и сегодня — состав витрины решает владелец (Р-006),
# и здесь он не меняется. С главной p4 достижим через «Все решения».
FEATURED = ["p7", "p2", "p3", "p1", "p5", "p9"]

CATALOG_OPEN = '<section class="section sales-solutions" id="catalog">'
NEXT_SECTION = '<section class="section checklist" id="checklist">'


def fail(message: str) -> None:
    print(f"Перенос не сделан: {message}", file=sys.stderr)
    raise SystemExit(1)


def cut_catalog(text: str) -> tuple[str, str]:
    """Возвращает (разметка каталога, текст без неё)."""
    start = text.find(CATALOG_OPEN)
    end = text.find(NEXT_SECTION)
    if start < 0 or end < 0 or end < start:
        fail("секция каталога не найдена по своим меткам")
    return text[start:end], text[:start] + text[end:]


def cut_itemlist(text: str) -> tuple[str, str]:
    """Вырезает запись ItemList из @graph вместе с её запятой."""
    marker = '      "@type": "ItemList",'
    pos = text.find(marker)
    if pos < 0:
        fail("разметка ItemList не найдена")
    start = text.rfind("    {\n", 0, pos)
    if start < 0:
        fail("начало записи ItemList не найдено")
    # Конец записи — строка `    },` того же уровня после её начала.
    end = text.find("\n    },\n", pos)
    if end < 0:
        fail("конец записи ItemList не найден")
    end += len("\n    },\n")
    return text[start:end], text[:start] + text[end:]


def parse_cards(catalog: str) -> dict[str, dict[str, object]]:
    """Разбирает карточки каталога в данные. Ничего не досочиняет: чего в
    разметке нет, того не будет и в короткой карточке."""
    out: dict[str, dict[str, object]] = {}
    for card in re.findall(r"<article class=\"product-card\".*?</article>", catalog, re.S):
        sku = re.search(r'data-sku="([^"]+)"', card)
        if not sku:
            continue
        name = re.search(r'data-product="([^"]+)"', card)
        price = re.search(r'data-price="(\d+)"', card)
        href = re.search(r'<h3><a href="([^"]+)"', card)
        number = re.search(r'<div class="product-number">([^<]*)</div>', card)
        lead = re.search(r"</h3><p>(.*?)</p>", card, re.S)
        docs = re.findall(r"<li>(.*?)</li>", card, re.S)
        shown = re.search(r"<strong>([^<]*)</strong>", card)
        if not (name and price and href):
            continue
        out[sku.group(1)] = {
            "name": name.group(1),
            "price": int(price.group(1)),
            "shown_price": shown.group(1).strip() if shown else "",
            "href": href.group(1),
            "number": number.group(1).strip() if number else "",
            "lead": lead.group(1).strip() if lead else "",
            "docs": [d.strip() for d in docs[:3]],
        }
    return out


def situations(text: str) -> dict[str, str]:
    """Ситуация под каждый комплект — из блока #situations, а не заново."""
    start = text.find('<section class="section" id="situations">')
    end = text.find("</section>", start)
    if start < 0:
        fail("блок ситуаций не найден")
    block = text[start:end]
    out = {}
    for href, title in re.findall(r'<h3><a href="products/([^"]+)">([^<]+)</a></h3>', block):
        sku = href.split("-")[0]
        out[sku] = title.strip()
    return out


def short_title(name: str) -> str:
    """Короткое имя комплекта: то, что стоит до двоеточия. Полное имя
    остаётся в data-product — по нему корзина сверяет товар."""
    inner = re.search(r"«(.+)»", name)
    text = inner.group(1) if inner else name
    return text.split(":")[0].strip()


def solutions_block(cards: dict, where: dict) -> str:
    items = []
    for sku in FEATURED:
        card = cards.get(sku)
        if card is None:
            fail(f"комплект {sku} не найден в каталоге")
        bullets = "".join(f"<li>{d}</li>" for d in card["docs"])
        when = where.get(sku, "")
        when_html = f'<p class="solution-when">{when}</p>' if when else ""
        items.append(
            f'<article class="solution-card">{when_html}'
            f'<h3><a href="{card["href"]}">{short_title(card["name"])}</a></h3>'
            f'<p class="solution-result">{card["lead"]}</p>'
            f'<ul class="solution-points">{bullets}</ul>'
            f'<div class="product-footer"><strong>{card["shown_price"]}</strong>'
            f'<button class="button add-to-cart" type="button" '
            f'data-product="{card["name"]}" data-sku="{sku}" '
            f'data-price="{card["price"]}">Добавить в корзину</button></div>'
            f"</article>"
        )
    cards_html = "\n        ".join(items)
    return (
        '    <section class="section solutions" id="catalog">\n'
        '      <div class="section-head row">\n'
        '        <div><p class="eyebrow">ГОТОВЫЕ РЕШЕНИЯ</p>'
        "<h2>Комплект под вашу ситуацию</h2>"
        '<p class="lead">Шаблоны, чек-листы и порядок действий — под тот момент, '
        "в котором вы сейчас находитесь.</p></div>\n"
        '        <a class="text-link" href="katalog.html">Все решения →</a>\n'
        "      </div>\n"
        '      <div class="solution-grid">\n'
        f"        {cards_html}\n"
        "      </div>\n"
        '      <p class="solutions-more"><a class="text-link" href="katalog.html">'
        "Полный каталог: комплекты, отдельные документы и бесплатные материалы →</a></p>\n"
        "    </section>\n\n"
    )


HEAD = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Каталог документов для строительных \
субподрядчиков: комплекты с шаблонами КС-2, КС-3, актами, претензиями и \
алгоритмами получения оплаты, отдельные документы и бесплатные материалы.">
  <link rel="canonical" href="https://marzhavbetone.ru/katalog.html">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Каталог документов для строительных подрядчиков">
  <meta property="og:description" content="Комплекты, отдельные документы и \
бесплатные материалы — по моменту работы: до подписания, по ходу работ, \
закрытие и оплата, удержания и споры, банкротство заказчика.">
  <meta property="og:url" content="https://marzhavbetone.ru/katalog.html">
  <link rel="alternate" type="application/rss+xml" title="Маржа в бетоне" href="/rss.xml">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="alternate icon" href="/favicon.ico">
  <title>Каталог документов для строительных подрядчиков — Маржа в бетоне</title>
"""


def build_katalog(index_text: str, catalog: str, itemlist: str) -> str:
    styles = "\n".join(re.findall(r'  <link rel="stylesheet" href="[^"]+">', index_text))
    topbar_start = index_text.find('  <header class="topbar">')
    topbar_end = index_text.find("  <main id=\"top\">")
    shell_top = index_text[topbar_start:topbar_end]
    # На каталоге разделы главной недостижимы якорем: ссылки ведут на главную.
    shell_top = shell_top.replace('href="#catalog"', 'href="katalog.html"')
    shell_top = shell_top.replace('href="#checklist"', 'href="/#checklist"')
    shell_top = shell_top.replace('href="#author"', 'href="/#author"')
    shell_top = shell_top.replace('href="#situations"', 'href="/diagnostika.html"')
    shell_top = shell_top.replace('href="#top"', 'href="/"')
    shell_top = shell_top.replace(">Найти решение<", ">Подобрать комплект<")

    footer_start = index_text.find("  <footer>")
    shell_bottom = index_text[footer_start:]
    # Диалог чек-листа живёт на главной: здесь его нечем открыть.
    dialog = re.search(r'  <dialog id="checklist-dialog">.*?</dialog>\n\n', shell_bottom, re.S)
    if dialog:
        shell_bottom = shell_bottom.replace(dialog.group(0), "")

    breadcrumbs = """  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Главная",
          "item": "https://marzhavbetone.ru/"
        },
        {
          "@type": "ListItem",
          "position": 2,
          "name": "Каталог документов",
          "item": "https://marzhavbetone.ru/katalog.html"
        }
      ]
    },
"""
    graph_close = "    ]\n  }\n  </script>\n"

    return (
        HEAD
        + styles
        + "\n"
        + breadcrumbs
        + itemlist.rstrip(",\n")
        + "\n"
        + graph_close
        + "</head>\n<body>\n"
        + shell_top
        + '  <main id="top">\n'
        '    <nav class="breadcrumbs" aria-label="Хлебные крошки">'
        '<a href="/">Главная</a><span>·</span><span>Каталог документов</span></nav>\n\n'
        + catalog.rstrip()
        + "\n\n"
        + shell_bottom
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    text = INDEX.read_text(encoding="utf-8")
    if KATALOG.exists() and not args.write:
        print("katalog.html уже существует — перенос уже сделан")
    catalog, rest = cut_catalog(text)
    itemlist, rest = cut_itemlist(rest)
    cards = parse_cards(catalog)
    where = situations(text)

    missing = [s for s in FEATURED if s not in cards]
    if missing:
        fail(f"в каталоге нет комплектов: {', '.join(missing)}")

    block = solutions_block(cards, where)
    new_index = rest.replace(NEXT_SECTION, block + "    " + NEXT_SECTION.lstrip(), 1)
    katalog = build_katalog(text, catalog, itemlist)

    print(f"каталог: {len(cards)} карточек, {len(catalog)} знаков → katalog.html")
    print(f"разметка ItemList: {len(itemlist)} знаков → katalog.html")
    print(f"на главной остаётся решений: {len(FEATURED)} — {', '.join(FEATURED)}")
    for sku in FEATURED:
        print(f"  · {sku}: {short_title(cards[sku]['name'])} "
              f"— {where.get(sku, 'ситуация не найдена')}")
    print(f"главная: {len(text)} → {len(new_index)} знаков")

    if not args.write:
        print("\nпоказ, файлы не изменены. Записать — с --write")
        return 0

    KATALOG.write_text(katalog, encoding="utf-8")
    INDEX.write_text(new_index, encoding="utf-8")
    print("\nзаписано: katalog.html, index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
