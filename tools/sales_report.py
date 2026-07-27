#!/usr/bin/env python3
"""Сводка продаж по источникам из файлов заказов.

Отвечает на вопрос, ради которого расставлялись UTM-метки: какая площадка и
какая тема приносят деньги. Без этого оптимизировать воронку приходится
наугад.

Запуск:
    python3 tools/sales_report.py <папка-с-заказами> [--days 30]

Отчёт агрегированный: email и телефоны покупателей в него не попадают, чтобы
персональные данные не расходились по логам и артефактам.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

MSK = timezone(timedelta(hours=3))
# Цель владельца — 300 000 ₽ в месяц. Суммы в заказах хранятся в копейках,
# поэтому и цель держим в копейках: иначе сравнение даёт результат в сто раз
# больше настоящего.
GOAL_PER_MONTH_KOPECKS = 300_000 * 100


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.0f} ₽".replace(",", " ")


def load_orders(directory: Path, days: int | None) -> tuple[list[dict], list[str]]:
    orders, broken = [], []
    cutoff = datetime.now(MSK) - timedelta(days=days) if days else None

    for path in sorted(directory.glob("order_*.json")):
        try:
            order = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            broken.append(f"{path.name}: {exc}")
            continue
        created = order.get("paid_at") or order.get("created_at")
        if created:
            try:
                order["_dt"] = datetime.fromisoformat(created)
            except ValueError:
                order["_dt"] = None
        else:
            order["_dt"] = None
        if cutoff and order["_dt"] and order["_dt"] < cutoff:
            continue
        orders.append(order)
    return orders, broken


def touch_label(order: dict, which: str) -> str:
    touch = (order.get("attribution") or {}).get(which) or {}
    source = touch.get("source")
    if not source:
        return "неизвестно"
    medium = touch.get("medium")
    return f"{source} / {medium}" if medium else source


def section(title: str) -> None:
    print(f"\n{title}")
    print("─" * len(title))


def table(rows: list[tuple[str, int, int]], head: str) -> None:
    """rows: (название, число оплат, сумма в копейках)"""
    if not rows:
        print("  нет данных")
        return
    width = max(len(head), max(len(name) for name, _, _ in rows))
    total = sum(amount for _, _, amount in rows)
    print(f"  {head.ljust(width)}  оплат   выручка      доля")
    for name, count, amount in sorted(rows, key=lambda r: -r[2]):
        share = f"{amount / total * 100:.0f}%" if total else "—"
        print(f"  {name.ljust(width)}  {count:>5}  {money(amount):>10}  {share:>6}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Сводка продаж по источникам")
    parser.add_argument("orders_dir", help="папка с файлами order_*.json")
    parser.add_argument("--days", type=int, default=None,
                        help="учитывать заказы за последние N дней")
    args = parser.parse_args()

    directory = Path(args.orders_dir)
    if not directory.is_dir():
        print(f"Папки нет: {directory}")
        return 1

    orders, broken = load_orders(directory, args.days)
    paid = [o for o in orders if o.get("status") == "paid"]
    pending = [o for o in orders if o.get("status") == "pending"]
    revenue = sum(int(o.get("total") or 0) for o in paid)

    period = f"за последние {args.days} дней" if args.days else "за всё время"
    print(f"Сводка продаж {period}")
    print(f"Сформирована {datetime.now(MSK):%d.%m.%Y %H:%M} МСК")

    section("Итого")
    print(f"  Оплачено заказов:      {len(paid)}")
    print(f"  Выручка:               {money(revenue)}")
    if paid:
        print(f"  Средний чек:           {money(revenue // len(paid))}")
    print(f"  Не доведено до оплаты: {len(pending)}")
    if paid and (len(paid) + len(pending)):
        conversion = len(paid) / (len(paid) + len(pending)) * 100
        print(f"  Доведено до оплаты:    {conversion:.0f}% от начатых")

    if args.days:
        monthly = revenue / args.days * 30
        share = monthly / GOAL_PER_MONTH_KOPECKS * 100
        print(f"  В пересчёте на месяц:  {money(int(monthly))} "
              f"({share:.0f}% от цели {money(GOAL_PER_MONTH_KOPECKS)})")

    if not paid:
        print("\nОплаченных заказов пока нет — разбивка по источникам появится "
              "после первых продаж.")
        if broken:
            section("Файлы, которые не удалось прочитать")
            for line in broken:
                print(f"  {line}")
        return 0

    for which, title in (("first", "Кто привёл покупателя (первое касание)"),
                         ("last", "Что подтолкнуло купить (последнее касание)")):
        by_source: dict[str, list[int]] = defaultdict(list)
        for order in paid:
            by_source[touch_label(order, which)].append(int(order.get("total") or 0))
        section(title)
        table([(name, len(amounts), sum(amounts))
               for name, amounts in by_source.items()], "источник")

    by_campaign: dict[str, list[int]] = defaultdict(list)
    for order in paid:
        touch = (order.get("attribution") or {}).get("first") or {}
        campaign = touch.get("campaign") or "без метки кампании"
        by_campaign[campaign].append(int(order.get("total") or 0))
    section("Какая тема приносит деньги (кампания первого касания)")
    table([(name, len(amounts), sum(amounts))
           for name, amounts in by_campaign.items()], "кампания")

    by_product: dict[str, list[int]] = defaultdict(list)
    for order in paid:
        for item in order.get("items") or []:
            name = item.get("name") or item.get("sku") or "без названия"
            by_product[name[:60]].append(int(item.get("price") or 0))
    section("Что покупают")
    table([(name, len(prices), sum(prices))
           for name, prices in by_product.items()], "комплект")

    no_attribution = [o for o in paid if not (o.get("attribution") or {}).get("first")]
    if no_attribution:
        section("Обратить внимание")
        print(f"  У {len(no_attribution)} из {len(paid)} оплаченных заказов нет "
              f"источника.")
        print("  Так бывает у заказов, созданных до подключения учёта, при "
              "заходе в приватном режиме")
        print("  или при прямом заходе на сайт без метки и без перехода.")

    if broken:
        section("Файлы, которые не удалось прочитать")
        for line in broken:
            print(f"  {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
