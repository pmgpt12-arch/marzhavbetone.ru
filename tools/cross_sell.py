#!/usr/bin/env python3
"""Допродажа по ситуации, а не по похожести товара.

Замер 15.08.2026 по 18 страницам товаров: у шести стоял блок «С чем это
покупают», у одной «Похожие комплекты», у двенадцати — ничего. Оба
заголовка называют товар («похожий», «покупают вместе»), а не положение
покупателя, и решение о покупке из них не следует: человек пришёл с
конкретной бедой, и «похожий комплект» ему ничего не говорит.

Здесь блок собирается из `data/sales/product-map.csv` и называет
**ситуацию**: «Если ваша ситуация также включает: не возвращают
удержания». Названия ситуаций — заголовки болей из
`data/business/money-pains.yaml`, то есть те же слова, которыми боль
названа в лестнице и в блоке ситуаций на главной.

Что делает инструмент:

  · для каждого товара берёт его боли и допродажи из карты;
  · добавляет товары соседних болей, названные допродажей;
  · пишет блок с ситуацией у каждой карточки;
  · заменяет прежние «Похожие комплекты» и «С чем это покупают», а не
    добавляется рядом с ними — иначе на странице стояло бы два блока
    про одно и то же.

Цена в блоке не печатается намеренно: она живёт в кассе и на странице
товара, а третья копия разошлась бы с ними при первой правке.

    python3 tools/cross_sell.py           # что изменится и покрытие
    python3 tools/cross_sell.py --write   # проставить
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "data" / "sales" / "product-map.csv"
PAINS = ROOT / "data" / "business" / "money-pains.yaml"

MARK_OPEN = '<section class="section cross-sell">'
MAX_CARDS = 3


def pain_titles() -> dict[str, str]:
    import yaml
    data = yaml.safe_load(PAINS.read_text(encoding="utf-8"))
    return {k: (v.get("title") or k) for k, v in (data.get("pains") or {}).items()}


def rows() -> list[dict]:
    with MAP.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def short_name(name: str) -> str:
    inner = re.search(r"«(.+)»", name)
    text = inner.group(1) if inner else name
    return text.split(":")[0].strip()


def catalog_names() -> dict[str, str]:
    text = (ROOT / "products-config.php").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"'([a-z0-9]+)'\s*=>\s*\[\s*'name'\s*=>\s*'((?:[^']|\\')*)'", text):
        out[m.group(1)] = m.group(2).replace("\\'", "'")
    return out


def build_block(sku: str, by_id: dict, titles: dict, names: dict) -> str | None:
    """Собирает блок. Возвращает None, если предлагать нечего."""
    row = by_id[sku]
    own_pains = set(filter(None, row["money_pain"].split(";")))

    # Кандидаты: явные допродажи товара, затем ядра соседних болей,
    # названных его допродажей. Порядок — порядок полезности.
    candidates: list[str] = [c for c in row["cross_sell"].split(";") if c]
    for other in by_id.values():
        if other["product_id"] == sku or other["status"] != "active":
            continue
        other_pains = set(filter(None, other["money_pain"].split(";")))
        if other_pains & own_pains and other["stage"] == "core":
            if other["product_id"] not in candidates:
                candidates.append(other["product_id"])

    cards = []
    for cid in candidates:
        target = by_id.get(cid)
        if not target or not target["product_url"] or target["status"] != "active":
            continue
        # Ситуация берётся из боли товара-кандидата: именно её человек
        # должен узнать в себе, чтобы блок сработал.
        pains = [titles[p] for p in target["money_pain"].split(";") if p in titles]
        situation = pains[0] if pains else ""
        if not situation:
            continue
        href = target["product_url"].replace("/products/", "")
        cards.append(
            f'        <article class="cross-card">'
            f'<p class="cross-when">{situation}</p>'
            f'<h3><a href="{href}">{short_name(names.get(cid, cid))}</a></h3>'
            f'<a class="text-link" href="{href}">Посмотреть комплект →</a>'
            f"</article>"
        )
        if len(cards) >= MAX_CARDS:
            break

    if not cards:
        return None
    body = "\n".join(cards)
    return (f'    {MARK_OPEN}\n'
            f"      <h2>Если ваша ситуация также включает</h2>\n"
            f'      <div class="cross-grid">\n{body}\n      </div>\n'
            f"    </section>\n")


# Прежние блоки о том же. Снимаются вместе с заголовком и содержимым.
OLD_BLOCKS = [
    re.compile(r'[ \t]*<section class="section related">\s*<h2>Похожие комплекты</h2>.*?</section>\n',
               re.S),
    re.compile(r'[ \t]*<section class="section[^"]*">\s*<h2>С чем это покупают</h2>.*?</section>\n',
               re.S),
    re.compile(r'[ \t]*' + re.escape(MARK_OPEN) + r'.*?</section>\n', re.S),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    by_id = {r["product_id"]: r for r in rows()}
    titles = pain_titles()
    names = catalog_names()

    active = [r for r in by_id.values() if r["status"] == "active" and r["product_url"]]
    covered, empty = 0, []
    for row in sorted(active, key=lambda r: r["product_id"]):
        sku = row["product_id"]
        path = ROOT / row["product_url"].lstrip("/")
        if not path.exists():
            continue
        block = build_block(sku, by_id, titles, names)
        if block is None:
            empty.append(sku)
            continue
        covered += 1
        if not args.write:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in OLD_BLOCKS:
            text = pattern.sub("", text)
        # Блок встаёт перед «Полезными материалами», если они есть, иначе
        # перед концом main: допродажа должна идти после состава и цены,
        # но до ухода со страницы.
        anchor = re.search(r'[ \t]*<section class="section related-articles">', text)
        if anchor:
            text = text[:anchor.start()] + block + text[anchor.start():]
        else:
            end = text.rfind("  </main>")
            text = text[:end] + block + text[end:]
        path.write_text(text, encoding="utf-8")

    print(f"Товаров со страницами: {len(active)}; "
          f"с допродажей по ситуации: {covered}")
    if empty:
        print(f"Без допродажи ({len(empty)}): {', '.join(sorted(empty))}")
        print("  Это не дефект инструмента: у этих товаров в карте нет "
              "соседей по боли. Состав лестницы — решение владельца (Р-006).")
    if args.write:
        print("записано")
    else:
        print("показ, файлы не изменены. Проставить — с --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
