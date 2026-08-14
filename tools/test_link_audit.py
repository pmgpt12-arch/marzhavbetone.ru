#!/usr/bin/env python3
"""Регресс на сплошную проверку ссылок.

Появился из замера 14.08.2026: две битые ссылки на
`materialy/akt-skrytyh-rabot.html` прожили до ручного разбора, потому что
проверка обходила только каталог `articles/`. Тест держит именно это —
что проверка видит цель в любом каталоге и в любом атрибуте, а не то,
что сегодня на сайте ноль дефектов.

Запуск без pytest: python3 tools/test_link_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from link_audit import ROOT, SITE, link_integrity, resolve_target  # noqa: E402

# Файл кладётся в корень: разрешение относительных ссылок идёт от страницы,
# и подмена каталога сделала бы проверку не той, что работает на сайте.
PROBE = ROOT / ".link-audit-probe.html"

# Каталог у каждой цели свой — ровно то, на чём проверка была слепа.
BROKEN = {
    "articles": '<a href="/articles/net-takogo-razbora.html">разбор</a>',
    "products": '<a href="../products/net-takogo-tovara.html">товар</a>',
    "materialy": '<a href="/materialy/net-takogo-materiala.html">материал</a>',
    "demo": '<a href="demo/net-takoy-stranicy.html">демо</a>',
    "картинка src": '<img src="/assets/net-takoy-kartinki.jpg" alt="">',
    "скрипт src": '<script src="/net-takogo-skripta.js"></script>',
    "форма action": '<form action="/net-takogo-obrabotchika.php"></form>',
}

# Ссылки, на которые проверка ругаться не должна: внешние, якоря, почта,
# версии ассетов и выдача кассы, которой в репозитории нет по устройству.
QUIET = [
    '<a href="https://dzen.ru/marzhavbetone">Дзен</a>',
    '<a href="mailto:marzhavbetone@yandex.ru">почта</a>',
    '<a href="tel:+70000000000">телефон</a>',
    '<a href="#catalog">каталог</a>',
    '<a href="/">главная</a>',
    '<a href="/articles/">витрина</a>',
    '<link rel="stylesheet" href="/styles.css?v=deadbeef">',
    '<a href="/download.php?order=1">скачать</a>',
]


def write_probe(body: str) -> None:
    PROBE.write_text(
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<link rel="canonical" href="{SITE}/.link-audit-probe.html">'
        f"</head><body>{body}</body></html>",
        encoding="utf-8",
    )


def test_resolve_target_ignores_external_and_anchors() -> None:
    page = ROOT / "index.html"
    for value in ("https://example.com/x.html", "mailto:a@b.ru", "tel:+7",
                  "#catalog", "javascript:void(0)", "", "/orders/1.zip"):
        assert resolve_target(value, page) is None, value


def test_resolve_target_strips_query_and_hash() -> None:
    page = ROOT / "index.html"
    target = resolve_target("/styles.css?v=deadbeef", page)
    assert target is not None and target.exists(), "версия ассета съела путь"
    target = resolve_target("/articles/index.html#top", page)
    assert target is not None and target.exists(), "якорь съел путь"


def test_directory_link_resolves_to_index() -> None:
    page = ROOT / "index.html"
    target = resolve_target("/articles/", page)
    assert target == (ROOT / "articles" / "index.html"), target


def test_every_directory_and_attribute_is_checked() -> None:
    """Сердце регресса: дефект в любом каталоге и атрибуте обязан быть найден."""
    try:
        for name, markup in BROKEN.items():
            write_probe(markup)
            fails = [f for f in link_integrity() if ".link-audit-probe" in f]
            assert fails, f"проверка не увидела битую цель: {name}"
    finally:
        PROBE.unlink(missing_ok=True)


def test_valid_links_do_not_raise_findings() -> None:
    try:
        write_probe("".join(QUIET))
        fails = [f for f in link_integrity() if ".link-audit-probe" in f]
        assert not fails, f"ложное срабатывание: {fails}"
    finally:
        PROBE.unlink(missing_ok=True)


def test_site_is_clean_today() -> None:
    """Состояние сайта, а не устройство проверки: падает — значит дефект внесён."""
    assert link_integrity() == []


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
