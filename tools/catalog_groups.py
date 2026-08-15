#!/usr/bin/env python3
"""Каталог главной — группами по моменту работы, а не одной лентой.

Замер 11.08.2026 на 390px (playwright, viewport 390×844):

    главная целиком      31 214px = 37 экранов
    секция #catalog      16 638px = 20 экранов
    25 карточек          15 228px, в среднем 609px на карточку
    перечни документов    4 947px из них

То есть больше половины главной — одна непрерывная лента из 25 карточек
без единой опоры. Пролистать её до нужного товара нельзя: ориентиров нет,
и человек листает, пока не устанет.

Что делает инструмент. Раскладывает карточки по шести группам и оборачивает
каждую в `<details class="product-group" open>`. Порядок групп — порядок
моментов, в которые субподрядчик приходит за документом: до подписания,
пока идут работы, закрытие и оплата, удержания и споры, банкротство
заказчика, бесплатное. Перед каталогом ставит полосу переходов по группам.

Почему `<details>` с `open` в разметке, а не свёрнутое состояние. На
десктопе каталог сеткой в три колонки и в опоре не нуждается — там всё
открыто. Свёртку на телефоне делает `attribution.js`: он снимает `open`
со всех групп, кроме первой. Без JS страница остаётся такой же, как
сегодня, — это ухудшение до текущего состояния, а не поломка.

    python3 tools/catalog_groups.py           # показать, что изменится
    python3 tools/catalog_groups.py --write   # разложить

Повторный прогон ничего не дублирует: если группы уже стоят, инструмент
разбирает их обратно в плоский список и собирает заново — так правка
состава каталога подхватывается, а не расходится с разметкой.

Товар, которого нет в карте групп, не теряется: он уходит в последнюю
группу, и инструмент называет его вслух. Молча спрятать товар — дороже,
чем поставить его не в ту группу.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "index.html")

# Группы в порядке появления. Ключ — идентификатор якоря, значение —
# заголовок, короткая подпись и перечень sku. Это данные, а не код:
# состав каталога меняется здесь, а не в разметке.
GROUPS = [
    ("do-podpisaniya", "До подписания",
     "Договор, аванс, смета, расчёт метрами — пока условия ещё можно менять",
     ["p7", "p8", "p13", "p11", "t6"]),
    ("po-hodu-rabot", "Пока идут работы",
     "Исполнительная документация и дополнительные объёмы",
     ["p4", "p2"]),
    ("zakrytie-i-oplata", "Закрытие и оплата",
     "КС-2, передача комплекта и первый шаг, когда денег нет",
     ["p3", "p1", "t2", "t1", "t3"]),
    ("uderzhaniya-i-spory", "Удержания и споры",
     "Гарантийное удержание, штрафы, спор о сумме",
     ["p5", "p12"]),
    ("bankrotstvo", "Банкротство заказчика",
     "Реестр требований кредиторов и работа с управляющим",
     ["p9", "p10", "t4"]),
    ("besplatno", "Бесплатные материалы",
     "Проверочные листы и бланки — без оплаты и регистрации",
     []),  # пустой перечень: сюда уходит всё, что не названо выше
]

CARD = re.compile(r'\s*<article class="product-card".*?</article>', re.S)
SKU = re.compile(r'data-sku="([a-z0-9]+)"')
# Сетка закрывается меткой, а не первым попавшимся </div>: после первого же
# прогона внутри сетки появляются свои </div>, и поиск «до ближайшего»
# отрезал бы каталог посередине. Замер: без метки повторный прогон терял
# все карточки.
END = "<!-- /product-grid -->"
# Метку ищем первой и только потом — «до ближайшего </div>». Одним
# выражением с альтернативой это не делается: `.*?` берёт самое раннее
# совпадение любой ветки, то есть внутренний </div>.
GRID_MARKED = re.compile(
    r'(<div class="product-grid">)(.*?)(\n\s*</div>\s*' + re.escape(END) + r')',
    re.S)
GRID_PLAIN = re.compile(r'(<div class="product-grid">)(.*?)(\n\s*</div>)', re.S)
JUMP = re.compile(r'\s*<nav class="catalog-jump".*?</nav>', re.S)
GROUP_WRAP = re.compile(
    r'\s*<details class="product-group"[^>]*>\s*<summary.*?</summary>'
    r'\s*<div class="product-grid-inner">(.*?)</div>\s*</details>', re.S)


def flatten(body: str) -> str:
    """Разобрать уже расставленные группы обратно в плоский список карточек."""
    if '<details class="product-group"' not in body:
        return body
    # rstrip обязателен: захват группы забирает отступ перед закрывающим
    # </div>, и без него каждый прогон добавлял бы по пустой строке.
    return "".join(m.group(1).rstrip() for m in GROUP_WRAP.finditer(body))


def build(cards: list[tuple[str, str]]) -> tuple[str, str, list[str]]:
    by_sku = {sku: html for sku, html in cards}
    placed: set = set()
    blocks, chips, unnamed = [], [], []

    for slug, title, note, skus in GROUPS:
        if skus:
            members = [by_sku[s] for s in skus if s in by_sku]
            placed.update(s for s in skus if s in by_sku)
        else:
            members = [html for sku, html in cards if sku not in placed]
            unnamed = [sku for sku, _ in cards
                       if sku not in placed and not sku.startswith("free")]
            placed.update(sku for sku, _ in cards)
        if not members:
            continue
        chips.append(
            f'<a href="#group-{slug}">{title}<span>{len(members)}</span></a>')
        blocks.append(
            f'\n        <details class="product-group" id="group-{slug}" open>'
            f'\n          <summary><span class="product-group-title">{title}</span>'
            f'<span class="product-group-note">{note}</span>'
            f'<span class="product-group-count">{len(members)}</span></summary>'
            f'\n          <div class="product-grid-inner">'
            + "".join(members)
            + '\n          </div>\n        </details>')

    return chips, "".join(blocks), unnamed


def main() -> int:
    write = "--write" in sys.argv
    with open(PAGE, encoding="utf-8") as fh:
        text = fh.read()

    # Старую полосу переходов снимаем до поиска сетки: иначе её вырезание
    # сдвинуло бы границы, по которым собирается новая разметка.
    clean = JUMP.sub("", text)
    grid = GRID_MARKED.search(clean) or GRID_PLAIN.search(clean)
    if not grid:
        print("не найдена сетка каталога .product-grid — разметка изменилась")
        return 1

    body = flatten(grid.group(2))
    cards = []
    for m in CARD.finditer(body):
        sku = SKU.search(m.group(0))
        cards.append((sku.group(1) if sku else f"free{len(cards)}", m.group(0)))
    if not cards:
        print("карточек товара не найдено")
        return 1

    chips, blocks, unnamed = build(cards)

    # Бесплатные материалы лежат своей сеткой ниже групп и в группировку не
    # входят — у них уже есть свой заголовок. В полосу переходов они всё
    # равно попадают: без чипса раздел на телефоне достижим только
    # прокруткой через весь каталог.
    free = clean.count('class="product-card free"')
    if free:
        clean = clean.replace(
            '<div class="section-head catalog-split">',
            '<div class="section-head catalog-split" id="group-besplatno">', 1)
        chips.append(
            f'<a href="#group-besplatno">Бесплатные<span>{free}</span></a>')
    jump = ('\n      <nav class="catalog-jump" aria-label="Разделы каталога">'
            + "".join("\n        " + c for c in chips)
            + '\n      </nav>')
    tail = f'\n      </div>\n      {END}'
    # Голову режем по rstrip: снятая полоса переходов забирает с собой
    # ведущий отступ, а вставляемая приносит свой — без этого каждый прогон
    # оставлял бы после себя лишнюю пустую строку.
    head = clean[:grid.start()].rstrip()
    updated = (head + "\n" + jump.lstrip("\n") + grid.group(1) + blocks
               + tail + clean[grid.end():])

    named = sum(1 for _, t, _, s in GROUPS for _ in s if s)
    if unnamed:
        print("не названы в карте групп, ушли в последнюю: "
              + ", ".join(unnamed))
    print(f"карточек {len(cards)}, групп {blocks.count('<details')}, "
          f"названо в карте {named}")

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
