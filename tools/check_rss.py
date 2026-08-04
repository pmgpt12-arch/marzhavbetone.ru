#!/usr/bin/env python3
"""Проверяет, что фид для Дзена несёт то же, что статья на сайте.

Дзен внутри `content:encoded` принимает только `p`, `h2`, `h3`, списки,
`strong`, `em`, ссылки и цитаты. Таблицу он не примет — но опасность не в
этом, а в том, как она пропадала: разбор статьи идёт по перечню тегов, и
таблица в него просто не входила. Текст смыкался, фид получался валидным, и
ничего нигде не падало. На восемнадцати статьях из двадцати девяти так
терялось от трёх до двадцати одного процента текста, а в разборах
формулировок — вся суть: колонка «что делает с деньгами» и есть материал.

Проверка сравнивает содержимое таблиц статьи с текстом фида. Берётся
достаточно длинная ячейка: короткая («да», «нет», число) могла бы совпасть
случайно.

    python3 tools/check_rss.py

Код возврата 1, если содержимое статьи не доехало до фида.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
FEED = ROOT / "rss.xml"

# Ячейка короче этого могла бы совпасть с текстом статьи случайно
MIN_PROBE = 25


def cells(table: str) -> list[str]:
    return [re.sub(r"<[^>]+>", "", cell).strip()
            for cell in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", table, re.S)]


def main() -> int:
    if not FEED.is_file():
        # Фид собирается при деплое и в репозитории не лежит
        print("rss.xml не найден — собираю", file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_rss.py")],
                       cwd=ROOT, check=True, capture_output=True)

    feed = FEED.read_text(encoding="utf-8")
    articles = [p for p in sorted(ARTICLES.glob("*.html")) if p.name != "index.html"]

    problems: list[str] = []
    checked = 0
    for path in articles:
        source = path.read_text(encoding="utf-8")
        for table in re.findall(r"<table.*?</table>", source, re.S):
            probe = next((c for c in cells(table) if len(c) > MIN_PROBE), None)
            if probe is None:
                continue
            checked += 1
            if probe not in feed:
                problems.append(f"{path.name}: содержимое таблицы не в фиде — "
                                f"«{probe[:70]}»")

    # Дзен требует, чтобы в фиде было не меньше десяти материалов
    items = feed.count("<item>")

    for line in problems:
        print(f"РАСХОЖДЕНИЕ  {line}")
    print(f"\nСтатей: {len(articles)}, таблиц проверено: {checked}, "
          f"материалов в фиде: {items}, расхождений: {len(problems)}")
    if items < 10:
        print("В фиде меньше десяти материалов — Дзен трансляцию не включит.")
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
