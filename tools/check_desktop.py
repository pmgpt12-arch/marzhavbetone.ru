#!/usr/bin/env python3
"""Проверка сайта на большом экране: настоящий рендер, а не чтение CSS.

Появилась 15.08.2026. До неё замер был только телефонный
(`check_mobile.py`), и это прямо объясняет, почему дефекты десктопа никто
не ловил: страница, которая на 390px ведёт себя правильно, на 1920px может
и переполняться вбок, и растягиваться на два десятка экранов — ни одну из
этих поломок телефонная проверка не видит по устройству.

Проверяется на трёх ширинах — 1366, 1440, 1920. Это не «популярные
разрешения вообще», а три разных режима вёрстки сайта: 1366 ниже
брейкпоинта 1600, 1440 между 1100 и 1600, 1920 выше обоих. Ширина, не
меняющая ни одной ветки CSS, ничего бы не проверяла.

  1. страница не уходит в горизонтальную прокрутку;
  2. ни один элемент не вылезает за свой контейнер — карточка, у которой
     текст выходит за рамку, ловится здесь, а не глазами;
  3. страница не длиннее своего порога высоты: длина главной это её
     структура, и мерить её надо числом, а не ощущением;
  4. сетка не оставляет рваного хвоста: в ряду из N колонок последний ряд
     не должен содержать одну карточку, когда всего их больше двух.

Порог длины намеренно стоит только на главной: у разбора длина это его
содержание, и ограничивать её нечем.

Запуск:
    python3 tools/check_desktop.py            # выборка страниц каждого типа
    python3 tools/check_desktop.py --all      # все страницы сайта

Нужен playwright с хромиумом. Без него проверка не «прошла», а
«не запускалась» — и говорит об этом прямо, кодом возврата 2.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Три ширины — три разные ветки CSS сайта, а не три популярных монитора.
# Брейкпоинты на 15.08.2026: 1100 (desktop.css), 1600 (desktop-wide.css),
# 1700 (desktop.css). 1366 берёт ветку 1100+, 1440 её же с другим запасом
# по ширине контейнера, 1920 — обе широкие.
WIDTHS = [(1366, 768), (1440, 900), (1920, 1080)]

# Допуск на субпиксель: рендер даёт дробные ширины, и расхождение в
# полпикселя — округление, а не переполнение.
OVERFLOW_TOLERANCE = 1.0

# Длина страницы в пикселях, а не в экранах. Экран — мера подвижная: одна
# и та же страница даёт 13,0 экрана на 768px высоты и 9,2 на 1080, и порог
# в экранах наказывал бы за низкий монитор, а не за длинную страницу.
#
# Замеры 15.08.2026 по главной: 25 475px до переработки (весь каталог на
# главной), 14 380px после переноса каталога, 9 956px после снятия повторов
# и правки ритма. Порог 10 500px ловит возврат отросшего блока, оставляя
# запас на правку текста. В экранах это 9,2 на 1920×1080.
#
# Структура главной — десять блоков примерно по экрану каждый; порог
# соответствует ей, а не выбран круглым числом.
HEIGHT_MAX = {"index.html": 10_500}

SAMPLE = [
    "index.html",
    "katalog.html",
    "articles/garantiynoe-uderzhanie-chto-eto.html",
    "products/p1-oplata-po-ks2.html",
    "materialy/uderzhaniya.html",
    "articles/index.html",
    "materialy/index.html",
    "kalkulyator.html",
    "diagnostika.html",
]

SKIP = {"test-pokupka.html", "success.html", "fail.html"}
SKIP_DIRS = ("content/", ".claude/")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve() -> tuple[socketserver.TCPServer, int]:
    """Отдаёт сайт по http: ассеты подключены абсолютными путями, и по file://
    они не грузятся — под file:// проверка молча прошла бы на пустой странице."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    port = free_port()
    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def chromium_nearby() -> Path | None:
    """Хромиум, поставленный окружением, а не playwright'ом."""
    import os

    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if not root.is_dir():
        return None
    for candidate in sorted(root.glob("chromium-*/chrome-linux/chrome"), reverse=True):
        if candidate.exists():
            return candidate
    return None


