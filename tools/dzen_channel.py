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
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
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


def fetch_page(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Не удалось получить канал: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Дзен ответил не JSON — вероятно, поменялся адрес API"
        ) from exc


def fetch_items(channel: str = CHANNEL, max_pages: int = 10) -> list[dict]:
    """Все публикации канала, а не первая страница.

    Страницу площадка отдаёт по двадцать штук и продолжение кладёт в `more`.
    Первый живой замер 16.08.2026 это и показал: в ответе ровно 20 записей,
    а самых старых ручных публикаций в них нет — счёт по одной странице
    занизил бы канал и показал бы «пропавшие» материалы, которых никто не
    терял.
    """
    items, url, seen_urls = [], API.format(channel=channel), set()
    for _ in range(max_pages):
        if not url or url in seen_urls:
            break
        seen_urls.add(url)
        payload = fetch_page(url)
        page = payload.get("items") or []
        if not page:
            break
        items.extend(page)
        more = payload.get("more") or {}
        url = more.get("link") if isinstance(more, dict) else None
    return items


def channel_meta(channel: str = CHANNEL) -> dict:
    """Что площадка говорит о самом канале, включая подписчиков.

    Подписчики здесь есть — вопреки тому, что считалось. Прежде было
    записано, что публичный экспорт счётчика не отдаёт и число снимается
    только с экрана Студии; первый живой ответ 16.08.2026 показал
    `source.subscribers`, и ручной шаг владельца на этом снимается.
    """
    payload = fetch_page(API.format(channel=channel))
    for item in payload.get("items") or []:
        source = item.get("source") or {}
        if source.get("subscribers") is not None:
            return {
                "channel": source.get("url"),
                "title": source.get("title"),
                "subscribers": source.get("subscribers"),
                "publisher_id": source.get("publisher_id"),
                "share_link": source.get("feed_share_link"),
            }
    return {}


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


