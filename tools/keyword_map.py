#!/usr/bin/env python3
"""Строит карту запрос → страница из замеренной семантики.

Соблазн — сделать по странице на запрос. Инструмент показывает, во что
запросы сворачиваются на самом деле: по (кластер, подкластер, интент)
внутри группы они отличаются словами, а не намерением. «Генподрядчик не
платит» и «генподрядчик задерживает оплату» — одна страница, а не две.
Замер 14.08.2026: 297 запросов дают 37 групп и 31 страницу.

Строки со статусом «Заготовка» пропускаются. Это шаблонные записи вида
«основа — хвост» («… — типовые ошибки», «… — образец документа»), которых
в семантике 300; поисковыми запросами они не являются, замера у них нет ни
у одной, а в счёте кластера раздували его втрое.

Инструмент делает только механическую часть, и делает её воспроизводимо:

  * группирует запросы по намерению;
  * назначает в каждой группе носителя — запрос с наибольшей частотностью;
  * ищет уже опубликованную страницу по slug целевого URL;
  * ставит предварительное решение из пяти: keep, improve, merge, create,
    no-page.

Чего он не делает: не решает, отвечает ли найденная страница именно этому
запросу, и не заводит страниц. Первое — суждение (`marzha-seo-strategist`),
второе — решение владельца (Р-006 в ai-business-os).

    python3 tools/keyword_map.py                  # сводка
    python3 tools/keyword_map.py --out карта.csv  # карта построчно

Код возврата 0 всегда: инструмент строит, а не проверяет.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMANTIC = ROOT / "content" / "strategy" / "semantic-core.csv"

PAGE_GLOBS = (
    "articles/*.html",
    "products/*.html",
    "materialy/*.html",
    "demo/*.html",
)

COLUMNS = [
    "Кластер",
    "Подкластер",
    "Интент",
    "Запрос",
    "Частотность",
    "Широкая частотность",
    "Существующая страница",
    "Решение",
    "Целевая страница",
    "Чем показано",
    "Примечание",
]


def slug_of(url: str) -> str:
    tail = url.strip("/").split("/")[-1]
    return tail[: -len(".html")] if tail.endswith(".html") else tail


def published_by_slug() -> dict[str, str]:
    pages: dict[str, str] = {}
    for pattern in PAGE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            if rel.endswith("/index.html"):
                continue
            pages[slug_of(rel)] = "/" + rel
    return pages


def frequency(row: dict[str, str]) -> int:
    raw = (row.get("Частотность") or "").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


def build() -> tuple[list[dict[str, str]], dict[str, int]]:
    with SEMANTIC.open(encoding="utf-8") as fh:
        all_rows = list(csv.DictReader(fh))

    # Заготовки — строки вида «основа — хвост», не поисковые запросы. В карту
    # они не идут и в счёт кластера тоже: иначе кластер из тридцати заготовок
    # выглядит крупнее кластера из десяти замеренных фраз.
    rows = [r for r in all_rows if r.get("Статус", "").strip() != "Заготовка"]
    skipped = len(all_rows) - len(rows)

    pages = published_by_slug()

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("Кластер", "").strip(),
            row.get("Подкластер", "").strip(),
            row.get("Интент", "").strip(),
        )
        groups[key].append(row)

    out: list[dict[str, str]] = []
    counts: dict[str, int] = defaultdict(int)

    for key, members in sorted(groups.items()):
        cluster, subcluster, intent = key
        members.sort(key=frequency, reverse=True)

        # Носитель группы — самый частотный запрос. Он и получает страницу;
        # остальные её же и обслуживают.
        carrier = members[0]

        # Есть ли уже страница под кого-то из группы. Берём первую найденную
        # по slug целевого URL: план и факт расходятся каталогом, но не
        # именем страницы.
        existing = ""
        matched_query = ""
        for member in members:
            found = pages.get(slug_of(member.get("Целевой URL", "")))
            if found:
                existing, matched_query = found, member.get("Запрос", "")
                break

        for member in members:
            is_carrier = member is carrier
            query = member.get("Запрос", "").strip()
            own = pages.get(slug_of(member.get("Целевой URL", "")), "")

            if existing and is_carrier:
                decision = "keep" if own else "improve"
                target = existing
                note = (
                    ""
                    if own
                    else f"страница есть под «{matched_query}» — проверить, "
                    "отвечает ли она этому запросу"
                )
            elif existing and own:
                # Страница под этот запрос уже есть, и под носителя группы
                # тоже. Две страницы на один интент — каннибализация, и
                # решается она слиянием, а не «не делать»: `no-page` здесь
                # читался бы как «удалить опубликованное».
                decision = "merge"
                target = existing
                note = (
                    f"своя страница есть, но интент общий с "
                    f"«{carrier.get('Запрос','')}» — решить, какая сильнее"
                )
            elif existing:
                decision = "no-page"
                target = existing
                note = f"тот же интент, что «{carrier.get('Запрос','')}»"
            elif is_carrier:
                decision = "create"
                target = member.get("Целевой URL", "").strip()
                note = (
                    "единственный запрос группы — страница будет тонкой, "
                    "рассмотреть merge в соседнюю"
                    if len(members) == 1
                    else ""
                )
            else:
                decision = "no-page"
                target = carrier.get("Целевой URL", "").strip()
                note = f"тот же интент, что «{carrier.get('Запрос','')}»"

            counts[decision] += 1
            out.append(
                {
                    "Кластер": cluster,
                    "Подкластер": subcluster,
                    "Интент": intent,
                    "Запрос": query,
                    "Частотность": member.get("Частотность", "").strip(),
                    "Широкая частотность":
                        member.get("Широкая частотность", "").strip(),
                    "Существующая страница": own or existing,
                    "Решение": decision,
                    "Целевая страница": target,
                    "Чем показано": "semantic-core.csv + файлы репозитория",
                    "Примечание": note,
                }
            )

    counts["групп"] = len(groups)
    counts["запросов"] = len(rows)
    counts["заготовок"] = skipped
    return out, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="куда записать карту")
    args = parser.parse_args()

    rows, counts = build()

    # Файл пишется до вывода: сводку часто смотрят через `| head`, и тогда
    # печать обрывается BrokenPipe — карта не должна от этого пропадать.
    if args.out:
        with args.out.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    pages_needed = counts.get("create", 0) + counts.get("improve", 0)
    print(
        f"Запросов: {counts['запросов']}, групп по намерению: {counts['групп']}"
        + (f"; заготовок пропущено: {counts['заготовок']}"
           if counts.get("заготовок") else "")
    )
    print()
    for decision in ("keep", "improve", "merge", "create", "no-page"):
        if counts.get(decision):
            print(f"  {decision:9} {counts[decision]:4}")
    print()
    print(
        f"Страниц под запросы получается {pages_needed}, а не "
        f"{counts['запросов']}: {counts.get('no-page', 0)} запросов "
        "обслуживаются уже назначенными страницами."
    )

    # Пустая частотность — «не замерено», а не «нет спроса», и путать их
    # нельзя: сумма по кластеру без этого числа читается как сигнал.
    print("\nЗамеренность спроса по кластерам:")
    measured: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        stat = measured[row["Кластер"]]
        stat[0] += 1
        # Точная и широкая частота считаются вместе как «замерено», но в один
        # столбец не сводятся: облачный режим API кавычек не поддерживает.
        value = (row["Частотность"].strip()
                 or row.get("Широкая частотность", "").strip())
        if value.isdigit() and int(value) > 0:
            stat[1] += 1
    for cluster, (total, with_value) in sorted(
        measured.items(), key=lambda item: item[1][1] / max(item[1][0], 1)
    ):
        share = with_value / total if total else 0
        mark = "  ← спрос почти не замерен" if share < 0.2 else ""
        print(
            f"  {cluster:32} {with_value:3} из {total:3} "
            f"({share:.0%}){mark}"
        )

    if args.out:
        print(f"\nКарта записана: {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
