#!/usr/bin/env python3
"""Считает, какие механики роликов работают на нашей аудитории.

Данные лежат в content/reels/results.csv — по строке на опубликованный
ролик. Пока нет Insights API, цифры вносятся руками из статистики
публикации; формат от этого не зависит, и при подключении API заполнение
станет автоматическим без переделки отчёта.

Главное свойство отчёта — он отказывается делать выводы на малой выборке.
Разница между двумя механиками по трём роликам — это шум, и назвать её
результатом означает начать оптимизировать случайность.

    python3 tools/reels_report.py
    python3 tools/reels_report.py --min-group 5
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "content" / "reels" / "results.csv"

# Сколько роликов в группе нужно, чтобы вообще сравнивать группы между собой
MIN_GROUP = 5
# Во сколько раз должны отличаться средние, чтобы разницу стоило обсуждать
MEANINGFUL_RATIO = 1.5

NUMERIC = ["duration", "views", "saves", "shares", "profile_visits",
           "link_clicks", "followers"]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    clean: list[dict] = []
    for index, row in enumerate(rows, start=2):
        if not (row.get("file") or "").strip():
            continue
        for field in NUMERIC:
            value = (row.get(field) or "").strip()
            if value == "":
                row[field] = None
                continue
            try:
                row[field] = float(value.replace(",", "."))
            except ValueError:
                raise ValueError(
                    f"строка {index}: в поле {field} не число — {value!r}"
                ) from None
        clean.append(row)
    return clean


def rate(row: dict, field: str) -> float | None:
    """Доля от просмотров: абсолютные числа зависят от раздачи алгоритма."""
    views, value = row.get("views"), row.get(field)
    if not views or value is None:
        return None
    return value / views


def describe(values: list[float]) -> str:
    if len(values) == 1:
        return f"{values[0]:.2%}"
    return (f"{statistics.mean(values):.2%} "
            f"(от {min(values):.2%} до {max(values):.2%})")


def group_by(rows: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        value = row.get(key)
        # Числовые поля уже приведены к float, строковые остались строками
        if isinstance(value, float):
            name = f"{value:g} с"
        else:
            name = (value or "").strip() or "не указано"
        groups.setdefault(name, []).append(row)
    return groups


def report_metric(groups: dict[str, list[dict]], field: str, title: str,
                  min_group: int) -> None:
    print(f"\n{title}")
    measured: dict[str, list[float]] = {}
    for name, rows in sorted(groups.items()):
        values = [r for r in (rate(row, field) for row in rows) if r is not None]
        if not values:
            print(f"  {name}: нет данных ({len(rows)} роликов)")
            continue
        measured[name] = values
        mark = "" if len(values) >= min_group else "  ← выборка мала"
        print(f"  {name}: {describe(values)} по {len(values)} роликам{mark}")

    comparable = {n: v for n, v in measured.items() if len(v) >= min_group}
    if len(comparable) < 2:
        print(f"  Сравнивать нечего: нужно минимум по {min_group} роликов "
              f"хотя бы в двух группах.")
        return

    ranked = sorted(comparable.items(), key=lambda item: statistics.mean(item[1]),
                    reverse=True)
    best, worst = ranked[0], ranked[-1]
    best_mean, worst_mean = statistics.mean(best[1]), statistics.mean(worst[1])
    if worst_mean and best_mean / worst_mean >= MEANINGFUL_RATIO:
        print(f"  Вывод: «{best[0]}» опережает «{worst[0]}» "
              f"в {best_mean / worst_mean:.1f} раза.")
    else:
        print("  Вывод: разница между группами меньше полутора раз — "
              "на таких числах это неотличимо от случайности.")


def warn_confounded(groups: dict[str, list[dict]], other_key: str,
                    axis: str, other_axis: str) -> None:
    """Предупреждает, когда две оси менялись одновременно.

    Если каждой длительности соответствует ровно одна механика, разницу
    нельзя приписать длительности: она с тем же успехом объясняется
    механикой. Правило «одна ось в неделю» существует ровно для этого,
    и нарушение видно только по данным.
    """
    if len(groups) < 2:
        return
    mapping = {
        name: {(row.get(other_key) or "").strip() for row in rows}
        for name, rows in groups.items()
    }
    if not all(len(values) == 1 for values in mapping.values()):
        return
    singles = {next(iter(values)) for values in mapping.values()}
    # Если во всех группах одна и та же механика, вторая ось не менялась —
    # и путаницы осей нет, сравнение по длительности корректно
    if len(singles) < 2:
        return

    pairs = ", ".join(f"{name} → {next(iter(values))}"
                      for name, values in sorted(mapping.items()))
    print(f"  ВНИМАНИЕ: каждой группе по оси «{axis}» соответствует своя "
          f"{other_axis} ({pairs}). Разницу нельзя приписать {axis}: "
          f"менялись обе оси сразу.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Отчёт по роликам")
    parser.add_argument("--min-group", type=int, default=MIN_GROUP,
                        help=f"минимум роликов в группе для сравнения (по умолчанию {MIN_GROUP})")
    args = parser.parse_args()

    if not RESULTS.is_file():
        print(f"ОШИБКА: нет файла {RESULTS.relative_to(ROOT)}", file=sys.stderr)
        return 1

    try:
        rows = load(RESULTS)
    except ValueError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print("Опубликованных роликов пока нет — заполните content/reels/results.csv "
              "после первой публикации.")
        return 0

    print(f"Роликов в выборке: {len(rows)}")
    with_views = [row for row in rows if row.get("views")]
    if with_views:
        views = [row["views"] for row in with_views]
        print(f"Просмотры: медиана {statistics.median(views):.0f}, "
              f"от {min(views):.0f} до {max(views):.0f}")
        clicks = [row["link_clicks"] for row in rows if row.get("link_clicks") is not None]
        if clicks:
            print(f"Переходов по ссылке всего: {sum(clicks):.0f}")

    by_mechanic = group_by(rows, "mechanic")
    report_metric(by_mechanic, "saves", "Сохранения по механикам", args.min_group)
    report_metric(by_mechanic, "link_clicks", "Переходы по ссылке по механикам",
                  args.min_group)

    by_duration = group_by(rows, "duration")
    report_metric(by_duration, "saves", "Сохранения по длительности", args.min_group)
    warn_confounded(by_duration, "mechanic", "длительность", "механика")

    print("\nПросмотры показывают раздачу алгоритма, а не попадание в нашего "
          "зрителя, поэтому сравниваются доли, а не абсолютные числа. Пока в "
          f"группе меньше {args.min_group} роликов, выводы не делаются.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
