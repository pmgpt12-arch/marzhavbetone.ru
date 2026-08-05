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


# Статьи, опубликованные в Дзене вручную до включения RSS-трансляции.
#
# Дзен привозит из фида всё, чего у него ещё нет, и по одному адресу
# заводит вторую публикацию: накопленные дочитывания и подписчики
# остаются у первой, а показы делятся между двумя. Поэтому исключение
# делается ДО включения трансляции, а не после.
#
# Список снят с экрана Студии 04.08.2026: одиннадцать опубликованных,
# сопоставлены с заготовками content/dzen по заголовку. Репозиторий до
# этого считал девять — счёт вёлся по сверке канала от 27.07 и отстал.
#
# Что заставит пересмотреть: удаление ручной публикации в Студии. Тогда
# статью надо вернуть в фид, иначе она не попадёт в Дзен вовсе.
PUBLISHED_BY_HAND = {
    "genpodryadchik-zarabatyvaet-na-vas",          # материал 01
    "avans-eto-ne-dengi-eto-kryuchok",             # 02
    "bankrotstvo-genpodryadchika-5-markerov",      # 03
    "skidka-15-procentov-na-tendere-eto-otbor-zhertv",  # 04
    "pyat-dokazatelstv-vypolneniya",               # 05
    "podpisannaya-ks2-ne-znachit-chto-zaplatyat",  # 06
    "stroitelnaya-smeta-gde-teryaetsya-marzha",    # 07
    "akt-skrytyh-rabot-obrazec",                   # 08
    "krasnye-flagi-dogovora-subpodryada",          # 09
    "vklyuchenie-v-reestr-trebovaniy-kreditorov",  # 11
    "neotrabotannyy-avans",                        # 15
    "reestr-trebovaniy-kreditorov",                # 10, вышла 05.08
}

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


def table_to_list(fragment: str) -> str:
    """Таблицу — в список: Дзен внутри content:encoded таблиц не принимает.

    Раньше таблица не вырезалась, а просто не попадала в разбор: цикл идёт
    по p, h2, h3, спискам и цитатам, table в этот перечень не входит, и
    текст молча смыкался. В восемнадцати статьях из двадцати девяти это от
    трёх до двадцати одного процента текста, а в разборах формулировок —
    вся суть: колонка «что делает с деньгами» и есть материал.

    Заголовок таблицы становится подписью к каждой строке: «Формулировка —
    что делает: …; что спросить: …». Многословнее таблицы, зато читается
    подряд и на телефоне лучше, чем таблица в семь колонок.
    """
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", fragment, re.S)
    if not rows:
        return ""
    cells = [re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S) for row in rows]
    cells = [[strip_tags(c).strip() for c in row] for row in cells if row]
    if not cells:
        return ""

    head, body = ([], cells) if len(cells) == 1 else (cells[0], cells[1:])
    # Шапкой считаем первую строку, только если она из th
    if "<th" not in rows[0]:
        head, body = [], cells

    items = []
    for row in body:
        if not any(row):
            continue
        first, rest = row[0], row[1:]
        parts = []
        for i, value in enumerate(rest, start=1):
            if not value:
                continue
            label = head[i] if i < len(head) and head[i] else ""
            parts.append(f"{label}: {value}" if label else value)
        tail = "; ".join(parts)
        items.append(f"<li><strong>{first}</strong>{' — ' + tail if tail else ''}</li>")
    return "<ul>" + "".join(items) + "</ul>" if items else ""


def article_body(source: str) -> str:
    """Текст статьи для content:encoded: лид, заголовки, абзацы, списки."""
    main = re.search(r"<main[^>]*>(.*?)</main>", source, re.S)
    if not main:
        return ""
    body = main.group(1)

    # Конец текста — «Читайте также». Рекламные блоки убираются по классу,
    # а не по положению: прежде границей служил блок кнопок, но он есть не у
    # всех статей, и у тех, где его нет, карточка комплекта с ценой уезжала
    # в фид. Замер 04.08.2026: цена стояла в тексте 16 материалов из 18.
    #
    # Классы перечислены поимённо, а не маской: маска однажды съест раздел
    # статьи. Вложенных div внутри этих блоков нет — проверено, поэтому
    # закрывающий тег ищется первый.
    body = body.split('<section class="article-links"')[0]
    for promo in ("article-cta", "article-lead", "article-actions"):
        body = re.sub(rf'<div class="{promo}".*?</div>', "", body, flags=re.S)

    # Навигация (хлебные крошки) в текст статьи не идёт
    body = re.sub(r"<nav\b.*?</nav>", "", body, flags=re.S)

    # Таблицы — в списки до разбора по блокам: иначе они не попадут в него
    # вовсе и исчезнут молча
    body = re.sub(r"<table\b.*?</table>", lambda m: table_to_list(m.group(0)),
                  body, flags=re.S)

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
    skipped = []
    for path in sorted(ARTICLES.glob("*.html")):
        if path.name == "index.html":
            continue
        if path.stem in PUBLISHED_BY_HAND:
            skipped.append(path.stem)
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
    if skipped:
        print(f"исключено как опубликованное вручную: {len(skipped)} — "
              + ", ".join(sorted(skipped)))
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
