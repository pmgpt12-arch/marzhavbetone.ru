#!/usr/bin/env python3
"""Допродажа после покупки на success.html — из карты товаров, не наугад.

Замер 15.08.2026: страница благодарности показывала состав заказа и ссылки
на скачивание и ничем не заканчивалась. Купивший один комплект не узнавал о
следующем — при том, что это самый дешёвый показ на сайте: человек уже
заплатил, доверие максимально, а платить второй раз не надо ни за трафик,
ни за прогрев.

Что делает инструмент: собирает из `data/sales/product-map.csv` таблицу
«купленный sku → что предложить» и вставляет её в `success.html` вместе с
блоком, который выбирает предложение по фактическому составу заказа.
Случайных товаров не показывает: если для купленного sku в карте ничего
нет, блок не появляется вовсе.

Предложение берётся из той же связи «по ситуации», что и допродажа на
странице товара, — но здесь выводится словами о положении покупателя:
«вы закрыли <боль>, часто следом приходит <боль>».

    python3 tools/build_upsell.py           # показать
    python3 tools/build_upsell.py --write   # вставить
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "data" / "sales" / "product-map.csv"
PAGE = ROOT / "success.html"
PAINS = ROOT / "data" / "business" / "money-pains.yaml"

BEGIN = "  <!-- upsell:begin -->"
END = "  <!-- upsell:end -->"


def short_name(name: str) -> str:
    inner = re.search(r"«(.+)»", name)
    text = inner.group(1) if inner else name
    return text.split(":")[0].strip()


def catalog_names() -> dict[str, str]:
    text = (ROOT / "products-config.php").read_text(encoding="utf-8")
    return {m.group(1): m.group(2).replace("\\'", "'") for m in
            re.finditer(r"'([a-z0-9]+)'\s*=>\s*\[\s*'name'\s*=>\s*'((?:[^']|\\')*)'", text)}


def build_map() -> dict[str, dict]:
    import yaml
    titles = {k: v.get("title", k) for k, v in
              (yaml.safe_load(PAINS.read_text(encoding="utf-8")).get("pains") or {}).items()}
    names = catalog_names()
    with MAP.open(encoding="utf-8") as fh:
        rows = {r["product_id"]: r for r in csv.DictReader(fh)}

    out: dict[str, dict] = {}
    for sku, row in rows.items():
        if row["status"] != "active" or not row["product_url"]:
            continue
        own = set(filter(None, row["money_pain"].split(";")))
        # Кандидаты сортируются так, чтобы вперёд шли те, чья боль
        # отличается от уже закрытой. Иначе выходит «вы закрыли допработы,
        # следом приходят допработы» — предложение, которое покупатель
        # читает как ошибку, потому что это и есть ошибка.
        candidates = [c for c in row["cross_sell"].split(";") if c]
        def differs(cid: str) -> int:
            target = rows.get(cid)
            if not target:
                return 2
            other = set(filter(None, target["money_pain"].split(";")))
            return 0 if other - own else 1
        for cid in sorted(candidates, key=differs):
            target = rows.get(cid)
            if not target or target["status"] != "active" or not target["product_url"]:
                continue
            target_pains = [p for p in target["money_pain"].split(";")
                            if p in titles and p not in own] or \
                           [p for p in target["money_pain"].split(";") if p in titles]
            if not target_pains:
                continue
            # Ситуация, которую покупатель уже закрыл, и та, что часто
            # приходит следом. Обе — словами лестницы, а не выдуманными.
            closed = next((titles[p] for p in own if p in titles), "")
            out[sku] = {
                "url": target["product_url"],
                "name": short_name(names.get(cid, cid)),
                "closed": closed,
                "next": titles[target_pains[0]],
            }
            break
    return out


BLOCK = """  <!-- upsell:begin -->
  <script>
    // Таблица собирается tools/build_upsell.py из data/sales/product-map.csv.
    // Руками не правится: разойдётся с каталогом на первой правке состава.
    window.MVB_UPSELL = %(map)s;
  </script>
  <!-- upsell:end -->
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    mapping = build_map()
    text = PAGE.read_text(encoding="utf-8")

    print(f"Товаров с предложением после покупки: {len(mapping)}")
    for sku, item in sorted(mapping.items()):
        print(f"   {sku} → {item['name']} (следом: {item['next']})")

    if not args.write:
        print("\nпоказ, файл не изменён. Вставить — с --write")
        return 0

    block = BLOCK % {"map": json.dumps(mapping, ensure_ascii=False, indent=2)}
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END) + len(END) + 1
        text = text[:start] + block + text[finish:]
    else:
        anchor = text.rindex("</body>")
        text = text[:anchor] + block + text[anchor:]
    PAGE.write_text(text, encoding="utf-8")
    print("\nзаписано: success.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
