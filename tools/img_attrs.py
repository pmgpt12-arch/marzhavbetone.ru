#!/usr/bin/env python3
"""Проставляет картинкам размеры и ленивую загрузку.

Замер 11.08.2026: в статьях 64 тега `<img>`, из них с `width` — ноль, с
`loading="lazy"` — ноль. Следствия разные и оба видны читателю:

  · без `width`/`height` браузер не знает места под картинку, пока не начал
    её качать, и текст прыгает под пальцем уже после того, как читатель начал
    читать;
  · без `loading="lazy"` телефон тянет все картинки страницы сразу, включая
    те, до которых не долистают.

Первая картинка экрана — обложка разбора и снимок главной — наоборот, должна
грузиться раньше прочего: она и есть то, что читатель ждёт. Ей ставится
`fetchpriority="high"` и никакой ленивости.

Размеры берутся из самого файла, а не назначаются: назначенный размер,
разошедшийся с настоящим, растягивает картинку.

    python3 tools/img_attrs.py            # показать
    python3 tools/img_attrs.py --write    # проставить
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = ("content/", "demo/", ".claude/")

# Классы картинок первого экрана: им ленивая загрузка вредна.
EAGER_MARKERS = ("article-cover", "hero-visual")

IMG = re.compile(r"<img\b[^>]*>", re.I)
ATTR = re.compile(r'(\w[\w-]*)\s*=\s*"([^"]*)"')


def size_of(src: str, page: Path) -> tuple[int, int] | None:
    """Размеры из файла. Путь считается от страницы: в статьях он относительный
    (`../assets/…`), на главной — от корня (`assets/…`)."""
    if src.startswith(("http://", "https://", "data:")):
        return None
    clean = src.split("?")[0]
    path = (ROOT / clean.lstrip("/")) if clean.startswith("/") else (page.parent / clean).resolve()
    if not path.exists():
        return None
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.width, image.height
    except Exception:
        return None


def eager(tag: str, before: str) -> bool:
    if any(marker in tag for marker in EAGER_MARKERS):
        return True
    # Картинка внутри hero-блока главной: класс стоит на figure, не на img
    tail = before[-400:]
    return "hero-visual" in tail and "</figure>" not in tail.split("hero-visual")[-1]


def patch(text: str, page: Path) -> tuple[str, int, int]:
    added_size = added_lazy = 0
    out = []
    position = 0
    for match in IMG.finditer(text):
        tag = match.group(0)
        out.append(text[position:match.start()])
        position = match.end()

        attrs = dict(ATTR.findall(tag))
        src = attrs.get("src", "")
        insert = ""

        if "width" not in attrs and "height" not in attrs:
            size = size_of(src, page)
            if size:
                insert += f' width="{size[0]}" height="{size[1]}"'
                added_size += 1

        if "loading" not in attrs and "fetchpriority" not in attrs:
            if eager(tag, text[:match.start()]):
                insert += ' fetchpriority="high" decoding="async"'
            else:
                insert += ' loading="lazy" decoding="async"'
                added_lazy += 1

        out.append(tag[:-1].rstrip() + insert + ">" if insert else tag)
    out.append(text[position:])
    return "".join(out), added_size, added_lazy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow не установлен — размеры взять неоткуда, обработка НЕ ЗАПУСКАЛАСЬ.")
        print("  pip install pillow")
        return 2

    files = 0
    sizes = lazies = 0
    for path in sorted(ROOT.glob("**/*.html")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(SKIP_DIRS):
            continue
        text = path.read_text(encoding="utf-8")
        if "<img" not in text:
            continue
        new, added_size, added_lazy = patch(text, path)
        if new == text:
            continue
        files += 1
        sizes += added_size
        lazies += added_lazy
        print(f"  {rel}: размеров {added_size}, ленивых {added_lazy}")
        if args.write:
            path.write_text(new, encoding="utf-8")

    print()
    print(f"Страниц изменено: {files}, проставлено размеров: {sizes}, ленивых: {lazies}")
    if not args.write and files:
        print("Это показ. Записать: --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
