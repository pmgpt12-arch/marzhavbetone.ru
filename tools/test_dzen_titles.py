#!/usr/bin/env python3
"""Размеченные случаи: какой заголовок уходит в фид Дзена.

Проверка доказана откатом — снятие USE_DZEN_TITLES роняет первый случай,
подмена блока «Ссылка» роняет второй, вторая заготовка на ту же статью
роняет третий.

    python3 tools/test_dzen_titles.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_rss

ROOT = Path(__file__).resolve().parent.parent

# Случаи размечены по заготовкам content/dzen: слева адрес статьи из блока
# «Ссылка», справа строка из блока «Заголовок» дословно. Набор небольшой
# намеренно — он проверяет разбор заготовки, а не пересчитывает их все.
CASES = [
    ("garantiynoe-uderzhanie-chto-eto",
     "Пять процентов, которые вы больше не увидите"),
    ("akt-osvidetelstvovaniya-skrytyh-rabot",
     "Скрытые работы закрыли. Акт подписать забыли"),
    ("stroitelnyy-musor-v-smete",
     "Мусор вывозите вы. В смете его нет"),
]


def main() -> int:
    problems: list[str] = []

    titles = build_rss.dzen_titles()

    if not titles:
        problems.append(
            "заготовки не разобраны вовсе: dzen_titles() пуст — фид уедет "
            "с поисковыми заголовками, и никто этого не заметит"
        )

    for slug, expected in CASES:
        actual = titles.get(slug)
        if actual != expected:
            problems.append(
                f"{slug}: ожидался заголовок заготовки «{expected}», "
                f"получен «{actual}»"
            )

    # Заголовок заготовки обязан доехать до самого фида, а не только до
    # словаря: между ними стоит ветка выпуска, и она однажды уже съедала
    # содержимое молча.
    feed_titles = {item["title"] for item in build_rss.collect()}
    for slug, expected in CASES:
        article = ROOT / "articles" / f"{slug}.html"
        if not article.is_file():
            problems.append(f"{slug}: статьи нет, случай проверить нечем")
            continue
        if slug in build_rss.PUBLISHED_BY_HAND:
            continue
        if expected not in feed_titles:
            problems.append(
                f"{slug}: заголовок «{expected}» до фида не доехал"
            )

    # Каждая заготовка обязана указывать на существующую статью: заготовка,
    # потерявшая адрес при переименовании, молча перестаёт влиять на фид.
    for slug in titles:
        if not (ROOT / "articles" / f"{slug}.html").is_file():
            problems.append(
                f"заготовка ссылается на {slug}.html, которой нет в articles/"
            )

    if problems:
        for line in problems:
            print(f"ДЕФЕКТ: {line}")
        return 1

    print(
        f"Заголовков из заготовок: {len(titles)}, "
        f"размеченных случаев сошлось: {len(CASES)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
