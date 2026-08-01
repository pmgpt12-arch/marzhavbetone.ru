#!/usr/bin/env python3
"""Показывает, каким разборам нужна обложка.

Обложка живёт в трёх местах сразу: страница разбора, список разборов и
материал для Дзена. Пока её нет, статью можно публиковать — но в ленте
Дзена и в превью ссылки она проигрывает соседям, а это первое, что видит
читатель.

    python3 tools/check_covers.py

Код возврата 1, если есть разборы без нормальной обложки.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
PROMPTS = ROOT / "content" / "covers"

# Заглушку из build_cover.py опознаём по её формату, а не по весу.
# Вес обманывает: 01.08.2026 сгенерированная ночная сцена уложилась в
# 167 КБ — тёмный кадр жмётся, — и проверка объявила её заглушкой, которой
# «не хватает промпта». Ложная тревога в проверке стоит доверия ко всем
# остальным её строкам.
#
# build_cover.py рисует ровно 1200x630 PNG (см. WIDTH, HEIGHT в нём) —
# это og:image по стандарту и ни один прогон генератора такого размера не
# даёт: у него 16:9. Пара «PNG и точно 1200x630» и есть подпись заглушки.
PLACEHOLDER_SIZE = (1200, 630)
# Вес остался вторым признаком, но уже не самостоятельным
PLACEHOLDER_LIMIT_KB = 200
# Ниже этого обложка мылит на ретине. Порог Дзена — 480x320, он ниже,
# поэтому ограничивает нас именно экран, а не площадка
MIN_LONG_SIDE = 1200


def article_title(text: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    if not match:
        return "без заголовка"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", match.group(1))).strip()


def main() -> int:
    todo: list[tuple[str, str, str]] = []
    ratios: dict[str, list[str]] = {}
    # Кто чью обложку использует. Переиспользованный кадр проходит все
    # проверки ниже — он существует, он тяжёлый, он большой, — и проверка
    # молча зеленеет на статье, у которой своей обложки нет. 01.08.2026
    # так и вышло: восемь новых разборов взяли по одной картинке на
    # кластер, а check_covers отчитался «требуют внимания: 0»
    users: dict[str, list[str]] = {}
    checked = 0

    for path in sorted(ARTICLES.glob("*.html")):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        title = article_title(text)
        cover = re.search(r'article-cover[^>]*src="\.\./(assets/[^"]+)"', text)

        if not cover:
            todo.append((path.name, title, "обложка не подключена"))
            continue

        asset = ROOT / cover.group(1)
        if not asset.is_file():
            todo.append((path.name, title, f"файл {cover.group(1)} отсутствует"))
            continue

        checked += 1
        size_kb = asset.stat().st_size / 1024
        with Image.open(asset) as image:
            width, height = image.size

        if (width, height) == PLACEHOLDER_SIZE and size_kb < PLACEHOLDER_LIMIT_KB:
            prompt = PROMPTS.glob(f"*{asset.stem[:12]}*")
            has_prompt = any(prompt)
            note = "заглушка из build_cover.py"
            # Запасные промпты лежат здесь, рабочие — в prompts-articles.yaml
            # репозитория ai-business-os, куда этой проверке не дотянуться.
            # Поэтому «ПРОМПТА НЕТ» означает «здесь нет», а не «нигде нет»
            note += ", запасной промпт есть" if has_prompt else (
                ", запасного промпта нет — рабочие в prompts-articles.yaml "
                "репозитория ai-business-os")
            todo.append((asset.name, title, note))
        elif max(width, height) < MIN_LONG_SIDE:
            todo.append((asset.name, title,
                         f"{width}x{height} — мылит на ретине, нужно от "
                         f"{MIN_LONG_SIDE} px по длинной стороне"))

        ratios.setdefault(f"{width}x{height}", []).append(asset.name)
        users.setdefault(asset.name, []).append(title)

    if todo:
        print("Нужна обложка:\n")
        for asset, title, note in todo:
            print(f"  {title}")
            print(f"      {asset} — {note}")
    else:
        print("Все разборы с обложками.")

    shared = {name: titles for name, titles in users.items() if len(titles) > 1}
    if shared:
        # Замечание, а не задача: своя обложка у каждого разбора — решение
        # владельца, а не требование. Но знать, где кадр делится, надо:
        # в списке разборов две одинаковые карточки рядом читаются как
        # дубль статьи
        print("\nК сведению — одна обложка на несколько разборов:")
        for name, titles in sorted(shared.items(), key=lambda item: -len(item[1])):
            print(f"  {name} — {len(titles)}:")
            for title in titles:
                print(f"      {title}")

    if len(ratios) > 1:
        # Это замечание, а не задача: пропорция не мешает публикации, но
        # вертикальный кадр в превью ссылки обрезается по центру
        print("\nК сведению — разные пропорции. В превью ссылки вертикальные")
        print("обложки обрезаются по центру и теряют композицию:")
        for size, names in sorted(ratios.items(), key=lambda item: -len(item[1])):
            print(f"  {size}: {len(names)} — {', '.join(sorted(names)[:3])}"
                  + (" и др." if len(names) > 3 else ""))

    print(f"\nРазборов с обложками: {checked}, требуют внимания: {len(todo)}")
    return 1 if todo else 0


if __name__ == "__main__":
    sys.exit(main())
