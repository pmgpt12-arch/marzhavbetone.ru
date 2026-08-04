#!/usr/bin/env python3
"""Собирает заготовку для Дзена из статьи сайта.

Заготовка — не копия статьи. Отличий три, и все три родились из практики
ручных публикаций (`content/dzen/README.md`):

* **таблиц нет** — редактор Дзена работает с ними плохо, а в RSS-фиде они и
  так превращаются в списки; читатель Дзена иначе терял бы половину смысла;
* **одна ссылка на сайт в конце** — много исходящих Дзен не любит;
* **разметки внутри текста нет** — редактор вставляет `###` и `**` как
  обычные символы, и вычищать их пришлось бы прямо в статье.

Чего инструмент не делает: заголовок. На сайте заголовок поисковый
(«Возврат аванса по договору подряда: что делать в первые дни»), в Дзене
нужен крючок («Аванс требуют вернуть целиком. Считать — не первое, что
нужно делать»). Это редакторская работа, и подставлять сюда заголовок
статьи было бы тихой подменой: заготовка выглядела бы готовой, а крючка в
ней не было бы.

    python3 tools/build_dzen_draft.py <номер> <статья> --headline "..." [--query "..."]

Без `--headline` заготовка соберётся, но с пометкой, что заголовок не
написан, и в публикацию в таком виде не пойдёт.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
DRAFTS = ROOT / "content" / "dzen"
SITE = "https://marzhavbetone.ru"

HOWTO = """## Как публиковать с телефона

1. Студия Дзена → «+» → «Статья».
2. Заголовок скопировать из блока «Заголовок».
3. Обложку загрузить из `{cover}` —
   тот же файл, что на сайте.
4. Текст скопировать одним куском из блока «Текст»: разметки в нём нет,
   поэтому в редактор он ложится как есть.
5. Подзаголовки выделить стилем «Заголовок» — список в конце файла.
6. Последней строкой вставить ссылку из блока «Ссылка».
"""


def plain(fragment: str) -> str:
    """Текст без разметки, с распрямлёнными пробелами.

    Ссылки внутри абзаца становятся обычным текстом: в Дзен уходит одна
    ссылка в конце. От снятого тега остаётся пробел, и перед знаком
    препинания он читается как опечатка — поэтому подчищается.
    """
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())
    return re.sub(r"\s+([,.;:!?»])", r"\1", text).replace("« ", "«")


def table_lines(fragment: str) -> list[str]:
    """Таблица — строками списка: шапка становится подписью к каждой строке."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", fragment, re.S)
    cells = [[plain(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
             for r in rows]
    cells = [row for row in cells if any(row)]
    if not cells:
        return []
    head, body = ([], cells) if "<th" not in rows[0] else (cells[0], cells[1:])
    out = []
    for row in body:
        parts = []
        for i, value in enumerate(row[1:], start=1):
            if not value:
                continue
            label = head[i] if i < len(head) and head[i] else ""
            parts.append(f"{label}: {value}" if label else value)
        out.append(f"— {row[0]}" + (f". {'; '.join(parts)}" if parts else ""))
    return out


def article_text(source: str) -> tuple[list[str], list[str]]:
    """Текст статьи для Дзена и перечень подзаголовков."""
    main = re.search(r"<main[^>]*>(.*?)</main>", source, re.S)
    body = main.group(1) if main else source
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
    body = re.sub(r"<nav\b.*?</nav>", "", body, flags=re.S)

    blocks: list[str] = []
    heads: list[str] = []
    pattern = re.compile(r"<(p|h2|h3|ul|ol|table)(\s[^>]*)?>(.*?)</\1>", re.S)
    for match in pattern.finditer(body):
        tag, attrs, inner = match.group(1), match.group(2) or "", match.group(3)
        if "breadcrumbs" in attrs or "eyebrow" in attrs:
            continue
        if tag == "table":
            blocks.extend(table_lines(match.group(0)))
            continue
        if tag in ("ul", "ol"):
            for item in re.findall(r"<li[^>]*>(.*?)</li>", inner, re.S):
                text = plain(item)
                if text:
                    blocks.append(f"— {text}")
            continue
        text = plain(inner)
        if not text:
            continue
        if tag in ("h2", "h3"):
            heads.append(text)
        blocks.append(text)
    return blocks, heads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", help="номер материала, например 18")
    parser.add_argument("article", help="имя файла статьи без .html")
    parser.add_argument("--headline", help="заголовок для Дзена — крючок, не поисковый")
    parser.add_argument("--query", help="целевой запрос и частотность")
    parser.add_argument("--campaign", help="метка utm_campaign; по умолчанию из имени")
    args = parser.parse_args()

    path = ARTICLES / f"{args.article}.html"
    if not path.is_file():
        print(f"нет статьи {path.name}", file=sys.stderr)
        return 1
    source = path.read_text(encoding="utf-8")

    image = re.search(r'<meta\s+property="og:image"\s+content="([^"]*)"', source)
    cover = (image.group(1).replace(f"{SITE}/", "") if image
             else f"assets/{args.article}.jpg")
    blocks, heads = article_text(source)
    campaign = args.campaign or args.article[:40]
    link = (f"{SITE}/articles/{args.article}.html"
            f"?utm_source=dzen&utm_medium=article&utm_campaign={campaign}")

    headline = args.headline or "ЗАГОЛОВОК НЕ НАПИСАН — крючок, а не заголовок статьи"
    parts = [
        f"# Материал {args.number}",
        "",
        f"Обложка: `{cover}`",
        "",
    ]
    if args.query:
        parts += [f"Целевой запрос — {args.query}.", ""]
    parts += [
        HOWTO.format(cover=cover),
        "## Заголовок",
        "",
        "```",
        headline,
        "```",
        "",
        "## Текст",
        "",
        "```",
        "\n\n".join(blocks),
        "```",
        "",
        "## Подзаголовки — выделить стилем «Заголовок»",
        "",
        *[f"- {h}" for h in heads],
        "",
        "## Ссылка",
        "",
        "Вставить последней строкой публикации. UTM-метка уже проставлена, поэтому",
        "переходы и продажи из Дзена будут видны в сводке отдельно.",
        "",
        "```",
        link,
        "```",
        "",
    ]
    out = DRAFTS / f"{args.number}-{campaign}.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {len(blocks)} блоков, {len(heads)} подзаголовков"
          + ("" if args.headline else "  ЗАГОЛОВОК НЕ НАПИСАН"))
    return 0 if args.headline else 1


if __name__ == "__main__":
    sys.exit(main())
