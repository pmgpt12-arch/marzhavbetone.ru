#!/usr/bin/env python3
"""Проверка сайта на телефоне: настоящий рендер, а не чтение CSS.

Появилась 11.08.2026 после двух дефектов, которых не видно ни в одном
текстовом замере:

  · до 900px навигация пряталась и ничем не заменялась — на телефоне у сайта
    не было меню вовсе, а читатель из Дзена приходит именно с телефона;
  · таблица разбора шире экрана растягивала страницу на 12px, и весь текст
    ездил вбок.

Оба нашлись только рендером. Поэтому проверка ходит браузером, а не грепом.

Проверяется на ширине 390px (iPhone 12/13/14 — самая распространённая):
  1. кнопка меню есть, видна и не меньше 44×44;
  2. меню закрыто до нажатия, раскрывается и закрывается;
  3. страница не уходит в горизонтальную прокрутку и не съезжает после
     загрузки (CLS), а весит не больше порога;
  3a. ни одна картинка не растянута: пропорция рендера совпадает с
     исходной, кроме тех, что режет object-fit: cover;
  4. пункты меню не ниже 44px — иначе по ним промахиваются пальцем;
  5. на 1440px меню осталось прежним, а кнопка не появилась.

Запуск:
    python3 tools/check_mobile.py            # выборка страниц каждого типа
    python3 tools/check_mobile.py --all      # все страницы сайта

Нужен playwright с хромиумом. Без него проверка не «прошла», а
«не запускалась» — и говорит об этом прямо, кодом возврата 2.

Граница проверки названа прямо: встроенный сервер отдаёт файлы как есть, то
есть `app-script.php` приходит исходником, а не javascript'ом. Всё, что
делает `app.js` — корзина, формы, — здесь не проверяется. Меню и ширина
страницы проверяются полностью: они держатся на CSS и attribution.js.
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
WIDTH_PHONE = 390
HEIGHT_PHONE = 844
TAP_MIN = 44  # минимальная площадь нажатия
# «Хорошо» по Core Web Vitals — CLS ниже 0,1. Порог вдвое строже: сдвиг ниже
# 0,05 на этих страницах достижим, замер 11.08.2026 даёт ноль.
CLS_MAX = 0.05
# Вес страницы целиком. Замер 11.08.2026 после сжатия картинок: 257–325 КБ.
# Порог оставлен с запасом, чтобы ловить возврат мегабайтной обложки, а не
# каждую новую картинку.
WEIGHT_MAX = 800_000
# Липкая шапка на телефоне съедает высоту у каждого экрана. Замер 11.08.2026:
# кнопка меню не помещалась в строку и шапка разбора занимала 103px из 844;
# после ужатия логотипа и призыва — 69px. Порог ловит возврат переноса.
HEADER_MAX = 90
# Картинка обязана держать свою пропорцию. Замер 11.08.2026: атрибуты
# width/height, проставленные ради устойчивой вёрстки, сами стали высотой
# там, где в CSS не было height:auto, — карточки рендерились 346×954 вместо
# 346×260. Ни один текстовый замер этого не видел, проверка веса и
# прокрутки тоже: страница не переполнялась, картинка просто была
# растянута. Допуск 5% — на округление.
RATIO_TOLERANCE = 0.05

MENU_SELECTOR = "nav[aria-label='Основная навигация'], nav.links"

# Выборка: по одной странице каждого шаблона. Витрина материалов добавлена
# отдельно от страниц раздела: у неё семь секций подряд, и растяжка
# карточки на телефоне видна только на ней. Дефект шапки в одном шаблоне
# шапки в одном из них не виден на остальных — так и нашёлся дефект статьи.
SAMPLE = [
    "index.html",
    "katalog.html",
    "articles/garantiynoe-uderzhanie-chto-eto.html",
    "products/p1-oplata-po-ks2.html",
    "materialy/uderzhaniya.html",
    "articles/index.html",
    "materialy/index.html",
    "kalkulyator.html",
]

SKIP = {"test-pokupka.html", "success.html", "fail.html"}
# .claude/worktrees — рабочие копии исполнителей: это чужие деревья того же
# репозитория, и проверять их значит мерить одну страницу дважды.
SKIP_DIRS = ("content/", ".claude/")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve() -> tuple[socketserver.TCPServer, int]:
    """Отдаёт сайт по http: ассеты подключены абсолютными путями, и по file://
    они не грузятся — под file:// проверка молча прошла бы на пустой странице."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # обращения к файлам не нужны в выводе
            pass

    port = free_port()
    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def chromium_nearby() -> Path | None:
    """Хромиум, поставленный окружением, а не playwright'ом."""
    import os

    roots = [Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))]
    for root in roots:
        if not root.is_dir():
            continue
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


