#!/usr/bin/env python3
"""Раскладывает шапку сайта из data/site/navigation.yaml по всем страницам.

Шапка руками не пишется. Замер 16.08.2026 до этого инструмента: десять
разных шапок на 84 страницах, пять страниц без шапки вовсе, один раздел под
двумя именами. Причина одна — шапка размножалась копированием, и каждая
новая страница наследовала ту, откуда её скопировали.

ЧТО СОХРАНЯЕТСЯ ИЗ СТАРОЙ ШАПКИ. Кнопка корзины: она принадлежит торговой
странице, а не шапке, и список страниц с ней ведётся в данных. Всё
остальное в шапке заменяется целиком.

ПОЧЕМУ РАЗМЕТКА ОДНА. Шапок было две — `.topbar` и `.article-nav`, — и
различались они отступом и насыщенностью шрифта. Обе описаны в styles.css,
который грузят все страницы, и обе обслуживаются одним и тем же
переключателем мобильного меню (`attribution.js` ищет
`.topbar, .article-nav` и `nav[aria-label="Основная навигация"], nav.links`).
То есть второй вариант не давал ничего, кроме второго места, где навигация
могла разойтись.

    python3 tools/build_nav.py            # показать, что изменится
    python3 tools/build_nav.py --write    # записать
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ДАННЫЕ = ROOT / "data" / "site" / "navigation.yaml"
ПРОПУСК_КАТАЛОГОВ = ("content/", ".claude/", "data/", "node_modules/", ".git/")
ПРОПУСК_ФАЙЛОВ = {"test-pokupka.html", "success.html", "fail.html"}

ШАПКА = re.compile(r"<header\b[^>]*>.*?</header>", re.S)
КОРЗИНА = re.compile(r'<button[^>]*class="[^"]*cart-toggle[^"]*".*?</button>', re.S)
ТЕЛО = re.compile(r"<body[^>]*>", re.I)


def страницы() -> list[Path]:
    out = []
    for путь in sorted(ROOT.glob("**/*.html")):
        rel = путь.relative_to(ROOT).as_posix()
        if rel.startswith(ПРОПУСК_КАТАЛОГОВ) or путь.name in ПРОПУСК_ФАЙЛОВ:
            continue
        out.append(путь)
    return out


def активный(rel: str, правила: list[dict]) -> str | None:
    for правило in правила:
        if "prefix" in правило and rel.startswith(правило["prefix"]):
            return правило["id"]
        if правило.get("page") == rel:
            return правило["id"]
    return None


def нужна_корзина(rel: str, правила: list) -> bool:
    for правило in правила:
        if isinstance(правило, str) and правило == rel:
            return True
        if isinstance(правило, dict) and rel.startswith(правило.get("prefix", "\0")):
            return True
    return False


def собрать(данные: dict, rel: str, корзина: str | None) -> str:
    brand = данные["brand"]
    текущий = активный(rel, данные.get("active", []))

    пункты = []
    for пункт in данные["items"]:
        отметка = ""
        if пункт["id"] == текущий:
            # aria-current несёт смысл для скринридера, класс — для глаза.
            # Подсветка не убирает остальные ссылки: они остаются такими же
            # кликабельными, меняется только текущая.
            отметка = ' class="is-current" aria-current="page"'
        пункты.append(f'<a href="{пункт["href"]}"{отметка}>{пункт["text"]}</a>')

    cta = данные["cta"]
    части = [
        '<header class="topbar">',
        f'<a class="brand" href="{brand["href"]}" aria-label="{brand["aria"]}">'
        f'<span class="brand-mark">{brand["mark"]}</span>'
        f'<span>{brand["text"]}</span></a>',
        '<nav aria-label="Основная навигация">' + "".join(пункты) + "</nav>",
        f'<a class="button button-small nav-cta" href="{cta["href"]}">{cta["text"]}</a>',
    ]
    if корзина:
        части.append(корзина)
    части.append("</header>")
    return "".join(части)


def main() -> int:
    разбор = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    разбор.add_argument("--write", action="store_true", help="записать изменения")
    аргументы = разбор.parse_args()

    данные = yaml.safe_load(ДАННЫЕ.read_text(encoding="utf-8"))
    пропустить = set(данные.get("skip") or [])

    изменено, добавлено, без_изменений = [], [], 0
    for путь in страницы():
        rel = путь.relative_to(ROOT).as_posix()
        if rel in пропустить:
            continue
        html = путь.read_text(encoding="utf-8")

        было = ШАПКА.search(html)
        корзина = None
        if нужна_корзина(rel, данные.get("cart_on", [])):
            # Кнопку берём из самой страницы: у неё свои id и aria-controls,
            # завязанные на панель корзины. Сочинить её здесь значило бы
            # разойтись с cart.js на первой же правке.
            найдена = КОРЗИНА.search(было.group(0) if было else html)
            корзина = найдена.group(0) if найдена else None

        новая = собрать(данные, rel, корзина)

        if было:
            if было.group(0) == новая:
                без_изменений += 1
                continue
            html_новый = html[:было.start()] + новая + html[было.end():]
            изменено.append(rel)
        else:
            тело = ТЕЛО.search(html)
            if not тело:
                print(f"ОШИБКА: в {rel} нет <body>", file=sys.stderr)
                return 2
            html_новый = html[:тело.end()] + новая + html[тело.end():]
            добавлено.append(rel)

        if аргументы.write:
            путь.write_text(html_новый, encoding="utf-8")

    глагол = "заменено" if аргументы.write else "будет заменено"
    print(f"{глагол}: {len(изменено)}, добавлено где не было: {len(добавлено)}, "
          f"без изменений: {без_изменений}")
    if добавлено:
        print("  шапки не было: " + ", ".join(добавлено))
    if not аргументы.write and (изменено or добавлено):
        print("Это показ. Записать — с ключом --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
