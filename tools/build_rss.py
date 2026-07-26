#!/usr/bin/env python3
"""Собирает rss.xml из статей в articles/ по требованиям Дзена.

Источник истины — сами страницы статей, поэтому фид не может разойтись
с сайтом. Запуск после добавления или правки статьи:

    python3 tools/build_rss.py

Требования Дзена, которые учитывает генератор:
- обязательные элементы channel: title, link, description, language;
- обязательные элементы item: title, link, guid, pubDate (RFC-822),
  content:encoded с полным текстом;
- namespace content и media;
- обложка не меньше 480x320 (проверяется, при нарушении — ошибка);
- в content:encoded только разрешённая разметка.

Документация: https://dzen.ru/help/ru/export-content/export.html
"""
from __future__ import annotations

import html
import re
import struct
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
SITE = "https://marzhavbetone.ru"
CHANNEL_TITLE = "Маржа в бетоне"
CHANNEL_DESCRIPTION = (
    "Разборы для строительных подрядчиков: как оформить работы, "
    "защитить допработы и получить оплату."
)
AUTHOR = "Александр Сергеев"
MSK = timezone(timedelta(hours=3))

# Разметка, разрешённая Дзеном внутри content:encoded
ALLOWED_TAGS = {"p", "h2", "h3", "ul", "ol", "li", "strong", "em", "br", "a", "blockquote"}


def meta(source: str, prop: str) -> str | None:
    """Значение og:/name-метатега."""
    pattern = rf'<meta\s+(?:property|name)="{re.escape(prop)}"\s+content="([^"]*)"'
    found = re.search(pattern, source)
    return html.unescape(found.group(1)) if found else None


