#!/usr/bin/env python3
"""Проверка сайта на большом экране: настоящий рендер, а не чтение CSS.

Появилась 15.08.2026. До неё замер был только телефонный
(`check_mobile.py`), и это прямо объясняет, почему дефекты десктопа никто
не ловил: страница, которая на 390px ведёт себя правильно, на 1920px может
и переполняться вбок, и растягиваться на два десятка экранов — ни одну из
этих поломок телефонная проверка не видит по устройству.

Проверяется на четырёх ширинах — 1366, 1440, 1600, 1920. Это не «популярные
разрешения вообще», а разные режимы вёрстки сайта: 1366 и 1440 в ветке
1100+, 1600 — сама граница `desktop-wide.css`, 1920 выше обеих. Ширина, не
меняющая ни одной ветки CSS, ничего бы не проверяла.

Граница проверяется отдельно от того, что за ней: дефект широкого монитора
16.08.2026 включался ровно на 1600, а в списке стояли 1440 и 1920 — то есть
сама точка переключения не бралась ни разу.

  1. страница не уходит в горизонтальную прокрутку;
  2. ни один элемент не вылезает за свой контейнер — карточка, у которой
     текст выходит за рамку, ловится здесь, а не глазами;
  3. страница не длиннее своего порога высоты: длина главной это её
     структура, и мерить её надо числом, а не ощущением;
  4. сетка не оставляет рваного хвоста: в ряду из N колонок последний ряд
     не должен содержать одну карточку, когда всего их больше двух;
  5. главная кнопка первого экрана видна без прокрутки.

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
# 1600 добавлена 16.08.2026: ровно на этой границе жил дефект широкого
# монитора (кегль заголовка ступенькой при упёршейся колонке), а в списке
# стояли 1440 и 1920 — то есть сама граница не проверялась ни разу.
WIDTHS = [(1366, 768), (1440, 900), (1600, 900), (1920, 1080)]

# Допуск на субпиксель: рендер даёт дробные ширины, и расхождение в
# полпикселя — округление, а не переполнение.
OVERFLOW_TOLERANCE = 1.0

# Длина страницы в пикселях, а не в экранах. Экран — мера подвижная: одна
# и та же страница даёт 13,0 экрана на 768px высоты и 9,2 на 1080, и порог
# в экранах наказывал бы за низкий монитор, а не за длинную страницу.
#
# Замеры 15.08.2026 по главной: 25 475px до переработки (весь каталог на
# главной), 14 380px после переноса каталога, 9 956px после снятия повторов
# и правки ритма, 9 190px после переноса лестницы этапов в первый экран.
# Порог 9 800px ловит возврат отросшего блока, оставляя запас на правку
# текста. В экранах это 8,5 на 1920×1080 — цель владельца была 7–9.
#
# Структура главной — десять блоков примерно по экрану каждый; порог
# соответствует ей, а не выбран круглым числом.
HEIGHT_MAX = {"index.html": 9_800}

# Второй показатель — число экранов, и он нужен рядом с пикселями, а не
# вместо них. Пиксельный порог не наказывает за низкий монитор, но и не
# показывает, сколько человек реально прокрутит: 9 500px это 8,8 экрана
# на 1920×1080 и 12,4 на 1366×768. Замер 15.08.2026.
#
# Порог пока предупреждающий, а не блокирующий: цель ≤10 экранов на 1366
# не достигнута (12,4), и делать проверку красной до того, как длина
# сокращена, значит красить гейт на известном и незакрытом.
SCREENS_TARGET = {"index.html": 10.0}

# Главная кнопка первого экрана — та, ради которой экран и существует.
# Селектор, а не «первая кнопка на странице»: первой в разметке идёт
# кнопка корзины в шапке, и проверка по ней всегда была бы зелёной.
CTA_SELECTORS = {"index.html": ".hero-actions .button"}

# Первый экран страницы товара. Требование спринта 15.08.2026: в первых
# 1–1.5 экранах покупатель видит ситуацию, результат, «кому подойдёт»,
# «когда применять», цену и одну кнопку покупки.
#
# Замер до правки: низ блока «когда применять / кому подойдёт» стоял на
# 1,60–1,80 экрана при 1366×768, то есть за пределом, а кнопка покупки на
# двух страницах — на 0,95 экрана, на волосок от сгиба. Причина не в самом
# блоке: заголовок товара занимал до 256px четырьмя строками по 63px, а
# декоративная картинка 4/3 — ещё 441px. Оба числа получены рендером;
# чтением разметки их не видно.
#
# Порог держит возврат этой картины. Он в долях экрана, а не в пикселях,
# потому что здесь вопрос ровно про сгиб: «видно ли без прокрутки».
PRODUCT_FIT_SCREENS = 1.5
PRODUCT_BUY_SCREENS = 1.0

SAMPLE = [
    "index.html",
    "katalog.html",
    "articles/garantiynoe-uderzhanie-chto-eto.html",
    "materialy/uderzhaniya.html",
    "articles/index.html",
    "materialy/index.html",
    "kalkulyator.html",
    "diagnostika.html",
] + sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "products").glob("*.html"))

SKIP = {"test-pokupka.html", "success.html", "fail.html"}

# `data/` — не сайт. Туда правовой контур складывает снятые страницы
# источников: чужая вёрстка девяностых на таблицах, `nobr` и фиксированных
# ширинах. Замер 16.08.2026: `--all` давал 733 расхождения, из них 731 на
# `data/legal/fixtures/pages` и 2 — замечания по длине главной. Режим,
# который на каждый прогон печатает семь сотен строк про чужие страницы,
# не читают вовсе, и настоящая находка в нём тонет. Ровно этим он и был
# бесполезен: дефект каталога при 1920px в этом выводе никто бы не нашёл,
# даже если бы проверка умела его видеть.
SKIP_DIRS = ("content/", ".claude/", "data/")


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


# Разрыв внутри слова. Класс дефектов, который проверка не видела вовсе:
# прогон 16.08.2026 на katalog.html при 1920px давал «расхождений нет», а
# на экране стояло «неотработанны/й остаток» и «субподрядчико/м».
#
# Почему не видела. Все прежние показатели — про коробки: ушла ли страница
# вбок, торчит ли содержимое, сирота ли в хвосте сетки. Здесь коробки
# целы: заголовок ровно в колонке, колонка ровно в сетке, переполнения
# нет. Дефект в том, ЧТО браузер сделал, чтобы переполнения не случилось, —
# `overflow-wrap:break-word` разрезал слово посередине. Проверка мерила
# следствие, которого не было, вместо причины, которая была.
#
# Меряется без порога, и это важно: «колонка уже 400px» было бы числом из
# головы. Слово либо помещается в строку, либо нет. Ширина слова считается
# тем же шрифтом, что и у самого заголовка, — скрытым span с `white-space:
# pre`, — и сравнивается с шириной содержимого строки.
#
# Мягкий перенос и неразрывный пробел в расчёт не идут: `­` даёт
# перенос по замыслу автора, а не по нехватке места.
WORDBREAK_SCRIPT = """() => {
  const out = [];
  const meas = document.createElement('span');
  document.body.appendChild(meas);
  const label = el => {
    const id = el.id ? '#' + el.id : '';
    const cls = (typeof el.className === 'string' && el.className)
      ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls;
  };
  for (const el of document.querySelectorAll('h1, h2, h3, h4, .button, .product-number')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (cs.overflowWrap !== 'break-word' && cs.overflowWrap !== 'anywhere'
        && cs.wordBreak !== 'break-all' && cs.wordBreak !== 'break-word') continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const avail = el.clientWidth
      - parseFloat(cs.paddingLeft || 0) - parseFloat(cs.paddingRight || 0);
    if (!(avail > 0)) continue;
    meas.style.cssText = 'position:absolute;visibility:hidden;white-space:pre;'
      + 'font:' + cs.font + ';letter-spacing:' + cs.letterSpacing;
    for (const word of (el.textContent || '').split(/[\\s\\u00a0\\u00ad]+/)) {
      if (!word) continue;
      meas.textContent = word;
      const w = meas.getBoundingClientRect().width;
      if (w > avail + 0.5) {
        out.push(label(el) + ': слово «' + word + '» ' + Math.round(w)
                 + 'px не влезает в строку ' + Math.round(avail)
                 + 'px и рвётся посередине (кегль ' + cs.fontSize + ')');
        break;
      }
    }
  }
  meas.remove();
  return out.slice(0, 8);
}"""

# Разрыв слова по факту раскладки, а не по предсказанию.
#
# WORDBREAK_SCRIPT выше считает, влезет ли слово в строку, и смотрит только
# заголовки, кнопки и рубрику. Этого мало по двум причинам, и обе замерены
# 16.08.2026 на katalog.html: перечень файлов внутри карточки — это `li`, в
# список селекторов он не входил вовсе; а предсказание по ширине шрифта не
# знает, где реально встал перенос строки.
#
# Здесь мерится результат: диапазон, покрывающий слово, отдаёт несколько
# прямоугольников на разной высоте только тогда, когда слово разложено на
# две строки. Порога нет — слово либо разорвано, либо нет.
#
# Дефис в состав слова НЕ входит, и это не мелочь. Первая редакция включала
# его и дала шесть ложных срабатываний на «чек-листу» и «из-за»: перенос по
# настоящему дефису — нормальная типографика, а не дефект. Мягкий перенос
# (U+00AD) в составе оставлен: разрыв по нему — это уже искусственная
# расстановка переносов, то есть ровно то, что ищем.
REALBREAK_SCRIPT = """() => {
  // Область — карточки, а не вся страница. Первая редакция откатывалась на
  // document.body там, где витрины нет, и строила диапазон на каждое слово
  // разбора: на длинной статье это тысячи вызовов getClientRects, шаг
  // прогона рос минутами. Заодно проверка уходила за свою тему — «из-за» в
  // тексте товара к вёрстке каталога отношения не имеет.
  const grids = document.querySelectorAll('.product-grid');
  const roots = grids.length ? [...grids]
                            : [...document.querySelectorAll('.product-card')];
  if (!roots.length) return [];
  const out = [];
  for (const root of roots) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const text = node.nodeValue;
      if (!text || !text.trim()) continue;
      const cs = getComputedStyle(node.parentElement);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const re = /[\\p{L}\\p{N}][\\p{L}\\p{N}\\u00ad]*/gu;
      let m;
      while ((m = re.exec(text))) {
        const word = m[0];
        if (word.length < 4) continue;
        const r = document.createRange();
        r.setStart(node, m.index);
        r.setEnd(node, m.index + word.length);
        const rects = [...r.getClientRects()].filter(x => x.width && x.height);
        if (rects.length < 2) continue;
        // Строки считаются по пересечению по вертикали, а не по равенству
        // `top`. Замер на раннере 16.08.2026: сравнение округлённых `top`
        // объявило разорванным слово «работ» на index.html при 1366 и 1440,
        // хотя оно стоит одной строкой. Один диапазон отдаёт несколько
        // прямоугольников и внутри строки — на границе шрифтового отката
        // кириллицы, — и у них `top` расходится на доли пикселя. Локально
        // шрифты другие, и прогон был зелёным: разошлись среды, а не вёрстка.
        //
        // Настоящий перенос даёт прямоугольники, не пересекающиеся по
        // вертикали вовсе. Поэтому новая строка засчитывается, только если
        // перекрытие с уже найденными меньше половины высоты.
        const lines = [];
        for (const x of rects) {
          const same = lines.some(l => {
            const overlap = Math.min(l.bottom, x.bottom) - Math.max(l.top, x.top);
            return overlap > Math.min(l.height, x.height) * 0.5;
          });
          if (!same) lines.push(x);
        }
        if (lines.length < 2) continue;
        const el = node.parentElement;
        out.push('слово «' + word + '» разорвано между строками в '
                 + el.tagName.toLowerCase()
                 + (el.className ? '.' + String(el.className).split(/\\s+/)[0] : ''));
        if (out.length >= 8) return out;
      }
    }
  }
  return out;
}"""

# Карточка каталога: содержимое на одной внутренней сетке, цена внутри
# коробки.
#
# Замер 16.08.2026: дефект первой карточки описывался как «текст и цена
# прижаты к левому краю». Проверять его сравнением `padding` недостаточно —
# padding может совпадать, а отрицательный margin, transform или вылет
# строки всё равно вынесут содержимое за границу. Поэтому меряется
# фактическое расстояние от левого края карточки до каждого её блока, и
# первая карточка сравнивается с соседними: расхождение больше пикселя
# означает, что к ней применилось правило, не применившееся к остальным.
CARDBOX_SCRIPT = """() => {
  const cards = [...document.querySelectorAll('.product-grid-inner .product-card')];
  if (cards.length < 2) return [];
  const out = [];
  const offsets = card => {
    const cr = card.getBoundingClientRect();
    const kids = ['.product-number', 'h3', 'p', 'ul', '.product-footer strong',
                  '.product-footer .button'];
    const o = {};
    for (const sel of kids) {
      const el = card.querySelector(sel);
      if (el) o[sel] = +(el.getBoundingClientRect().left - cr.left).toFixed(1);
    }
    return o;
  };
  const base = offsets(cards[1]);
  const first = offsets(cards[0]);
  for (const sel of Object.keys(first)) {
    if (!(sel in base)) continue;
    if (Math.abs(first[sel] - base[sel]) > 1) {
      out.push('первая карточка: ' + sel + ' отступ слева ' + first[sel]
               + 'px против ' + base[sel] + 'px у соседней');
    }
  }
  cards.forEach((card, i) => {
    const cr = card.getBoundingClientRect();
    for (const sel of ['.product-footer strong', '.product-footer .button']) {
      const el = card.querySelector(sel);
      if (!el) continue;
      const r = el.getBoundingClientRect();
      if (r.left < cr.left - 0.5 || r.right > cr.right + 0.5) {
        out.push('карточка ' + (i + 1) + ': ' + sel + ' выходит за границу — '
                 + Math.round(r.left) + '..' + Math.round(r.right)
                 + ' против ' + Math.round(cr.left) + '..' + Math.round(cr.right));
      }
    }
  });
  return out.slice(0, 8);
}"""


def first_screen(page, height: int) -> list[str]:
    """Что видно на странице товара до прокрутки.

    Отсутствие блока — тоже дефект, и он назван отдельно от «низ слишком
    низко»: пустой селектор молча даёт ноль, а ноль читается как «всё
    хорошо». Ровно так теряются цели Метрики, и здесь ошибка была бы та же.
    """
    out = []
    box = page.evaluate(
        """() => {
          const at = sel => {
            const el = document.querySelector(sel);
            return el ? Math.round(el.getBoundingClientRect().bottom + scrollY) : null;
          };
          return {fit: at('.product-fit'), buy: at('.add-to-cart'),
                  price: at('.price')};
        }""")
    for name, key, limit, human in (
            ("«когда применять / кому подойдёт»", "fit", PRODUCT_FIT_SCREENS,
             ".product-fit"),
            ("кнопка покупки", "buy", PRODUCT_BUY_SCREENS, ".add-to-cart"),
            ("цена", "price", PRODUCT_BUY_SCREENS, ".price")):
        bottom = box[key]
        if bottom is None:
            out.append(f"{name} не найдена по {human}")
            continue
        screens = bottom / height
        if screens > limit:
            out.append(f"{name}: низ на {bottom}px — {screens:.2f} экрана "
                       f"при пороге {limit}")
    return out


def check_page(browser, base: str, rel: str,
               notes: list[str]) -> list[str]:
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

            for item in page.evaluate(WORDBREAK_SCRIPT):
                bad.append(f"{rel} @{width}: {item}")

            for item in page.evaluate(REALBREAK_SCRIPT):
                bad.append(f"{rel} @{width}: {item}")

            for item in page.evaluate(CARDBOX_SCRIPT):
                bad.append(f"{rel} @{width}: {item}")

            # Главная кнопка первого экрана. Замер 15.08.2026: заголовок
            # главной при 95–101px занимал 528–563px, и низ кнопки
            # «Выбрать свою ситуацию» оказывался на 929px при экране 768 и
            # на 957 при 900 — то есть на двух самых частых десктопных
            # высотах призыв не был виден без прокрутки. Дефект не виден ни
            # переполнением, ни длиной: страница правильная, кнопка просто
            # ниже сгиба.
            if rel in CTA_SELECTORS:
                bottom = page.evaluate(
                    "(sel) => { const el = document.querySelector(sel);"
                    " return el ? Math.round(el.getBoundingClientRect().bottom) : null; }",
                    CTA_SELECTORS[rel])
                if bottom is None:
                    bad.append(f"{rel} @{width}: главная кнопка не найдена "
                               f"по {CTA_SELECTORS[rel]}")
                elif bottom > height:
                    bad.append(f"{rel} @{width}: главная кнопка ниже сгиба — "
                               f"низ на {bottom}px при экране {height}px")

            target = SCREENS_TARGET.get(rel)
            if target is not None:
                doc_height = page.evaluate("document.documentElement.scrollHeight")
                screens = doc_height / height
                if screens > target:
                    notes.append(f"{rel} @{width}: {screens:.1f} экрана против цели "
                                 f"{target} — {doc_height}px при окне {height}px")

            if rel.startswith("products/"):
                bad.extend(f"{rel} @{width}: {item}"
                           for item in first_screen(page, height))

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
    notes: list[str] = []
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
                    bad.extend(check_page(browser, base, rel, notes))
            finally:
                browser.close()
    finally:
        httpd.shutdown()

    if notes:
        print("Замечание — длина в экранах выше цели (не блокирует):")
        for line in notes:
            print(f"   · {line}")

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