def expected_from_feed() -> dict[str, str]:
    """slug → заголовок, с которым статья уходит в ленту.

    Берётся из сборщика фида, а не повторяется здесь: две копии расписания
    разошлись бы молча. Придержанные до срока в расчёт не идут — Дзену их
    ещё не отдавали, и их отсутствие в канале ничего не значит.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from build_rss import PUBLISHED_BY_HAND, RELEASE, dzen_titles

    today = date.today().isoformat()
    headlines = dzen_titles()
    expected: dict[str, str] = {}
    for path in sorted(ARTICLES_DIR.glob("*.html")):
        if path.name == "index.html" or path.stem in PUBLISHED_BY_HAND:
            continue
        due = RELEASE.get(path.stem)
        if due and due > today:
            continue
        title = headlines.get(path.stem)
        if not title:
            # Ровно то, что кладёт в фид build_rss: og:title без хвоста
            # бренда. Здесь стоял <h1>, и это давало ложное «не привезено»:
            # у dolg-zakryvali h1 звучит «...как четыре дома подряд
            # превратились в 28 млн», а в ленту и в канал ушло
            # «...случай на 28 млн» (замер 16.08.2026).
            text = path.read_text(encoding="utf-8", errors="replace")
            found = re.search(
                r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
                text,
            )
            title = html.unescape(found.group(1)) if found else ""
            title = re.sub(r"\s*—\s*Маржа в бетоне$", "", title)
        if title:
            expected[path.stem] = title
    return expected


def normalize(title: str) -> str:
    """Заголовок под точное сравнение: регистр, тире, кавычки, пробелы."""
    text = title.casefold().replace(" ", " ")
    for dash in ("—", "–", "‑", "−"):
        text = text.replace(dash, "-")
    for quote in ("«", "»", "“", "”", "„", "‘", "’"):
        text = text.replace(quote, '"')
    return " ".join(text.split())


def delivered_slugs(items: list[dict], expected: dict[str, str]) -> list[str]:
    """Какие статьи ленты доехали до канала.

    Сравнение точное, а не по словам, и это не придирка. `similarity()`
    делит общие слова на длину более короткого заголовка, поэтому ручная
    публикация «Аванс — это не деньги. Это крючок» совпадает с ожидаемым
    «Аванс по договору подряда: почему работа начинается на ваши деньги» на
    67% — две общие значимые слова из трёх. Для поиска дублей такой перекос
    в сторону лишнего срабатывания правильный, здесь — нет: он объявил бы
    трансляцию включённой на канале, куда она ничего не привозила (замер
    16.08.2026 на подставных данных).

    Точное сравнение здесь и есть верный признак: привозя материал из ленты,
    Дзен берёт заголовок из `<title>` дословно.
    """
    seen = {normalize(item.get("title") or "") for item in items}
    # Ссылка надёжнее заголовка, если площадка её отдаёт. Схема публичного
    # экспорта в репозитории не проверена — с раннера этого замера ещё не
    # делали, — поэтому ссылка используется, когда есть, и не требуется.
    links = " ".join(
        str(item.get(key) or "")
        for item in items
        for key in ("link", "url", "share_link", "canonical_url")
    )
    delivered = []
    for slug, title in sorted(expected.items()):
        if normalize(title) in seen or f"/articles/{slug}.html" in links:
            delivered.append(slug)
    return delivered


def snapshot(items: list[dict], threshold: float) -> str:
    """Снимок канала: сколько привезено из ленты, а сколько ещё нет.

    Это единственный способ узнать снаружи, включена ли трансляция: Студия
    из репозитория не читается, а привезённый материал в канале виден.
    Подписчиков здесь нет и быть не может — публичный экспорт их не отдаёт,
    и подставлять сюда число с экрана Студии значило бы выдать снятое
    руками за замер.
    """
    published = [item.get("title") or "" for item in items]
    expected = expected_from_feed()
    delivered = delivered_slugs(items, expected)
    missing = [slug for slug in sorted(expected) if slug not in delivered]

    lines = [
        "# Снимок канала Дзена. Собирается tools/dzen_channel.py --snapshot",
        "# из GitHub Actions: dzen.ru из облачной сессии закрыт (CONNECT 403).",
        f"channel: {CHANNEL}",
        f"measured_at: {date.today().isoformat()}",
        f"publications: {len(items)}",
        "# Статьи, которым срок ленты пришёл. Привезённые — те, чей заголовок",
        "# нашёлся в канале; совпадение по значимым словам, не по строке.",
        f"feed_due: {len(expected)}",
        f"feed_delivered: {len(delivered)}",
        f"feed_missing: {len(missing)}",
        "# Одна привезённая — уже доказательство: ручные публикации из ленты",
        "# исключены (PUBLISHED_BY_HAND), совпасть заголовком случайно нечему.",
        "# Ноль привезённых доказательством обратного не является: трансляция",
        "# может быть не включена, а может быть включена и ещё не отработать.",
        "# Различает это повторный снимок, а не этот.",
        f"translation_live: {'yes' if delivered else 'unknown'}",
        "delivered:",
        *[f"  - {slug}" for slug in delivered],
        "missing:",
        *[f"  - {slug}" for slug in missing],
        "titles_in_channel:",
        *[f"  - {json.dumps(title, ensure_ascii=False)}" for title in published],
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Публикации канала Дзена")
    parser.add_argument("--list", action="store_true",
                        help="только показать опубликованное")
    parser.add_argument("--snapshot", metavar="ПУТЬ", nargs="?",
                        const="", default=None,
                        help="записать снимок канала в файл (по умолчанию "
                             "content/metrics/dzen-<дата>.yaml)")
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

    if args.snapshot is not None:
        target = Path(args.snapshot) if args.snapshot else (
            ROOT / "content" / "metrics" / f"dzen-{date.today().isoformat()}.yaml"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        text = snapshot(items, args.threshold)
        target.write_text(text, encoding="utf-8")
        print(f"\nСнимок записан: {target.relative_to(ROOT)}")
        print(text)
        return 0

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