def pages(all_pages: bool) -> list[str]:
    if not all_pages:
        return SAMPLE
    out = []
    for path in sorted(ROOT.glob("**/*.html")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(SKIP_DIRS) or path.name in SKIP:
            continue
        out.append(rel)
    return out


# Переполнение ищется двумя разными способами, потому что это два разных
# дефекта и один другого не ловит.
#
# Первый — элемент шире собственной прокрутки (scrollWidth > clientWidth).
# Так выглядит длинное слово в узкой колонке: коробка на месте, текст из
# неё торчит.
#
# Второй — правый край ребёнка правее правого края родителя. Так выглядит
# сетка, которую распёрла колонка с неразрывным содержимым: сама коробка
# уехала, и первый способ про неё молчит, потому что внутри неё всё
# помещается.
#
# Служебные исключения: намеренно прокручиваемые вбок элементы
# (overflow-x: auto/scroll) и то, что скрыто.
OVERFLOW_SCRIPT = """(tol) => {
  const out = [];
  const label = el => {
    const id = el.id ? '#' + el.id : '';
    const cls = (typeof el.className === 'string' && el.className)
      ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls;
  };
  const scrollable = el => {
    const cs = getComputedStyle(el);
    return cs.overflowX === 'auto' || cs.overflowX === 'scroll'
        || cs.overflow === 'auto' || cs.overflow === 'scroll';
  };
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;

    if (!scrollable(el) && el.scrollWidth - el.clientWidth > tol && el.clientWidth > 0) {
      out.push(label(el) + ': содержимое шире коробки на '
               + Math.round(el.scrollWidth - el.clientWidth) + 'px');
      continue;
    }
    const parent = el.parentElement;
    if (!parent || parent === document.body) continue;
    if (scrollable(parent)) continue;
    const pcs = getComputedStyle(parent);
    if (pcs.overflow === 'hidden' || pcs.overflowX === 'hidden') continue;
    if (cs.position === 'absolute' || cs.position === 'fixed') continue;
    const pr = parent.getBoundingClientRect();
    if (!pr.width) continue;
    const spill = Math.max(r.right - pr.right, pr.left - r.left);
    if (spill > tol) {
      out.push(label(el) + ' вылезает из ' + label(parent)
               + ' на ' + Math.round(spill) + 'px');
    }
  }
  return out.slice(0, 12);
}"""


# Рваный хвост сетки. Замер 15.08.2026: шесть карточек ситуаций стояли в
# сетке из четырёх колонок и давали ряд 4 + ряд 2 — две сироты во втором
# ряду. Дефект видно глазами на любом широком экране, но ни одна текстовая
# проверка его не ловит: разметка правильная, переполнения нет.
#
# Считается по фактическим координатам, а не по CSS: колонок в ряду —
# сколько разных левых краёв у детей, сирот — сколько детей в последнем
# ряду. Одна сирота при трёх и более колонках это дефект; два ряда по
# половине — нет.
#
# Сетка групп каталога (`.product-grid-inner`) сюда намеренно не входит.
# Размер группы — это состав каталога, а он решение владельца (Р-006):
# в группе «До подписания» четыре комплекта, и в трёх колонках они дают
# 3 + 1. Подогнать ряд можно только добавив или убрав товар, то есть
# приняв за владельца решение о составе. Прогон 15.08.2026 эту сироту
# нашёл — она названа здесь, а не спрятана.
ORPHAN_SCRIPT = """(tol) => {
  const out = [];
  for (const grid of document.querySelectorAll('.topic-grid, .cards, .case-grid, .solution-grid')) {
    const kids = [...grid.children].filter(k => {
      const cs = getComputedStyle(k);
      return cs.display !== 'none' && k.getBoundingClientRect().width > 0;
    });
    if (kids.length < 3) continue;
    const lefts = [...new Set(kids.map(k => Math.round(k.getBoundingClientRect().left)))];
    const columns = lefts.length;
    if (columns < 3) continue;
    const orphans = kids.length % columns;
    if (orphans === 1) {
      const cls = (typeof grid.className === 'string' ? grid.className : '').trim().split(/\\s+/)[0];
      out.push('.' + cls + ': ' + kids.length + ' карточек в ' + columns
               + ' колонки — одна сирота в последнем ряду');
    }
  }
  return out;
}"""


def check_page(browser, base: str, rel: str) -> list[str]:
    bad: list[str] = []
    for width, height in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": height})
        try:
            page.goto(f"{base}/{rel}", wait_until="load")
            page.wait_for_timeout(250)

            doc_width = page.evaluate("document.documentElement.scrollWidth")
            if doc_width - width > OVERFLOW_TOLERANCE:
                bad.append(f"{rel} @{width}: страница уходит вбок — "
                           f"{doc_width}px против {width}px")

            for item in page.evaluate(OVERFLOW_SCRIPT, OVERFLOW_TOLERANCE):
                bad.append(f"{rel} @{width}: {item}")

            for item in page.evaluate(ORPHAN_SCRIPT, OVERFLOW_TOLERANCE):
                bad.append(f"{rel} @{width}: {item}")

            limit = HEIGHT_MAX.get(rel)
            if limit is not None:
                doc_height = page.evaluate("document.documentElement.scrollHeight")
                if doc_height > limit:
                    bad.append(f"{rel} @{width}: страница длиной {doc_height}px "
                               f"против {limit} — {doc_height / height:.1f} экрана")
        finally:
            page.close()
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="все страницы, а не выборка")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Проверка не запускалась: нет playwright. "
              "Установка: pip install playwright", file=sys.stderr)
        return 2

    httpd, port = serve()
    base = f"http://127.0.0.1:{port}"
    targets = pages(args.all)
    bad: list[str] = []
    try:
        with sync_playwright() as p:
            near = chromium_nearby()
            try:
                browser = (p.chromium.launch(executable_path=str(near)) if near
                           else p.chromium.launch())
            except Exception as exc:
                print(f"Проверка не запускалась: браузер не стартовал — {exc}",
                      file=sys.stderr)
                return 2
            try:
                for rel in targets:
                    bad.extend(check_page(browser, base, rel))
            finally:
                browser.close()
    finally:
        httpd.shutdown()

    widths = ", ".join(str(w) for w, _ in WIDTHS)
    if bad:
        print(f"Десктоп ({widths}): расхождений {len(bad)} на {len(targets)} страницах")
        for line in bad:
            print(f"  · {line}")
        return 1
    print(f"Десктоп ({widths}): {len(targets)} страниц, расхождений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
