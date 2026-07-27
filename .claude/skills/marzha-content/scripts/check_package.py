#!/usr/bin/env python3
"""Проверяет контент-пакет перед коммитом.

Собирает воедино проверки, каждая из которых уже ломалась на практике:
битые внутренние ссылки, сдвинутая нумерация в JSON-LD, забытая запись в
sitemap, обложка меньше минимума Дзена, статья без даты публикации,
невалидный пост Telegram.

Запуск из корня репозитория:

    python3 .claude/skills/marzha-content/scripts/check_package.py <slug>

Без аргумента проверяет весь сайт целиком (полезно после правок навигации).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SITE = "https://marzhavbetone.ru"

problems: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    problems.append(message)
    print(f"  ✗ {message}")


def ok(message: str) -> None:
    print(f"  ✓ {message}")


def note(message: str) -> None:
    notes.append(message)
    print(f"  ! {message}")


def check_article(slug: str) -> None:
    print(f"\nСтраница разбора articles/{slug}.html")
    path = ROOT / "articles" / f"{slug}.html"
    if not path.is_file():
        fail(f"файла нет: {path.relative_to(ROOT)}")
        return
    source = path.read_text(encoding="utf-8")

    required = {
        'meta name="description"': r'<meta name="description"',
        "og:title": r'property="og:title"',
        "og:image": r'property="og:image"',
        "og:url": r'property="og:url"',
        "canonical": r'rel="canonical"',
        "eyebrow (рубрика)": r'<p class="eyebrow">',
        "обложка article-cover": r'class="article-cover"',
        "лид": r'<p class="lead">',
    }
    missing = [name for name, pattern in required.items()
               if not re.search(pattern, source)]
    if missing:
        fail(f"в разметке нет: {', '.join(missing)}")
    else:
        ok("обязательные метатеги и элементы на месте")

    # datePublished — без него генератор фида останавливает деплой
    if not re.search(r'"datePublished":\s*"\d{4}-\d{2}-\d{2}"', source):
        fail('нет "datePublished" в JSON-LD — фид Дзена не соберётся')
    else:
        ok("datePublished указан")

    # JSON-LD должен парситься
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
    for i, block in enumerate(blocks, 1):
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            fail(f"JSON-LD блок {i} не парсится: {exc}")
            break
    else:
        if blocks:
            ok(f"JSON-LD валиден ({len(blocks)} блок(ов))")

    # Обложка: существует и не меньше минимума Дзена
    cover = re.search(r'property="og:image" content="([^"]+)"', source)
    if cover:
        local = ROOT / cover.group(1).replace(f"{SITE}/", "")
        if not local.is_file():
            fail(f"обложка не найдена: {local.relative_to(ROOT)}")
        else:
            size = image_size(local)
            if size is None:
                note(f"не удалось прочитать размер обложки {local.name}")
            elif size[0] < 480 or size[1] < 320:
                fail(f"обложка {size[0]}x{size[1]} меньше минимума Дзена 480x320")
            else:
                ok(f"обложка {size[0]}x{size[1]}")

    check_links(path, source)


def image_size(path: Path) -> tuple[int, int] | None:
    import struct
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


def check_links(path: Path, source: str) -> None:
    broken = []
    for href in set(re.findall(r'href="([^"]+)"', source)):
        if href.startswith(("http", "mailto:", "#", "tel:")):
            continue
        target = href.split("#")[0].split("?")[0]
        if not target:
            continue
        if target.startswith("/"):
            candidate = ROOT / target.lstrip("/")
        else:
            candidate = (path.parent / target).resolve()
        if target.endswith("/"):
            candidate = candidate / "index.html"
        if not candidate.exists():
            broken.append(href)
    if broken:
        fail(f"битые внутренние ссылки: {', '.join(sorted(broken))}")
    else:
        ok("все внутренние ссылки живые")


def check_navigation(slug: str | None) -> None:
    print("\nНавигация: список разборов и карта сайта")
    index = ROOT / "articles" / "index.html"
    source = index.read_text(encoding="utf-8")

    block = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
    if not block:
        fail("в articles/index.html нет JSON-LD")
    else:
        try:
            data = json.loads(block.group(1))
        except json.JSONDecodeError as exc:
            fail(f"JSON-LD списка разборов не парсится: {exc}")
            data = None
        if data:
            items = data["@graph"][0]["itemListElement"]
            positions = [item["position"] for item in items]
            if positions != list(range(1, len(items) + 1)):
                fail(f"нумерация в ItemList нарушена: {positions}")
            else:
                ok(f"ItemList: {len(items)} позиций, нумерация подряд")
            if slug:
                urls = " ".join(i["item"]["url"] for i in items)
                if slug not in urls:
                    fail(f"статьи {slug} нет в ItemList списка разборов")
                else:
                    ok("статья есть в ItemList")

    if slug:
        if f'href="{slug}.html"' not in source:
            fail(f"нет карточки статьи в сетке showcase-grid")
        else:
            ok("карточка в списке разборов есть")

        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        if f"/articles/{slug}.html" not in sitemap:
            fail("статьи нет в sitemap.xml")
        else:
            ok("запись в sitemap.xml есть")


def check_feed() -> None:
    print("\nФид Дзена")
    result = subprocess.run(
        [sys.executable, "tools/build_rss.py"],
        cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"фид не собирается: {result.stdout.strip()} {result.stderr.strip()}")
        return
    count = re.search(r"собран: (\d+) материалов", result.stdout)
    total = int(count.group(1)) if count else 0
    ok(f"фид собирается, материалов: {total}")
    if total < 10:
        note(f"Дзен принимает фид на проверку от 10 материалов, сейчас {total} — "
             f"нужно ещё {10 - total}")
    (ROOT / "rss.xml").unlink(missing_ok=True)


def check_telegram(slug: str | None) -> None:
    print("\nПост в Telegram")
    posts_dir = ROOT / "content" / "telegram"
    if not posts_dir.is_dir():
        note("папки content/telegram нет — пост не подготовлен")
        return
    if slug:
        # Ищем по ссылке в шапке, а не по имени файла: имя поста включает дату
        # публикации и обычно короче слага статьи, а ссылка однозначна.
        matching = [p for p in posts_dir.glob("*.md")
                    if p.name != "README.md"
                    and f"/articles/{slug}.html" in p.read_text(encoding="utf-8")]
        if not matching:
            note(f"нет поста в content/telegram со ссылкой на {slug} — "
                 f"пост для Telegram не подготовлен")
        else:
            ok(f"пост найден: {matching[0].name}")

    result = subprocess.run(
        [sys.executable, "tools/post_telegram.py", "--dry-run"],
        cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"пост не проходит проверку: {result.stderr.strip()}")
    else:
        ok("все посты валидны (разметка, длина, дата, ссылка)")


def check_social(slug: str | None) -> None:
    if not slug:
        return
    print("\nМатериалы Instagram и MAX")
    path = ROOT / "content" / "social" / f"{slug}.md"
    if not path.is_file():
        note(f"нет content/social/{slug}.md — материалы для Instagram и MAX "
             f"не подготовлены")
        return
    text = path.read_text(encoding="utf-8")
    for source_name in ("utm_source=instagram", "utm_source=max"):
        if source_name not in text:
            fail(f"в материалах нет метки {source_name} — продажи "
                 f"из этой площадки не будут видны отдельно")
    if all(s in text for s in ("utm_source=instagram", "utm_source=max")):
        ok("UTM-метки для обеих площадок на месте")


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    if slug:
        slug = slug.removesuffix(".html")
        print(f"Проверка контент-пакета: {slug}")
        check_article(slug)
    else:
        print("Проверка сайта целиком (slug не указан)")

    check_navigation(slug)
    check_feed()
    check_telegram(slug)
    check_social(slug)

    print("\n" + "=" * 60)
    if problems:
        print(f"Проблем: {len(problems)} — публиковать нельзя")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    if notes:
        print(f"Проблем нет. Обратить внимание: {len(notes)}")
        for n in notes:
            print(f"  ! {n}")
        return 0
    print("Всё в порядке — пакет готов к коммиту")
    return 0


if __name__ == "__main__":
    sys.exit(main())