CLS_SCRIPT = """() => new Promise(resolve => {
  let value = 0;
  new PerformanceObserver(list => {
    for (const entry of list.getEntries()) if (!entry.hadRecentInput) value += entry.value;
  }).observe({type: 'layout-shift', buffered: true});
  setTimeout(() => resolve(value), 400);
})"""


def check_page(browser, base: str, rel: str) -> list[str]:
    bad: list[str] = []
    page = browser.new_page(viewport={"width": WIDTH_PHONE, "height": HEIGHT_PHONE})
    weight = {"bytes": 0}

    def count(response):
        try:
            weight["bytes"] += len(response.body())
        except Exception:
            pass  # редирект или отменённый запрос тела не имеет

    page.on("response", count)
    try:
        page.goto(f"{base}/{rel}", wait_until="load")
        page.wait_for_timeout(250)

        shift = page.evaluate(CLS_SCRIPT)
        if shift > CLS_MAX:
            bad.append(f"{rel}: вёрстка съезжает после загрузки, CLS {shift:.3f} против {CLS_MAX}")

        if weight["bytes"] > WEIGHT_MAX:
            bad.append(f"{rel}: страница весит {weight['bytes'] / 1024:.0f} КБ "
                       f"против {WEIGHT_MAX // 1024} КБ")

        # Два разных дефекта, и первый я сам же и внёс.
        #
        # Первый: в CSS объявлена aspect-ratio, а картинка её не держит.
        # Так ломается коробка при object-fit: cover — сама картинка не
        # растягивается, она кадрируется, поэтому сверка с исходной
        # пропорцией тут молчит. Замер 11.08.2026: карточки рендерились
        # 346×954 вместо 346×260, потому что атрибут height стал высотой.
        #
        # Второй: пропорция рендера разошлась с исходной там, где картинку
        # никто не режет, — это и есть растянутая картинка.
        broken = page.evaluate("""() => {
            const out = [];
            for (const i of document.images) {
                if (!i.naturalWidth) continue;
                const cs = getComputedStyle(i), r = i.getBoundingClientRect();
                if (!r.height || !r.width) continue;
                const shown = r.width / r.height;
                const declared = cs.aspectRatio && cs.aspectRatio !== 'auto'
                    ? cs.aspectRatio.split('/').map(Number) : null;
                const src = i.currentSrc.split('/').pop();
                if (declared && declared.length === 2 && declared[1]) {
                    const want = declared[0] / declared[1];
                    if (Math.abs(shown - want) / want > %(tol)s) {
                        out.push(src + ': коробка ' + Math.round(r.width) + '×' +
                                 Math.round(r.height) + ' против объявленной ' + cs.aspectRatio);
                        continue;
                    }
                }
                if (cs.objectFit === 'cover' || cs.objectFit === 'contain') continue;
                const nat = i.naturalWidth / i.naturalHeight;
                if (Math.abs(shown - nat) / nat > %(tol)s) {
                    out.push(src + ': растянута, ' + shown.toFixed(2) +
                             ' против исходной ' + nat.toFixed(2));
                }
            }
            return out;
        }""" % {"tol": RATIO_TOLERANCE})
        if broken:
            bad.append(f"{rel}: картинки не держат пропорцию — " + "; ".join(broken[:3]))

        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        if overflow > 0:
            wide = page.evaluate(
                """() => {const w=document.documentElement.clientWidth;const out=[];
                   document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();
                     if(r.right>w+0.5) out.push(e.tagName.toLowerCase());});
                   return out.slice(0,3);}""")
            bad.append(f"{rel}: горизонтальная прокрутка {overflow}px, шире экрана: {', '.join(wide) or '?'}")

        menu = page.query_selector(MENU_SELECTOR)
        if menu is None:
            return bad  # страница без шапки с меню — калькулятор, служебные

        header_height = page.evaluate(
            """() => {const h = document.querySelector('.topbar, .article-nav');
               return h ? Math.round(h.getBoundingClientRect().height) : 0;}""")
        if header_height > HEADER_MAX:
            bad.append(f"{rel}: шапка занимает {header_height}px — содержимое не влезло в строку")

        toggle = page.query_selector(".nav-toggle")
        if toggle is None or not toggle.is_visible():
            bad.append(f"{rel}: кнопки меню нет или она невидима на {WIDTH_PHONE}px")
            return bad

        box = toggle.bounding_box() or {"width": 0, "height": 0}
        if box["width"] < TAP_MIN or box["height"] < TAP_MIN:
            bad.append(f"{rel}: кнопка меню {box['width']:.0f}×{box['height']:.0f}, нужно {TAP_MIN}×{TAP_MIN}")

        if menu.is_visible():
            bad.append(f"{rel}: меню видно до нажатия")

        toggle.click()
        page.wait_for_timeout(150)
        if not menu.is_visible():
            bad.append(f"{rel}: меню не раскрылось по нажатию")
        else:
            low = [a for a in menu.query_selector_all("a")
                   if (a.bounding_box() or {"height": 0})["height"] < TAP_MIN]
            if low:
                bad.append(f"{rel}: {len(low)} пунктов меню ниже {TAP_MIN}px")
            after = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if after > overflow:
                bad.append(f"{rel}: раскрытое меню добавило прокрутку {after - overflow}px")

        toggle.click()
        page.wait_for_timeout(150)
        if menu.is_visible():
            bad.append(f"{rel}: меню не закрылось повторным нажатием")
    finally:
        page.close()
    return bad