def image_type(path: Path) -> str:
    """MIME-тип по содержимому файла, а не по расширению: часть обложек
    лежит с расширением .jpg, но фактически является PNG."""
    signature = path.read_bytes()[:8]
    if signature[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if signature[:3] == b"GIF":
        return "image/gif"
    return "image/jpeg"


def image_size(path: Path) -> tuple[int, int] | None:
    """Размер PNG или JPEG без внешних зависимостей."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return width, height
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            (segment,) = struct.unpack(">H", data[i + 2:i + 4])
            i += 2 + segment
    return None


def strip_tags(fragment: str) -> str:
    return re.sub(r"<[^>]+>", "", fragment).strip()


def article_body(source: str) -> str:
    """Текст статьи для content:encoded: лид, заголовки, абзацы, списки."""
    main = re.search(r"<main[^>]*>(.*?)</main>", source, re.S)
    if not main:
        return ""
    body = main.group(1)

    # Отрезаем всё после основного текста: кнопки действий и «Читайте также»
    for cutoff in ('<div class="article-actions"', '<section class="article-links"'):
        body = body.split(cutoff)[0]

    # Навигация (хлебные крошки) в текст статьи не идёт
    body = re.sub(r"<nav\b.*?</nav>", "", body, flags=re.S)

    blocks: list[str] = []
    pattern = re.compile(
        r"<(p|h2|h3|ul|ol|blockquote)(\s[^>]*)?>(.*?)</\1>", re.S
    )
    for match in pattern.finditer(body):
        tag, attrs, inner = match.group(1), match.group(2) or "", match.group(3)
        # Хлебные крошки и рубрика в текст статьи не идут
        if "breadcrumbs" in attrs or "eyebrow" in attrs:
            continue
        inner = inner.strip()
        if not inner or not strip_tags(inner):
            continue
        # Оставляем только разрешённые Дзеном теги
        inner = re.sub(
            r"</?([a-zA-Z0-9]+)([^>]*)>",
            lambda m: m.group(0) if m.group(1).lower() in ALLOWED_TAGS else "",
            inner,
        )
        blocks.append(f"<{tag}>{inner}</{tag}>")
    return "\n".join(blocks)


def collect() -> list[dict]:
    items = []
    for path in sorted(ARTICLES.glob("*.html")):
        if path.name == "index.html":
            continue
        source = path.read_text(encoding="utf-8")

        title = meta(source, "og:title") or ""
        title = re.sub(r"\s*—\s*Маржа в бетоне$", "", title)
        if not title:
            found = re.search(r"<title>(.*?)</title>", source, re.S)
            title = html.unescape(found.group(1)) if found else path.stem

        published = re.search(r'"datePublished":\s*"([^"]+)"', source)
        if not published:
            raise SystemExit(f"{path.name}: нет datePublished в разметке JSON-LD")
        date = datetime.fromisoformat(published.group(1)).replace(tzinfo=MSK)

        image = meta(source, "og:image") or ""
        image_mime = "image/jpeg"
        if image:
            local = ROOT / image.replace(f"{SITE}/", "")
            if not local.is_file():
                raise SystemExit(f"{path.name}: обложка не найдена — {local}")
            image_mime = image_type(local)
            size = image_size(local)
            if size and (size[0] < 480 or size[1] < 320):
                raise SystemExit(
                    f"{path.name}: обложка {size[0]}x{size[1]} меньше минимума Дзена 480x320"
                )

        eyebrow = re.search(r'<p class="eyebrow">(.*?)</p>', source, re.S)
        category = strip_tags(eyebrow.group(1)).split("/")[0].strip().capitalize() if eyebrow else "Разбор"

        body = article_body(source)
        if len(strip_tags(body)) < 200:
            raise SystemExit(f"{path.name}: слишком короткий текст для фида")

        items.append({
            "title": title,
            "image_type": image_mime,
            "link": f"{SITE}/articles/{path.name}",
            "description": meta(source, "og:description") or "",
            "date": date,
            "image": image,
            "category": category,
            "body": body,
        })

    items.sort(key=lambda item: item["date"], reverse=True)
    return items


def build(items: list[dict]) -> str:
    def esc(text: str) -> str:
        return html.escape(text, quote=False)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        '     xmlns:content="https://purl.org/rss/1.0/modules/content/"',
        '     xmlns:media="https://search.yahoo.com/mrss/">',
        "  <channel>",
        f"    <title>{esc(CHANNEL_TITLE)}</title>",
        f"    <link>{SITE}/</link>",
        f"    <description>{esc(CHANNEL_DESCRIPTION)}</description>",
        "    <language>ru</language>",
    ]
    for item in items:
        # Ссылка внутри текста помечена UTM — так видно переходы из Дзена
        cta = (
            f'<p><a href="{SITE}/?utm_source=dzen&amp;utm_medium=article'
            f'&amp;utm_campaign=rss">Комплекты документов для подрядчиков '
            f"на «Марже в бетоне»</a></p>"
        )
        parts += [
            "    <item>",
            f"      <title>{esc(item['title'])}</title>",
            f"      <link>{item['link']}</link>",
            f"      <guid isPermaLink=\"true\">{item['link']}</guid>",
            f"      <pubDate>{item['date'].strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>",
            f"      <author>{esc(AUTHOR)}</author>",
            f"      <category>{esc(item['category'])}</category>",
            f"      <description>{esc(item['description'])}</description>",
        ]
        if item["image"]:
            parts.append(
                f'      <enclosure url="{item["image"]}" type="{item["image_type"]}" />'
            )
            parts.append(f'      <media:content url="{item["image"]}" medium="image" />')
        parts += [
            f"      <content:encoded><![CDATA[{item['body']}\n{cta}]]></content:encoded>",
            "    </item>",
        ]
    parts += ["  </channel>", "</rss>", ""]
    return "\n".join(parts)


def main() -> int:
    items = collect()
    (ROOT / "rss.xml").write_text(build(items), encoding="utf-8")
    print(f"rss.xml собран: {len(items)} материалов")
    if len(items) < 10:
        print(
            f"ВНИМАНИЕ: Дзен принимает фид на проверку от 10 материалов, "
            f"сейчас {len(items)}. Нужно ещё {10 - len(items)}."
        )
    for item in items:
        print(f"  {item['date']:%d.%m.%Y}  {item['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
