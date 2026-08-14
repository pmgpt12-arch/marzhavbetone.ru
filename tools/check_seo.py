#!/usr/bin/env python3
"""Сверяет замеренный спрос с тем, что на сайте действительно опубликовано.

Семантика лежит в `content/strategy/semantic-core.csv` — 585 строк с колонкой
«Целевой URL», подтверждённых Wordstat. Ни один инструмент репозитория эту
колонку с реальностью не сверял, и расхождение накопилось молча: замер
13.08.2026 показал, что из целевых URL семантики в `sitemap.xml` не попал
ни один, а 462 запроса метят в раздел `/baza-znanii/`, которого на сайте нет.
Обходом живого сайта такое не находится — семантика лежит в `content/`,
который не деплоится.

Проверка делит найденное на два вида, и это не оттенки строгости.

  РАСХОЖДЕНИЕ — дефект: страница выпала из карты сайта, canonical увёл на
    чужой адрес, два запроса конкурируют за один URL, две страницы носят
    один `<title>`. Чинится тем, кто нашёл, и поднимает код возврата.

  РЕШЕНИЕ — не дефект: где живёт раздел, строить ли страницу под запрос,
    нужна ли статье строка в семантике. Архитектура и состав каталога
    остаются владельцу (CLAUDE.md, «Не дефекты, а решения»), поэтому такие
    строки печатаются, но кода возврата не меняют.

    python3 tools/check_seo.py
    python3 tools/check_seo.py --json отчёт.json

Код возврата 1, если есть расхождения.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://marzhavbetone.ru"
SEMANTIC = ROOT / "content" / "strategy" / "semantic-core.csv"

# Страницы, которых в поиске быть не должно: служебные экраны кассы и
# страница, закрытая в robots.txt. Их отсутствие в sitemap — норма, а не
# находка.
NOT_FOR_SEARCH = {
    "/success.html",
    "/fail.html",
    "/test-pokupka.html",
}

# Где лежат страницы, попадающие в поиск.
PAGE_GLOBS = (
    "*.html",
    "articles/*.html",
    "products/*.html",
    "materialy/*.html",
    "demo/*.html",
)

CANONICAL = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"')
TITLE = re.compile(r"<title>(.*?)</title>", re.S)


def page_url(path: Path) -> str:
    """Адрес страницы на сайте по её файлу."""
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def site_pages() -> list[Path]:
    seen: list[Path] = []
    for pattern in PAGE_GLOBS:
        seen.extend(sorted(ROOT.glob(pattern)))
    return seen


def sitemap_paths() -> set[str]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return set()
    text = sitemap.read_text(encoding="utf-8")
    return {
        loc.replace(SITE, "") or "/"
        for loc in re.findall(r"<loc>(.*?)</loc>", text)
    }


def semantic_rows() -> list[dict[str, str]]:
    if not SEMANTIC.exists():
        return []
    with SEMANTIC.open(encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh)]


def slug_of(url: str) -> str:
    """Имя страницы без каталога и расширения.

    Семантика пишет целевые URL каталогом (`/baza-znanii/akty-.../`), сайт
    отдаёт файлом (`/articles/akty-....html`). Без срезанного `.html` один и
    тот же материал в этих двух записях не узнаётся.
    """
    tail = url.strip("/").split("/")[-1]
    return tail[: -len(".html")] if tail.endswith(".html") else tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="куда положить отчёт")
    args = parser.parse_args()

    pages = site_pages()
    in_sitemap = sitemap_paths()
    rows = semantic_rows()

    defects: list[str] = []
    decisions: list[str] = []

    # --- дефекты -----------------------------------------------------------
    titles: dict[str, list[str]] = defaultdict(list)
    published: dict[str, Path] = {}

    for path in pages:
        url = page_url(path)
        if url in NOT_FOR_SEARCH:
            continue
        published[url] = path
        html = path.read_text(encoding="utf-8", errors="replace")

        # Canonical на другой адрес — норма: так склеивают дубль
        # (`rekvizity.html` → `contacts.html`). Он же решает, ждём ли мы
        # страницу в карте сайта: два сигнала должны говорить одно.
        found = CANONICAL.search(html)
        declared = found.group(1).replace(SITE, "") or "/" if found else url
        canonical_elsewhere = declared != url

        if canonical_elsewhere and url in in_sitemap:
            defects.append(
                f"карта сайта зовёт индексировать, canonical уводит: "
                f"{url} → {declared}"
            )
        elif not canonical_elsewhere and url not in in_sitemap:
            defects.append(f"нет в sitemap.xml: {url}")

        title = TITLE.search(html)
        if title:
            titles[" ".join(title.group(1).split())].append(url)

    for title, urls in sorted(titles.items()):
        if len(urls) > 1:
            defects.append(
                "один <title> у разных страниц, они конкурируют в выдаче: "
                f"«{title}» — {', '.join(sorted(urls))}"
            )

    # Обратная сторона: карта сайта зовёт робота туда, где страницы нет.
    for url in sorted(in_sitemap - set(published)):
        defects.append(f"в sitemap.xml есть, страницы нет: {url}")

    # Два запроса из разных кластеров, нацеленные на одну страницу, —
    # каннибализация, заложенная ещё в план.
    by_target: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        target = row.get("Целевой URL", "").strip()
        if target:
            by_target[target].add(row.get("Кластер", "").strip())
    for target, clusters in sorted(by_target.items()):
        if len(clusters) > 1:
            defects.append(
                f"один целевой URL у разных кластеров: {target} — "
                + ", ".join(sorted(clusters))
            )

    # --- решения владельца -------------------------------------------------
    planned = {row.get("Целевой URL", "").strip() for row in rows}
    planned.discard("")

    missing_by_section: dict[str, int] = defaultdict(int)
    moved: list[tuple[str, str]] = []
    published_slugs = {slug_of(url): url for url in published}

    for target in sorted(planned):
        if target in published or target in in_sitemap:
            continue
        elsewhere = published_slugs.get(slug_of(target))
        if elsewhere:
            moved.append((target, elsewhere))
        else:
            section = "/" + target.strip("/").split("/")[0] + "/"
            missing_by_section[section] += 1

    for section, count in sorted(missing_by_section.items()):
        exists = (ROOT / section.strip("/")).is_dir()
        decisions.append(
            f"запросов метят в {section}: {count}; раздел на сайте "
            + ("есть, страниц под них нет" if exists else "не существует")
        )
    for target, elsewhere in moved:
        decisions.append(
            f"страница есть по другому адресу: план {target} → факт {elsewhere}"
        )

    planned_slugs = {slug_of(t) for t in planned}
    unplanned = sorted(
        url
        for url in published
        if url.startswith("/articles/")
        and url != "/articles/"
        and slug_of(url) not in planned_slugs
    )
    if unplanned:
        decisions.append(
            f"разборов без строки в семантике: {len(unplanned)} "
            f"(например {', '.join(unplanned[:3])})"
        )

    # --- вывод -------------------------------------------------------------
    for line in defects:
        print(f"РАСХОЖДЕНИЕ  {line}")
    for line in decisions:
        print(f"РЕШЕНИЕ      {line}")

    print(
        f"\nСтраниц в поиске: {len(published)}, в sitemap.xml: "
        f"{len(in_sitemap)}, строк семантики: {len(rows)}, "
        f"целевых URL: {len(planned)}, расхождений: {len(defects)}, "
        f"решений владельцу: {len(decisions)}"
    )

    if args.json:
        args.json.write_text(
            json.dumps(
                {"defects": defects, "decisions": decisions},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
