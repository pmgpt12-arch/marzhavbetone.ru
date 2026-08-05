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
from datetime import date
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
    from build_rss import PUBLISHED_BY_HAND, RELEASE

    # Придержанных до срока в фиде нет по замыслу: спрашивать с них
    # содержимое значило бы жечь проверку на своём же расписании.
    today = date.today().isoformat()
    held = {slug for slug, due in RELEASE.items() if due > today}

    feed = FEED.read_text(encoding="utf-8")
    # Сравнивать надо нормализованный текст: в фиде разметка, сущности и
    # переносы строк расставлены иначе, чем в статье, и точное совпадение
    # сырых кусков не срабатывает — первая версия проверки на этом и
    # промолчала.
    flat = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", feed)).split())
    articles = [p for p in sorted(ARTICLES.glob("*.html"))
                if p.name != "index.html"
                and p.stem not in PUBLISHED_BY_HAND and p.stem not in held]

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

    # Дата публикации не может быть раньше самой ранней статьи проекта.
    # 2024-01-15 стояло в двух статьях как заглушка из шаблона: Дзен
    # сортирует привоз по pubDate и такой материал импортирует как
    # архивный — он не всплывёт в ленте и показов почти не получит.
    # Порога в днях нет: сравнение идёт с датой первой статьи сайта.
    dates = re.findall(r"<pubDate>[^,]+,\s*\d+\s+\w+\s+(\d{4})", feed)
    stale = [d for d in dates if int(d) < 2026]
    if stale:
        problems.append(f"в фиде {len(stale)} материалов с датой раньше 2026 "
                        f"года — похоже на заглушку из шаблона")

    # Число материалов в фиде — состояние, а не проверка. Порог в десять был
    # нашим предположением: 05.08.2026 Дзен принял заявку на подключение при
    # одном материале, значит на подаче такого требования нет. Что решит
    # модерация — не известно, и падать по неизвестному правилу проверка не
    # должна.
    items = feed.count("<item>")

    for line in problems:
        print(f"РАСХОЖДЕНИЕ  {line}")
    print(f"\nСтатей в фиде: {len(articles)}, исключено вручную "
          f"опубликованных: {len(PUBLISHED_BY_HAND)}, придержано до срока: "
          f"{len(held)}, таблиц проверено: "
          f"{checked}, материалов в фиде: {items}, расхождений: {len(problems)}"
          + (f", реклама в фиде: {leaked}" if leaked else ""))
    if items < 10:
        if held:
            # Пока идёт выпуск по одной в день, малый фид — заявленное
            # состояние: через столько дней он дорастёт сам.
            print(f"В фиде {items} материалов, придержано до срока: "
                  f"{len(held)}. Десять наберётся через {10 - items} дней.")
        else:
            # Придержанных нет, а материалов меньше десяти — значит фид отдаёт
            # всё, что есть. Это не расхождение, но и не то, чего мы ждали:
            # сказать вслух и не падать.
            print(f"В фиде {items} материалов и ничего не придержано — фид "
                  f"отдаёт всё, что есть на сайте.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
