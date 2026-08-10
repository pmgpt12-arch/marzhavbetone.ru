#!/usr/bin/env python3
"""Сверяет каталог на продаже с продуктовой линейкой из плана.

Цена живёт в двух местах: в `products-config.php`, откуда её берёт касса, и
в `content/strategy/products.csv`, где записано решение по линейке. Разойтись
они могут молча — цену правят в одном файле, а в другом остаётся старая, и
дальше по ней считают выручку.

    python3 tools/check_products.py

Код возврата 1, если расхождение есть.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "products-config.php"
PLAN = ROOT / "content" / "strategy" / "products.csv"

# Цены в конфиге в копейках: касса принимает сумму в минимальных единицах
KOPECKS = 100
# Тестовая покупка за рубль в линейке не значится и значиться не должна
IGNORED_SKU = {"test1"}

ENTRY = re.compile(
    r"'(?P<sku>[a-z0-9]+)'\s*=>\s*\[\s*"
    r"'name'\s*=>\s*'(?P<name>(?:[^'\\]|\\.)*)'\s*,\s*"
    r"'price'\s*=>\s*(?P<price>\d+)",
    re.S,
)

# Памятка по серверу: по ней сверяют выдачу руками, и до 10.08.2026 она
# описывала снятую линейку. Сверяются цена, папка и имя архива.
SERVER_MANIFEST = ROOT / "products-storage" / "SERVER-MANIFEST.txt"
DELIVERY = re.compile(
    r"'(?P<sku>[a-z0-9]+)'\s*=>\s*\[\s*"
    r"'name'\s*=>\s*'(?:[^'\\]|\\.)*'\s*,\s*"
    r"'price'\s*=>\s*(?P<price>\d+)\s*,\s*"
    r"'dir'\s*=>\s*'(?P<dir>[^']+)'\s*,\s*"
    r"'zip'\s*=>\s*'(?P<zip>[^']+)'",
    re.S,
)
# Строка таблицы памятки: sku, цена, папка, архив
MANIFEST_ROW = re.compile(
    r"^\s{2,}(?P<sku>[a-z]+[0-9]+)\s+(?P<price>\d+)\s+"
    r"(?P<dir>[\w-]+)\s+(?P<zip>[\w.-]+\.zip)\s*$",
    re.M,
)


def live_catalog() -> dict[str, tuple[str, int]]:
    text = CONFIG.read_text(encoding="utf-8")
    found = {}
    for match in ENTRY.finditer(text):
        sku = match.group("sku")
        if sku in IGNORED_SKU:
            continue
        name = match.group("name").replace("\\'", "'")
        found[sku] = (name, int(match.group("price")) // KOPECKS)
    return found


def server_manifest_problems() -> list[str]:
    """Сверяет памятку по серверу с каталогом кассы.

    `products-storage/SERVER-MANIFEST.txt` — то, по чему сверяют выдачу на
    сервере руками. Пока его никто не проверял, он девять дней описывал
    снятую линейку: триггер-продукты t1–t3, которых нет, и цены
    12 900–69 900 ₽ из removed_levels. Сверяются два поля, которые в нём
    записаны машиночитаемо, — имя архива и цена; описания и порядок разделов
    пишет человек.
    """
    if not SERVER_MANIFEST.is_file():
        return ["products-storage/SERVER-MANIFEST.txt: файла нет"]

    live = {
        m.group("sku"): (int(m.group("price")) // KOPECKS,
                         m.group("dir"), m.group("zip"))
        for m in DELIVERY.finditer(CONFIG.read_text(encoding="utf-8"))
    }
    listed = {
        row.group("sku"): (int(row.group("price")),
                           row.group("dir"), row.group("zip"))
        for row in MANIFEST_ROW.finditer(
            SERVER_MANIFEST.read_text(encoding="utf-8"))
    }

    problems: list[str] = []
    for sku in sorted(set(listed) - set(live)):
        problems.append(
            f"SERVER-MANIFEST.txt: {sku} описан, но в каталоге кассы его нет"
        )
    for sku in sorted(set(live) - set(listed)):
        problems.append(f"SERVER-MANIFEST.txt: {sku} продаётся, но не описан")
    for sku in sorted(set(live) & set(listed)):
        for field, here, there in zip(("цена", "папка", "архив"),
                                      listed[sku], live[sku]):
            if here != there:
                problems.append(
                    f"SERVER-MANIFEST.txt ({sku}): {field} — «{here}», "
                    f"в каталоге «{there}»"
                )
    return problems


def main() -> int:
    if not CONFIG.is_file() or not PLAN.is_file():
        print("Не найден products-config.php или products.csv", file=sys.stderr)
        return 1

    live = live_catalog()
    problems: list[str] = []
    planned_skus: set[str] = set()

    with PLAN.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sku = row["SKU в products-config.php"].strip()
            status = row["Статус"].strip()
            code = row["Код"]

            if status == "Продаётся" and not sku:
                problems.append(f"{code}: в плане «Продаётся», но SKU не указан")
                continue
            if not sku:
                continue

            planned_skus.add(sku)
            if sku not in live:
                problems.append(f"{code}: SKU {sku} в плане есть, в каталоге нет")
                continue

            name, price = live[sku]
            if price != int(row["Цена"]):
                problems.append(
                    f"{code} ({sku}): в плане {int(row['Цена'])} ₽, "
                    f"в каталоге {price} ₽"
                )
            if name != row["Продукт"]:
                problems.append(
                    f"{code} ({sku}): название разошлось\n"
                    f"      план:    {row['Продукт']}\n"
                    f"      каталог: {name}"
                )

    for sku in sorted(set(live) - planned_skus):
        problems.append(f"{sku}: продаётся, но в продуктовой линейке не описан")

    problems += server_manifest_problems()

    if problems:
        print("Каталог и план разошлись:\n")
        for problem in problems:
            print(f"  {problem}")
    else:
        print(f"Каталог совпадает с планом: {len(live)} продуктов на продаже.")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
