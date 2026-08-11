#!/usr/bin/env python3
"""Достраивает шаблон разбора тем, чего в нём не хватало читателю.

Три замера 11.08.2026 и три правки под них.

**Оглавления не было ни в одной статье** (`grep -l 'class="toc' articles/*.html`
→ 0) при том, что десять разборов из тридцати двух длиннее 10 000 знаков, а в
самом длинном одиннадцать разделов. Без оглавления это лента без карты, и на
телефоне особенно: читатель не видит, сколько ещё осталось и есть ли там его
вопрос.

**Первый выход на товар стоял на 73–79% длины текста**, врезка бесплатного
материала — на 89–93%. Читатель, закрывший страницу на середине, не видел ни
одного выхода. Второй блок ставится после раздела, ближайшего к первой трети:
это то место, докуда доскроллит большинство.

**Даты на странице не было видно.** `datePublished` и `dateModified` есть в
разметке всех тридцати двух разборов, но читателю они не показаны — а в
юридической теме первый вопрос к тексту «это ещё действует?».

Правки идемпотентны: повторный прогон ничего не добавляет второй раз.

    python3 tools/article_ui.py            # показать
    python3 tools/article_ui.py --write    # проставить
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"

MIN_HEADINGS = 4      # ниже этого оглавление длиннее пользы
MIN_CHARS = 6000      # короткий разбор читается без карты
CTA_TARGET = 0.33     # доля текста, после которой ставится второй выход

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slug(text: str, taken: set[str]) -> str:
    out = "".join(TRANSLIT.get(ch, ch) for ch in text.lower())
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")[:48] or "razdel"
    base, n = out, 2
    while out in taken:
        out = f"{base}-{n}"
        n += 1
    taken.add(out)
    return out


def plain(html: str) -> str:
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def human_date(iso: str) -> str | None:
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not match:
        return None
    year, month, day = (int(x) for x in match.groups())
    if not 1 <= month <= 12:
        return None
    return f"{day} {MONTHS[month - 1]} {year}"


def content_end(text: str) -> int:
    """Где кончается сам разбор и начинается служебное. Ниже — «Читайте
    также» и баннер каналов: в оглавлении им делать нечего, это не разделы
    текста, а хвост шаблона."""
    marks = [text.find('<section class="article-links"'),
             text.find('<section class="channel-banner"'),
             text.find('class="channel-banner"')]
    marks = [m for m in marks if m > 0]
    return min(marks) if marks else len(text)


def add_heading_ids(text: str) -> tuple[str, list[tuple[str, str, int]]]:
    """Якоря разделам. Читаемые, а не «razdel-3»: по такой ссылке видно, куда
    она ведёт, и её не стыдно отправить в переписке."""
    taken: set[str] = set(re.findall(r'<h2[^>]*\bid="([^"]+)"', text))
    items: list[tuple[str, str, int]] = []

    def repl(match: re.Match[str]) -> str:
        opening, title = match.group(1), match.group(2)
        existing = re.search(r'\bid="([^"]+)"', opening)
        label = re.sub(r"<[^>]+>", "", title).strip()
        if existing:
            items.append((existing.group(1), label, match.start()))
            return match.group(0)
        anchor = slug(label, taken)
        items.append((anchor, label, match.start()))
        return f'<h2 id="{anchor}"{opening[3:]}>{title}</h2>'

    text = re.sub(r"(<h2\b[^>]*)>(.*?)</h2>", repl, text, flags=re.S)
    return text, items


def build_toc(items: list[tuple[str, str, int]]) -> str:
    rows = "\n".join(f'        <li><a href="#{a}">{t}</a></li>' for a, t, _ in items)
    return ('\n    <nav class="toc" aria-label="Содержание разбора">\n'
            "      <p class=\"toc-title\">В разборе</p>\n"
            f"      <ol>\n{rows}\n      </ol>\n    </nav>\n")


def build_date(iso_published: str, iso_modified: str) -> str:
    shown = human_date(iso_modified) or human_date(iso_published)
    if not shown:
        return ""
    word = "Обновлено" if iso_modified and iso_modified != iso_published else "Опубликовано"
    return (f'\n    <p class="article-date"><time datetime="{iso_modified or iso_published}">'
            f"{word} {shown}</time></p>\n")


def build_inline_cta(cta_html: str) -> str:
    """Короткий выход на тот же товар, что и в большом блоке внизу. Свой товар
    не выдумывается: если внизу его нет, нет и врезки."""
    link = re.search(r'href="(/products/[^"]+)"', cta_html)
    title = re.search(r"<h3[^>]*>(.*?)</h3>", cta_html, flags=re.S)
    if not link or not title:
        return ""
    name = re.sub(r"<[^>]+>", "", title.group(1)).strip()
    return ('\n    <aside class="article-cta-inline">\n'
            "      <p>Готовые документы по этой теме — "
            f'<a href="{link.group(1)}">{name}</a>.</p>\n'
            "    </aside>\n")


def place_after_third(text: str, block: str) -> str:
    """После раздела, ближайшего к первой трети текста. Считается по знакам
    текста, а не по числу разделов: разделы бывают очень разной длины."""
    heads = list(re.finditer(r"<h2\b", text))
    if len(heads) < 3:
        return text
    total = len(plain(text))
    best, best_delta = None, None
    for head in heads[1:]:
        share = len(plain(text[:head.start()])) / max(total, 1)
        delta = abs(share - CTA_TARGET)
        if best_delta is None or delta < best_delta:
            best, best_delta = head, delta
    if best is None:
        return text
    return text[:best.start()] + block.strip("\n") + "\n\n    " + text[best.start():]


def patch(text: str) -> tuple[str, list[str]]:
    done: list[str] = []

    if 'class="article-date"' not in text:
        published = re.search(r'"datePublished"\s*:\s*"([^"]+)"', text)
        modified = re.search(r'"dateModified"\s*:\s*"([^"]+)"', text)
        if published or modified:
            block = build_date(published.group(1) if published else "",
                               modified.group(1) if modified else "")
            anchor = re.search(r"</h1>", text)
            if block and anchor:
                text = text[:anchor.end()] + block + text[anchor.end():]
                done.append("дата")

    text, items = add_heading_ids(text)
    if items:
        done.append(f"якорей {len(items)}")

    if 'class="toc"' not in text:
        limit = content_end(text)
        own = [item for item in items if item[2] < limit]
        if len(own) >= MIN_HEADINGS and len(plain(text)) >= MIN_CHARS:
            lead = re.search(r'<p class="lead">.*?</p>', text, flags=re.S)
            if lead:
                text = text[:lead.end()] + build_toc(own) + text[lead.end():]
                done.append(f"оглавление из {len(own)}")

    if "article-cta-inline" not in text:
        cta = re.search(r'<div class="article-cta".*?</div>', text, flags=re.S)
        if cta:
            block = build_inline_cta(cta.group(0))
            if block:
                before = text
                text = place_after_third(text, block)
                if text != before:
                    done.append("врезка товара")

    return text, done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--rebuild", action="store_true",
                        help="пересобрать оглавления заново, а не дополнить")
    args = parser.parse_args()

    changed = 0
    for path in sorted(ARTICLES.glob("*.html")):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8")
        if args.rebuild:
            text = re.sub(r'\n?\s*<nav class="toc".*?</nav>\n?', "\n", text, flags=re.S)
        new, done = patch(text)
        if new == text:
            continue
        changed += 1
        print(f"  {path.name}: {', '.join(done)}")
        if args.write:
            path.write_text(new, encoding="utf-8")

    print()
    print(f"Разборов изменено: {changed}")
    if not args.write and changed:
        print("Это показ. Записать: --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
