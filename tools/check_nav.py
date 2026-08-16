#!/usr/bin/env python3
"""Шапка сайта одна и та же везде — проверка, а не обещание.

Замер 16.08.2026 до появления `build_nav.py`: десять разных шапок на 84
страницах. На странице разбора в шапке стояли «Все разборы, Каталог,
Telegram» — ни диагностики, ни бесплатных материалов, ни калькуляторов;
пять юридических страниц не имели шапки вовсе. Читатель, пришедший из
поиска на разбор, не имел из него ни одного пути в разделы сайта.

Проверка сверяет то, что лежит в страницах, с `data/site/navigation.yaml`:

  1. шапка есть и она одна;
  2. набор пунктов и их адреса совпадают с каноном — порядок тоже, потому
     что переставленная навигация читается как другая;
  3. подсвечен ровно тот пункт, который назначен правилами (и не более
     одного);
  4. адреса пунктов ведут в существующие цели;
  5. корзина стоит там, где объявлена, и не стоит там, где нет.

Список страниц не хранится: файлы берутся обходом каталога, поэтому новая
страница попадает под проверку сама, без правки этого файла.

    python3 tools/check_nav.py              # проверить
    python3 tools/check_nav.py --inventory  # какие варианты шапки есть
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ДАННЫЕ = ROOT / "data" / "site" / "navigation.yaml"
ПРОПУСК_КАТАЛОГОВ = ("content/", ".claude/", "data/", "node_modules/", ".git/")
ПРОПУСК_ФАЙЛОВ = {"test-pokupka.html", "success.html", "fail.html"}

ШАПКА = re.compile(r"<header\b[^>]*>.*?</header>", re.S)
ССЫЛКА = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S)


def страницы() -> list[Path]:
    out = []
    for путь in sorted(ROOT.glob("**/*.html")):
        rel = путь.relative_to(ROOT).as_posix()
        if rel.startswith(ПРОПУСК_КАТАЛОГОВ) or путь.name in ПРОПУСК_ФАЙЛОВ:
            continue
        out.append(путь)
    return out


def пункты_шапки(шапка: str) -> list[tuple[str, str, str]]:
    """(текст, адрес, класс) по каждой ссылке навигации, без бренда и призыва."""
    навигация = re.search(r"<nav\b[^>]*>.*?</nav>", шапка, re.S)
    if not навигация:
        return []
    out = []
    for атрибуты, текст in ССЫЛКА.findall(навигация.group(0)):
        href = re.search(r'href="([^"]*)"', атрибуты)
        класс = re.search(r'class="([^"]*)"', атрибуты)
        чистый = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", текст)).strip()
        out.append((чистый, href.group(1) if href else "",
                    класс.group(1) if класс else ""))
    return out


def цель_существует(href: str) -> bool:
    """Ведёт ли адрес пункта в существующий файл.

    Якорь на главную (`/#author`) проверяется по самой главной: пункт,
    указывающий в несуществующий раздел, — это та же битая ссылка, просто
    её не видно кодом ответа.
    """
    адрес = href.split("?")[0]
    якорь = ""
    if "#" in адрес:
        адрес, якорь = адрес.split("#", 1)
    if адрес in ("", "/"):
        файл = ROOT / "index.html"
    else:
        файл = ROOT / адрес.lstrip("/")
        if файл.is_dir() or адрес.endswith("/"):
            файл = файл / "index.html"
    if not файл.is_file():
        return False
    if якорь:
        текст = файл.read_text(encoding="utf-8", errors="replace")
        return f'id="{якорь}"' in текст
    return True


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


def main() -> int:
    разбор = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    разбор.add_argument("--inventory", action="store_true",
                        help="показать варианты шапки, ничего не проверяя")
    аргументы = разбор.parse_args()

    данные = yaml.safe_load(ДАННЫЕ.read_text(encoding="utf-8"))
    канон = [(п["text"], п["href"], п["id"]) for п in данные["items"]]
    пропустить = set(данные.get("skip") or [])
    список = [п for п in страницы()
              if п.relative_to(ROOT).as_posix() not in пропустить]

    if аргументы.inventory:
        варианты = collections.Counter()
        где = collections.defaultdict(list)
        for путь in список:
            шапка = ШАПКА.search(путь.read_text(encoding="utf-8", errors="replace"))
            ключ = tuple(т for т, _, _ in пункты_шапки(шапка.group(0))) if шапка \
                else ("(шапки нет)",)
            варианты[ключ] += 1
            где[ключ].append(путь.relative_to(ROOT).as_posix())
        print(f"страниц: {len(список)}, вариантов шапки: {len(варианты)}")
        for ключ, сколько in варианты.most_common():
            print(f"  {сколько:3} — {list(ключ)}")
            print(f"       напр.: {где[ключ][:3]}")
        return 0

    # Адреса канона проверяются один раз, а не на каждой странице: цель у
    # них общая, и 84 одинаковых сообщения о битом пункте читать невозможно.
    дефекты: list[str] = []
    for текст, href, _ in канон:
        if not цель_существует(href):
            дефекты.append(f"канон: пункт «{текст}» ведёт в никуда — {href}")
    if not цель_существует(данные["cta"]["href"]):
        дефекты.append(f"канон: призыв ведёт в никуда — {данные['cta']['href']}")

    for путь in список:
        rel = путь.relative_to(ROOT).as_posix()
        html = путь.read_text(encoding="utf-8", errors="replace")
        все = ШАПКА.findall(html)
        if not все:
            дефекты.append(f"{rel}: шапки нет вовсе")
            continue
        if len(все) > 1:
            дефекты.append(f"{rel}: шапок {len(все)}, должна быть одна")
        шапка = все[0]

        пункты = пункты_шапки(шапка)
        было = [(т, h) for т, h, _ in пункты]
        надо = [(т, h) for т, h, _ in канон]
        if было != надо:
            не_хватает = [т for т, _ in надо if т not in [x for x, _ in было]]
            лишние = [т for т, _ in было if т not in [x for x, _ in надо]]
            подробно = []
            if не_хватает:
                подробно.append("нет: " + ", ".join(не_хватает))
            if лишние:
                подробно.append("лишние: " + ", ".join(лишние))
            if not подробно:
                подробно.append("другой порядок или адреса")
            дефекты.append(f"{rel}: навигация разошлась с каноном — "
                           + "; ".join(подробно))
            continue

        ожидаемый = активный(rel, данные.get("active", []))
        текущие = [т for т, _, к in пункты if "is-current" in к]
        если_надо = [т for т, _, i in канон if i == ожидаемый]
        if len(текущие) > 1:
            дефекты.append(f"{rel}: подсвечено несколько пунктов — {текущие}")
        elif ожидаемый and текущие != если_надо:
            дефекты.append(f"{rel}: подсвечен {текущие or 'никто'}, "
                           f"а должен {если_надо}")
        elif not ожидаемый and текущие:
            дефекты.append(f"{rel}: подсвечен {текущие}, "
                           "хотя раздел для этой страницы не назначен")

        есть_корзина = "cart-toggle" in шапка
        должна = нужна_корзина(rel, данные.get("cart_on", []))
        if есть_корзина and not должна:
            дефекты.append(f"{rel}: корзина в шапке, хотя не объявлена")
        if должна and not есть_корзина:
            дефекты.append(f"{rel}: корзины нет, хотя объявлена")

    if дефекты:
        print(f"Шапка: расхождений {len(дефекты)} на {len(список)} страницах")
        for строка in дефекты[:40]:
            print(f"  · {строка}")
        if len(дефекты) > 40:
            print(f"  … и ещё {len(дефекты) - 40}")
        return 1

    print(f"Шапка: {len(список)} страниц, вариант один, расхождений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
