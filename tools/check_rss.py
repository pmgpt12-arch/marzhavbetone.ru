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

import html
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

    # Статьи, опубликованные в Дзене вручную, из фида исключены намеренно:
    # спрашивать с них содержимое значило бы жечь проверку на своём же
    # решении. Список берётся из сборщика, а не повторяется здесь — две
    # копии разошлись бы молча.
    sys.path.insert(0, str(ROOT / "tools"))
    from build_rss import PUBLISHED_BY_HAND

    feed = FEED.read_text(encoding="utf-8")
    # Сравнивать надо нормализованный текст: в фиде разметка, сущности и
    # переносы строк расставлены иначе, чем в статье, и точное совпадение
    # сырых кусков не срабатывает — первая версия проверки на этом и
    # промолчала.
    flat = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", feed)).split())
    articles = [p for p in sorted(ARTICLES.glob("*.html"))
                if p.name != "index.html" and p.stem not in PUBLISHED_BY_HAND]

    problems: list[str] = []
    checked = 0
    leaked = 0
    for path in articles:
        source = path.read_text(encoding="utf-8")

        # Рекламные блоки в фид не идут. Проверяется по содержимому, а не
        # по слову «₽»: цена может законно стоять в тексте разбора, а вот
        # фраза из карточки комплекта — нет. Замер 04.08.2026 показал цену
        # в шестнадцати материалах из восемнадцати: карточка уезжала у всех
        # статей, где нет блока кнопок, а он есть не у всех.
        for promo in re.findall(
                r'<div class="(?:article-cta|article-lead)".*?</div>',
                source, re.S):
            # Подпись-рубрику («ПЛАТНЫЙ КОМПЛЕКТ») сборщик выбрасывает и
            # без правки — она в <p class="eyebrow">. Пробу надо брать из
            # того, что в фид попало бы: иначе проверка сравнивает текст,
            # которого там не бывает никогда, и молчит.
            promo = re.sub(r'<p class="eyebrow".*?</p>', "", promo, flags=re.S)
            text = re.sub(r"<[^>]+>", " ", promo)
            probe = next((s.strip() for s in re.split(r"[.!?]", text)
                          if len(s.strip()) > 40), None)
            probe = " ".join(html.unescape(probe).split()) if probe else None
            if probe and probe in flat:
                leaked += 1
                problems.append(f"{path.name}: реклама в фиде — "
                                f"«{probe[:60]}»")

        for table in re.findall(r"<table.*?</table>", source, re.S):
            probe = next((c for c in cells(table) if len(c) > MIN_PROBE), None)
            if probe is None:
                continue
            checked += 1
            if " ".join(html.unescape(probe).split()) not in flat:
                problems.append(f"{path.name}: содержимое таблицы не в фиде — "
                                f"«{probe[:70]}»")

    # Дзен требует, чтобы в фиде было не меньше десяти материалов
    items = feed.count("<item>")

    for line in problems:
        print(f"РАСХОЖДЕНИЕ  {line}")
    print(f"\nСтатей в фиде: {len(articles)}, исключено вручную "
          f"опубликованных: {len(PUBLISHED_BY_HAND)}, таблиц проверено: "
          f"{checked}, материалов в фиде: {items}, расхождений: {len(problems)}"
          + (f", реклама в фиде: {leaked}" if leaked else ""))
    if items < 10:
        print("В фиде меньше десяти материалов — Дзен трансляцию не включит.")
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
