#!/usr/bin/env python3
"""Карта запросов не ссылается на страницу, которой нет.

Зачем. `content/strategy/keyword-map.csv` — канонический источник по теме
«поисковый спрос» (`docs/KNOWLEDGE_INDEX.md`). Замер 16.08.2026: 227 её
строк указывали в `/baza-znanii/` и `/proverki/` — разделы, которых на
сайте нет вовсе. Колонка называется «Целевая страница», и адрес в ней
читается как «страница есть, вот она». Означало это ровно обратное.

Ошибка была не в данных, а в том, что негде было сказать «страницы нет»:
карта подставляла в эту колонку план из семантики. Теперь там стоит
`LANDING GAP`, и проверка держит инвариант: **каждая цель — либо
опубликованная страница, либо явный признак разрыва.** Третьего значения
нет, и выдуманный адрес больше не пройдёт молча.

Проверяется два инварианта, и второй не менее важен первого:

  · цель существует либо объявлена разрывом — иначе карта врёт про
    страницу;
  · карта совпадает с тем, что строит `keyword_map.py` из семантики —
    иначе её можно поправить рукой, и она разойдётся с источником так же
    тихо, как разошлась в прошлый раз.

`check_seo.py` этого не ловит и ловить не должен: он смотрит семантику и
сайт, а `/baza-znanii/` в семантике — это план владельца, а не дефект.
Дефект появляется в тот момент, когда план переезжает в карту под именем
факта.

    python3 tools/check_keyword_map.py
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "content" / "strategy" / "keyword-map.csv"

sys.path.insert(0, str(ROOT / "tools"))
import keyword_map  # noqa: E402


def published() -> set[str]:
    pages: set[str] = set()
    for pattern in keyword_map.PAGE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            if rel.endswith("/index.html"):
                continue
            pages.add("/" + rel)
    return pages


def rebuilt() -> str:
    rows, _ = keyword_map.build()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keyword_map.COLUMNS,
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def main() -> int:
    if not MAP.exists():
        print(f"нет файла {MAP.relative_to(ROOT)}; построить: "
              f"python3 tools/keyword_map.py --out {MAP.relative_to(ROOT)}")
        return 1

    defects: list[str] = []
    pages = published()

    with MAP.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    gaps = 0
    live = 0
    for number, row in enumerate(rows, start=2):
        target = (row.get("Целевая страница") or "").strip()
        query = (row.get("Запрос") or "").strip()
        if target == keyword_map.GAP:
            gaps += 1
            continue
        if not target:
            defects.append(
                f"строка {number}: пустая цель у «{query}» — "
                f"страницы нет, но и разрыв не объявлен; "
                f"должно стоять {keyword_map.GAP}"
            )
            continue
        if target not in pages:
            defects.append(
                f"строка {number}: «{query}» метит в {target}, "
                f"страницы нет; если её и не будет — {keyword_map.GAP}"
            )
            continue
        live += 1

    # Второй инвариант: карта построена из семантики, а не поправлена рукой.
    if MAP.read_text(encoding="utf-8") != rebuilt():
        defects.append(
            "карта разошлась с семантикой: пересборка даёт другой файл. "
            "Починка: python3 tools/keyword_map.py --out "
            f"{MAP.relative_to(ROOT)}"
        )

    for defect in defects:
        print(f"ДЕФЕКТ   {defect}")

    print(f"\nСтрок карты: {len(rows)}, целей на опубликованные страницы: "
          f"{live}, объявленных разрывов: {gaps}, дефектов: {len(defects)}")
    if defects:
        return 1
    print("Дефектов нет: каждая цель карты — либо опубликованная страница, "
          "либо объявленный разрыв.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