# Ширины, на которых смотрят с телефона. Одной мало: дефект полей карточки
# 16.08.2026 владелец увидел на своём аппарате, а проверка стояла только на
# 390 и его не показывала — не потому, что 390 «хорошая» ширина, а потому
# что мерилась не та карточка.
CARD_WIDTHS = (375, 390, 393, 430)

# Минимальный внутренний зазор карточки. 12px — не «красиво», а граница
# между «поле есть» и «текст лежит на рамке»: сломанные карточки давали
# 0–1px, целые — 20–21px.
CARD_GAP_MIN = 12

# Насколько плавающий блок может заходить на содержимое. Ноль недостижим:
# блок с `position:fixed` по устройству лежит поверх прокручиваемого
# содержимого, и при ширине колонки во весь экран любой видимый блок с ней
# пересекается. Замер 16.08.2026: строка из четырёх значков по центру низа
# перекрывала заголовок и кнопку на 230px, столбец в углу — на 13px, то
# есть попадает в поле карточки, а не в текст. Порог 24px отделяет одно от
# другого.
FLOAT_OVERLAP_MAX = 24

# Карточка — блок с собственным фоном или рамкой, внутри которого есть
# заголовок. Класс не перечисляется: перечень устаревает, а дефект
# 16.08.2026 сидел ровно в той карточке, которой в перечне не было бы.
CARDGAP_SCRIPT = """(minGap) => {
  const bodyBg = getComputedStyle(document.body).backgroundColor;
  const out = [];
  for (const el of document.querySelectorAll('article, section, div, li, aside')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const bg = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== bodyBg;
    const bordered = parseFloat(cs.borderLeftWidth) > 0 && cs.borderLeftStyle !== 'none';
    if (!bg && !bordered) continue;
    const head = el.querySelector(':scope > h2, :scope > h3, :scope > h4');
    if (!head) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 240 || r.height < 120) continue;
    let worst = null;
    for (const kid of el.children) {
      const kr = kid.getBoundingClientRect();
      if (!kr.width || !kr.height) continue;
      const gap = Math.min(kr.left - r.left, r.right - kr.right);
      if (worst === null || gap < worst.gap) {
        worst = {gap, tag: kid.tagName.toLowerCase()
                      + (kid.className ? '.' + String(kid.className).split(/\\s+/)[0] : '')};
      }
    }
    if (worst && worst.gap < minGap) {
      out.push('карточка ' + el.tagName.toLowerCase()
               + (el.className ? '.' + String(el.className).split(/\\s+/)[0] : '')
               + ': поле ' + worst.gap.toFixed(1) + 'px до ' + worst.tag
               + ' (нужно от ' + minGap + ')');
    }
  }
  return out.slice(0, 6);
}"""

