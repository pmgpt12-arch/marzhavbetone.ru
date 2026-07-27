#!/usr/bin/env python3
"""Показывает, что уже опубликовано в канале Дзена, и ищет дубли.

Дзен не даёт публиковать из репозитория, пока в канале нет 10 подписчиков,
поэтому материалы уходят туда вручную. Из-за этого репозиторий не знает,
что в канале уже есть, — и материал легко подготовить второй раз.

Скрипт закрывает этот разрыв: читает список публикаций канала через
публичный API Дзена и сверяет его с заготовками в content/dzen и статьями
сайта.

Запуск:
    python3 tools/dzen_channel.py            # список публикаций и проверка
    python3 tools/dzen_channel.py --list     # только список

Код возврата 1, если найден дубль по заголовку.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DZEN_DIR = ROOT / "content" / "dzen"
ARTICLES_DIR = ROOT / "articles"
CHANNEL = "marzhavbetone"
API = "https://dzen.ru/api/v3/launcher/export?channel_name={channel}"
# Без узнаваемого User-Agent Дзен отдаёт заглушку авторизации вместо данных
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
# Слова, которые есть почти в каждом заголовке и потому ничего не различают
STOP_WORDS = {
    "как", "что", "не", "на", "в", "и", "из", "за", "по", "то", "это", "вы",
    "вас", "ваши", "сделать", "чтобы", "если", "для", "но", "а", "с", "о",
}


def fetch_items(channel: str = CHANNEL) -> list[dict]:
    request = urllib.request.Request(
        API.format(channel=channel), headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Не удалось получить канал: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Дзен ответил не JSON — вероятно, поменялся адрес API"
        ) from exc
    return payload.get("items") or []


def words(text: str) -> set[str]:
    tokens = re.findall(r"[\wЀ-ӿ]+", text.lower())
    return {token for token in tokens if len(token) > 2 and token not in STOP_WORDS}


def similarity(left: str, right: str) -> float:
    """Доля общих значимых слов относительно более короткого заголовка."""
    a, b = words(left), words(right)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def local_titles() -> list[tuple[str, str]]:
    """Заголовки заготовок для Дзена и статей сайта."""
    found: list[tuple[str, str]] = []
    for path in sorted(DZEN_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"## Заголовок\s*\n+```\n(.+?)\n```", text, re.S)
        if match:
            found.append((f"content/dzen/{path.name}", match.group(1).strip()))
    for path in sorted(ARTICLES_DIR.glob("*.html")):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
        if match:
            title = re.sub(r"<[^>]+>", "", match.group(1))
            found.append((f"articles/{path.name}", title.strip()))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Публикации канала Дзена")
    parser.add_argument("--list", action="store_true",
                        help="только показать опубликованное")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="доля общих слов, с которой считаем дублем")
    args = parser.parse_args()

    try:
        items = fetch_items()
    except RuntimeError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 1

    print(f"Опубликовано в канале: {len(items)}")
    for number, item in enumerate(items, 1):
        print(f"  {number}. {item.get('title')}")

    if args.list:
        return 0

    published = [item.get("title") or "" for item in items]
    duplicates, similar = [], []
    print("\nСверка с репозиторием")
    for source, title in local_titles():
        score, existing = max(
            ((similarity(title, item), item) for item in published), default=(0.0, "")
        )
        if score >= args.threshold:
            duplicates.append((source, title, existing, score))
        elif score >= args.threshold / 2:
            similar.append((source, title, existing, score))

    for source, title, existing, score in duplicates:
        print(f"  ДУБЛЬ {source}")
        print(f"    у нас:    {title}")
        print(f"    в Дзене:  {existing}")
        print(f"    совпадение по значимым словам: {score:.0%}")

    for source, title, existing, score in similar:
        print(f"  похоже {source} ({score:.0%})")
        print(f"    у нас:    {title}")
        print(f"    в Дзене:  {existing}")

    if not duplicates:
        print("  дублей нет" if not similar else "  явных дублей нет")
        # Заголовки на сайте короткие и рекламные, поэтому совпадение по
        # словам ловит точный повтор, но не пересечение тем. Список выше
        # напечатан целиком именно для того, чтобы тему сверил человек.
        return 0

    print(
        "\nПовторная публикация того же материала не даёт охвата и ухудшает "
        "показы канала. Для заготовок в content/dzen — заменить тему; для "
        "статей сайта — учесть при включении трансляции из rss.xml."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
