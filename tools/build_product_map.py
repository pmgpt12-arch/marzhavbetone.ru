#!/usr/bin/env python3
"""Единая карта товаров: data/sales/product-map.csv.

Карта не пишется рукой. Она собирается из трёх уже существующих
источников, и это принципиально: рукописная карта расходится с каталогом
на первой же правке цены, а расхождение здесь стоит денег — по этой карте
подбирается допродажа и следующий шаг после покупки.

    products-config.php          цена, имя, sku — то же, что видит касса
    data/business/money-pains.yaml  боль, ступень лестницы, допродажа
    products/*.html              наличие страницы товара

Что проверяется на выходе:

  · все товары каталога попали в карту, ни один не потерян;
  · нет ссылок на несуществующие страницы — ни у товара, ни у допродажи,
    ни у бесплатного входа;
  · нет повторов product_id;
  · цена в карте совпадает с ценой кассы;
  · допродажа не ссылается на сам товар.

    python3 tools/build_product_map.py            # показать
    python3 tools/build_product_map.py --write    # записать
    python3 tools/build_product_map.py --check    # только проверить
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sales" / "product-map.csv"
PAINS = ROOT / "data" / "business" / "money-pains.yaml"

FIELDS = ["product_id", "product_url", "money_pain", "stage", "price",
          "primary_landing", "free_entry", "cross_sell", "upsell", "bundle",
          "status"]


def catalog() -> dict[str, dict]:
    """Товары кассы: sku → имя и цена в рублях."""
    text = (ROOT / "products-config.php").read_text(encoding="utf-8")
    out: dict[str, dict] = {}
    for m in re.finditer(
            r"'([a-z0-9]+)'\s*=>\s*\[\s*'name'\s*=>\s*'((?:[^']|\\')*)',\s*"
            r"'price'\s*=>\s*(\d+)", text):
        out[m.group(1)] = {
            "name": m.group(2).replace("\\'", "'"),
            "price": int(m.group(3)) // 100,
        }
    return out


def pains() -> dict:
    """Лестница болей. Разбирается построчно: yaml в окружении может не быть,
    а ставить зависимость ради одного файла — лишнее."""
    try:
        import yaml
        return yaml.safe_load(PAINS.read_text(encoding="utf-8")).get("pains", {})
    except ImportError:
        pass
    out, current, key = {}, None, None
    for line in PAINS.read_text(encoding="utf-8").splitlines():
        if re.match(r"^  (MP-\d+):", line):
            key = line.strip().rstrip(":")
            current = out.setdefault(key, {})
        elif current is not None and line.startswith("    "):
            m = re.match(r"^    (\w+):\s*(.*)$", line)
            if m:
                current[m.group(1)] = m.group(2)
    return out


def product_page(sku: str) -> str | None:
    for path in sorted((ROOT / "products").glob(f"{sku}-*.html")):
        return f"/products/{path.name}"
    return None


def build() -> tuple[list[dict], list[str]]:
    import yaml
    data = yaml.safe_load(PAINS.read_text(encoding="utf-8"))
    cat = catalog()
    problems: list[str] = []

    # sku → (боль, ступень, бесплатный вход, допродажа)
    meta: dict[str, dict] = {}
    for pain_id, pain in (data.get("pains") or {}).items():
        free = (pain.get("free") or [None])[0]
        for stage in ("entry", "core"):
            node = pain.get(stage)
            if not node:
                continue
            sku = node.get("sku")
            if not sku:
                continue
            # Один и тот же входной товар обслуживает две боли (t3 —
            # MP-2 и MP-4). Первая записанная выигрывает, вторая
            # добавляется в список: терять связь нельзя.
            entry = meta.setdefault(sku, {"pains": [], "stage": stage,
                                          "free": free, "cross": []})
            entry["pains"].append(pain_id)
            entry["stage"] = "entry" if stage == "entry" else entry["stage"]
            if stage == "core":
                entry["cross"] = list(pain.get("cross_sell") or [])
                entry["free"] = entry["free"] or free

    # Обратная привязка: товар, которого нет ни во входе, ни в ядре ни одной
    # боли, но который назван чьей-то допродажей, относится к той же боли.
    # Иначе семь товаров каталога числились бы «ни к чему не привязанными»
    # только потому, что лестница описывает их со стороны покупателя, а не
    # со стороны товара.
    for pain_id, pain in (data.get("pains") or {}).items():
        for sku in (pain.get("cross_sell") or []):
            if sku in cat and sku not in meta:
                meta[sku] = {"pains": [pain_id], "stage": "cross",
                             "free": (pain.get("free") or [None])[0], "cross": []}
            elif sku in meta and pain_id not in meta[sku]["pains"]:
                meta[sku]["pains"].append(pain_id)

    rows: list[dict] = []
    for sku, product in sorted(cat.items()):
        url = product_page(sku)
        # test1 — служебный товар за 1 ₽: в каталоге не показывается,
        # покупается только со скрытой /test-pokupka.html и выдаёт
        # бесплатный лид-магнит. Своей страницы у него нет по устройству,
        # и требовать её значило бы ловить несуществующий дефект.
        if url is None and sku != "test1":
            problems.append(f"{sku}: в кассе есть, страницы товара нет")
        info = meta.get(sku, {})
        cross = [c for c in info.get("cross", []) if c != sku]
        for c in cross:
            if c not in cat:
                problems.append(f"{sku}: допродажа {c} — такого товара в кассе нет")
            elif product_page(c) is None:
                problems.append(f"{sku}: у допродажи {c} нет страницы")
        free = info.get("free") or ""
        if free and not (ROOT / free).exists():
            problems.append(f"{sku}: бесплатный вход {free} не существует")
        rows.append({
            "product_id": sku,
            "product_url": url or "",
            "money_pain": ";".join(info.get("pains", [])) or "не назначена",
            "stage": info.get("stage", "не назначена"),
            "price": product["price"],
            "primary_landing": url or "",
            "free_entry": "/" + free if free else "",
            "cross_sell": ";".join(cross),
            "upsell": "",
            "bundle": "",
            "status": "test" if sku == "test1" else "active",
        })

    seen = [r["product_id"] for r in rows]
    for sku in {s for s in seen if seen.count(s) > 1}:
        problems.append(f"{sku}: повторяется в карте")
    orphans = [r["product_id"] for r in rows
               if r["money_pain"] == "не назначена" and r["status"] != "test"]
    for sku in orphans:
        problems.append(f"{sku}: не привязан ни к одной денежной боли — "
                        f"продаётся только допродажей или не продаётся вовсе")
    return rows, problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rows, problems = build()
    cat = catalog()

    print(f"Товаров в кассе: {len(cat)}; строк в карте: {len(rows)}")
    covered = sum(1 for r in rows if r["money_pain"] != "не назначена")
    with_cross = sum(1 for r in rows if r["cross_sell"])
    print(f"С назначенной болью: {covered}/{len(rows)}; "
          f"с допродажей: {with_cross}/{len(rows)}")

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"записано: {OUT.relative_to(ROOT)}")

    if problems:
        print(f"\nРАСХОЖДЕНИЙ: {len(problems)}")
        for line in problems:
            print(f"   ✗ {line}")
        # Мёртвая ссылка в карте — дефект. Товар без боли — замечание:
        # состав каталога решает владелец (Р-006).
        blocking = [p for p in problems if "не привязан" not in p]
        return 1 if blocking else 0
    print("Дефектов нет: страницы существуют, повторов нет, цены из кассы.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