# Плавающие блоки против того, ради чего страница существует: цена и кнопка.
FLOATHIT_SCRIPT = """(maxOverlap) => {
  const floats = [...document.querySelectorAll('body *')].filter(el => {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed') return false;
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.top < innerHeight && r.bottom > 0;
  });
  const targets = [...document.querySelectorAll(
    '.product-footer strong, .product-footer .button, .product-footer .add-to-cart,'
    + ' .product-card h3, .solution-card h3')];
  const out = [];
  for (const f of floats) {
    const fr = f.getBoundingClientRect();
    for (const t of targets) {
      const tr = t.getBoundingClientRect();
      if (tr.bottom < 0 || tr.top > innerHeight) continue;
      const ox = Math.min(fr.right, tr.right) - Math.max(fr.left, tr.left);
      const oy = Math.min(fr.bottom, tr.bottom) - Math.max(fr.top, tr.top);
      if (ox > maxOverlap && oy > 2) {
        out.push((f.className ? '.' + String(f.className).split(/\\s+/)[0] : f.tagName)
                 + ' закрывает ' + (t.className ? '.' + String(t.className).split(/\\s+/)[0]
                                                : t.tagName.toLowerCase())
                 + ' «' + (t.textContent || '').trim().slice(0, 22) + '» на '
                 + Math.round(ox) + 'px');
      }
    }
  }
  return out.slice(0, 6);
}"""


def check_cards(browser, base: str, rel: str) -> list[str]:
    """Геометрия карточек и плавающих блоков на четырёх ширинах телефона.

    Меряется рендер, а не объявления в css: дефект 16.08.2026 был именно
    расхождением объявленного с получившимся — `.solution-card` объявляла
    `padding:22px 20px`, а получала `26px 0` от пережившего вёрстку правила
    `.solution-grid article`, у которого специфичность выше.
    """
    bad: list[str] = []
    for width in CARD_WIDTHS:
        context = browser.new_context(
            viewport={"width": width, "height": HEIGHT_PHONE},
            device_scale_factor=3, is_mobile=True, has_touch=True)
        page = context.new_page()
        try:
            page.goto(f"{base}/{rel}", wait_until="load")
            page.wait_for_timeout(250)
            # Одинаковых карточек в сетке несколько, и правило у них общее:
            # шесть одинаковых строк про один дефект читать невозможно.
            for item in dict.fromkeys(page.evaluate(CARDGAP_SCRIPT, CARD_GAP_MIN)):
                bad.append(f"{rel} @{width}: {item}")
            # Прокрутка нужна: плавающий блок стоит на месте, а содержимое
            # под ним меняется, и на первом экране пересечения может не быть.
            for y in (0, 900, 1800, 3000):
                page.evaluate("(y) => window.scrollTo(0, y)", y)
                page.wait_for_timeout(140)
                for item in page.evaluate(FLOATHIT_SCRIPT, FLOAT_OVERLAP_MAX):
                    line = f"{rel} @{width}: {item}"
                    if line not in bad:
                        bad.append(line)
        finally:
            page.close()
            context.close()
    return bad


def check_desktop(browser, base: str) -> list[str]:
    bad: list[str] = []
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    try:
        page.goto(f"{base}/index.html", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        menu = page.query_selector(MENU_SELECTOR)
        if menu is None or not menu.is_visible():
            bad.append("десктоп 1440px: меню пропало")
        toggle = page.query_selector(".nav-toggle")
        if toggle is not None and toggle.is_visible():
            bad.append("десктоп 1440px: кнопка мобильного меню видна")
    finally:
        page.close()
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="все страницы, а не выборка")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright не установлен — проверка НЕ ЗАПУСКАЛАСЬ, а не прошла.")
        print("  pip install playwright && playwright install chromium")
        return 2

    targets = pages(args.all)
    httpd, port = serve()
    base = f"http://127.0.0.1:{port}"
    bad: list[str] = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                # Версия playwright и версия сборки хромиума расходятся, когда
                # браузер поставлен окружением, а не `playwright install`.
                # Тогда берём тот, что лежит рядом, вместо отказа.
                found = chromium_nearby()
                if found is None:
                    print("хромиум не запускается — проверка НЕ ЗАПУСКАЛАСЬ.")
                    print("  playwright install chromium")
                    return 2
                browser = p.chromium.launch(executable_path=str(found))
            for rel in targets:
                bad += check_page(browser, base, rel)
            # Геометрия карточек — там, где карточки есть. Гонять четыре
            # ширины по всем страницам незачем: на разборе карточек нет.
            for rel in ("index.html", "katalog.html", "materialy/index.html"):
                if rel in targets:
                    bad += check_cards(browser, base, rel)
            bad += check_desktop(browser, base)
            browser.close()
    finally:
        httpd.shutdown()

    print(f"Проверено страниц: {len(targets)} на {WIDTH_PHONE}px плюс десктоп.")
    if bad:
        print(f"Расхождений: {len(bad)}")
        for item in bad:
            print("  ·", item)
        return 1
    print("Расхождений нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
