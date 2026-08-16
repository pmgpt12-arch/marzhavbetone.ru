#!/usr/bin/env python3
"""Граф внутренних связей сайта: разборы, товары, кластеры.

Считает шесть фактов, названных в аудите:
  1. сироты среди разборов (не считая витрины articles/index.html)
  2. тупики (нет исходящих ссылок на другие разборы)
  3. товары без входящих ссылок из разборов
  4. разборы без товара (нет article-cta или ведёт в несуществующий файл)
  5. асимметричные пары (A → B, B ↛ A)
  6. распределение по кластерам

Скрипт ничего не правит: он только измеряет. Запуск:
    python3 tools/link_audit.py [--json путь]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://marzhavbetone.ru"
ARTICLES = ROOT / "articles"
PRODUCTS = ROOT / "products"
INDEX = ARTICLES / "index.html"

# Кластеры — измеренные, по ним и группируем. Ключ — файл разбора.
CLUSTERS = {
    "исполнительная документация": [
        "akt-skrytyh-rabot-obrazec.html",
        "akty-skrytyh-rabot-kakie.html",
        "akt-skrytyh-rabot-montazh.html",
        "zos-v-stroitelstve.html",
        "akt-osvidetelstvovaniya-skrytyh-rabot.html",
        "ispolnitelnaya-dokumentaciya-sostav.html",
        "pyat-dokazatelstv-vypolneniya.html",
    ],
    "сметы": [
        "stroitelnaya-smeta-gde-teryaetsya-marzha.html",
        "stroitelnyy-musor-v-smete.html",
        "vsyo-vklyucheno-v-cenu.html",
        "skidka-15-procentov-na-tendere-eto-otbor-zhertv.html",
    ],
    "договор субподряда": [
        "dogovor-subpodryada-obrazec.html",
        "krasnye-flagi-dogovora-subpodryada.html",
        "protokol-raznoglasiy-k-dogovoru.html",
    ],
    "гарантийное удержание": [
        "garantiynoe-uderzhanie-chto-eto.html",
        "garantiynoe-uderzhanie-v-ks-2-i-ks-3.html",
        "srok-garantiynogo-uderzhaniya.html",
        "vozvrat-garantiynogo-uderzhaniya.html",
        "genpodryadchik-zarabatyvaet-na-vas.html",
    ],
    "банкротство и реестр кредиторов": [
        "bankrotstvo-genpodryadchika-5-markerov.html",
        "reestr-trebovaniy-kreditorov.html",
        "vklyuchenie-v-reestr-trebovaniy-kreditorov.html",
        "srok-vklyucheniya-v-reestr-trebovaniy-kreditorov.html",
        "zayavlenie-o-vklyuchenii-v-reestr-trebovaniy.html",
        "zapros-arbitrazhnomu-upravlyayushchemu.html",
    ],
    "аванс": [
        "avans-eto-ne-dengi-eto-kryuchok.html",
        "neotrabotannyy-avans.html",
        "vozvrat-avansa-po-dogovoru-podryada.html",
        "bankovskaya-garantiya-na-vozvrat-avansa.html",
    ],
    "неоплата и закрытие работ": [
        "podpisannaya-ks2-ne-znachit-chto-zaplatyat.html",
        "zakazchik-ne-oplachivaet-vypolnennye-raboty.html",
        "raboty-ne-prinyaty.html",
        "proverka-ks-2-pered-sdachey.html",
    ],
    "допработы": [
        "dopraboty-bez-soglasheniya.html",
        "dopolnitelnye-raboty-v-stroitelstve.html",
    ],
    # Кластер открыт замером 02.08.2026: «акт передачи строительной площадки
    # подрядчику образец» — 308/мес, «акт входного контроля материалов
    # образец» — 124/мес. Пока в нём одна страница, вторая под входной
    # контроль ещё не написана.
    "передача площадки и входной контроль": [
        "akt-peredachi-stroitelnoy-ploshchadki-obrazec.html",
    ],
}


class Page(HTMLParser):
    """Достаёт h1, ссылки и ссылку из блока article-cta."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1: str = ""
        self.links: list[tuple[str, str]] = []  # (href, текст)
        self.cta_hrefs: list[str] = []
        self._in_h1 = False
        self._h1_parts: list[str] = []
        self._a_href: str | None = None
        self._a_parts: list[str] = []
        self._cta_depth = 0
        self._depth = 0
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in ("br", "img", "meta", "link", "hr", "input"):
            self._depth += 1
            classes = (attrs.get("class") or "").split()
            if "article-cta" in classes and self._cta_depth == 0:
                self._cta_depth = self._depth
        if tag == "h1":
            self._in_h1 = True
            self._h1_parts = []
        elif tag == "a":
            self._a_href = attrs.get("href", "")
            self._a_parts = []

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False
            if not self.h1:
                self.h1 = " ".join("".join(self._h1_parts).split())
        elif tag == "a" and self._a_href is not None:
            text = " ".join("".join(self._a_parts).split())
            self.links.append((self._a_href, text))
            if self._cta_depth:
                self.cta_hrefs.append(self._a_href)
            self._a_href = None
        if tag not in ("br", "img", "meta", "link", "hr", "input"):
            if self._cta_depth and self._depth <= self._cta_depth:
                self._cta_depth = 0
            self._depth -= 1

    def handle_data(self, data):
        if self._in_h1:
            self._h1_parts.append(data)
        if self._a_href is not None:
            self._a_parts.append(data)


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def parse(path: Path) -> Page:
    p = Page()
    p.feed(read(path))
    p.close()
    return p


def article_files() -> list[str]:
    return sorted(f.name for f in ARTICLES.glob("*.html") if f.name != "index.html")


def product_skus() -> dict[str, str]:
    """sku → название из products-config.php (истина по перечню товаров)."""
    text = (ROOT / "products-config.php").read_text(encoding="utf-8")
    body = text.split("function mvb_products(): array", 1)[1]
    body = body.split("/** Ищет продукт", 1)[0]
    out = {}
    for m in re.finditer(r"'([a-z0-9]+)'\s*=>\s*\[\s*\n\s*'name'\s*=>\s*'((?:[^']|'')*)'", body):
        out[m.group(1)] = m.group(2).replace("''", "'")
    return out


def product_page_for(sku: str) -> str | None:
    hits = sorted(PRODUCTS.glob(f"{sku}-*.html"))
    return hits[0].name if hits else None


def norm_article(href: str) -> str | None:
    """Ссылка на разбор → имя файла, иначе None."""
    href = href.split("#")[0].split("?")[0]
    if not href.endswith(".html"):
        return None
    for prefix in ("/articles/", "articles/", "./", "../articles/"):
        if href.startswith(prefix):
            name = href[len(prefix):]
            if "/" not in name and (ARTICLES / name).exists() or "/" not in name:
                return name
    if "/" not in href:
        return href
    return None


def norm_product(href: str) -> str | None:
    href = href.split("#")[0].split("?")[0]
    if "/products/" in href and href.endswith(".html"):
        return href.rsplit("/", 1)[1]
    return None


def build():
    files = article_files()
    pages = {f: parse(ARTICLES / f) for f in files}
    titles = {f: pages[f].h1 for f in files}

    # Исходящие ссылки на другие разборы (витрина не считается ни в чём).
    out_links: dict[str, set[str]] = {}
    broken: list[tuple[str, str]] = []
    for f in files:
        targets = set()
        for href, _ in pages[f].links:
            if href.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            name = norm_article(href)
            if name and href.rstrip("/").endswith(".html") and "/products/" not in href:
                if name == "index.html":
                    continue
                if (ARTICLES / name).exists():
                    if name != f:
                        targets.add(name)
                else:
                    broken.append((f, href))
            prod = norm_product(href)
            if prod and not (PRODUCTS / prod).exists():
                broken.append((f, href))
        out_links[f] = targets

    in_links: dict[str, set[str]] = {f: set() for f in files}
    for f, targets in out_links.items():
        for t in targets:
            in_links[t].add(f)

    # Товары
    skus = product_skus()
    catalog = {sku: product_page_for(sku) for sku in skus if sku != "test1"}
    product_in: dict[str, set[str]] = {page: set() for page in catalog.values() if page}
    cta_of: dict[str, list[str]] = {}
    for f in files:
        for href, _ in pages[f].links:
            prod = norm_product(href)
            if prod and prod in product_in:
                product_in[prod].add(f)
        ctas = [norm_product(h) for h in pages[f].cta_hrefs]
        cta_of[f] = [c for c in ctas if c]

    orphans = sorted(f for f in files if not in_links[f])
    dead_ends = sorted(f for f in files if not out_links[f])
    products_no_in = sorted(p for p, s in product_in.items() if not s)
    no_product = sorted(
        f for f in files
        if not cta_of[f] or any(not (PRODUCTS / c).exists() for c in cta_of[f])
    )
    asym = sorted(
        (a, b) for a in files for b in out_links[a] if a not in out_links[b]
    )

    cluster_rows = []
    known = {f for names in CLUSTERS.values() for f in names}
    for name, members in CLUSTERS.items():
        prods = sorted({c for m in members for c in cta_of.get(m, [])})
        cluster_rows.append((name, len(members), members, prods))
    unassigned = sorted(set(files) - known)

    return dict(
        files=files, titles=titles, out_links=out_links, in_links=in_links,
        orphans=orphans, dead_ends=dead_ends, products=catalog,
        product_in=product_in, products_no_in=products_no_in,
        no_product=no_product, cta_of=cta_of, asym=asym,
        cluster_rows=cluster_rows, unassigned=unassigned, broken=broken,
        skus=skus,
    )


def table(headers, rows) -> str:
    cols = [len(h) for h in headers]
    rows = [[str(c) for c in r] for r in rows]
    for r in rows:
        for i, c in enumerate(r):
            cols[i] = max(cols[i], len(c))
    line = "  ".join(h.ljust(cols[i]) for i, h in enumerate(headers))
    out = [line, "  ".join("-" * c for c in cols)]
    for r in rows:
        out.append("  ".join(c.ljust(cols[i]) for i, c in enumerate(r)))
    return "\n".join(out)


def report(g) -> str:
    L = []
    n = len(g["files"])
    L.append(f"Разборов: {n}   товаров в каталоге: {len(g['products'])}"
             f"   (плюс служебная test1, вне каталога)")
    L.append("")

    L.append(f"1. СИРОТЫ — на них не ссылается ни один другой разбор: {len(g['orphans'])}")
    if g["orphans"]:
        L.append(table(["файл", "заголовок"],
                       [(f, g["titles"][f]) for f in g["orphans"]]))
    else:
        L.append("   нет")
    L.append("")

    L.append(f"2. ТУПИКИ — нет исходящих ссылок на другие разборы: {len(g['dead_ends'])}")
    if g["dead_ends"]:
        L.append(table(["файл", "заголовок"],
                       [(f, g["titles"][f]) for f in g["dead_ends"]]))
    else:
        L.append("   нет")
    L.append("")

    L.append("2а. Исходящих ссылок на разборы, по файлам (норма — 3):")
    L.append(table(["файл", "исх.", "вх."],
                   [(f, len(g["out_links"][f]), len(g["in_links"][f]))
                    for f in sorted(g["files"],
                                    key=lambda x: (len(g["out_links"][x]), x))]))
    L.append("")

    L.append(f"3. ТОВАРЫ БЕЗ ВХОДЯЩИХ ССЫЛОК ИЗ РАЗБОРОВ: {len(g['products_no_in'])}")
    rows = []
    for sku, page in sorted(g["products"].items()):
        rows.append((sku, page, len(g["product_in"].get(page, ())),
                     g["skus"][sku][:58]))
    L.append(table(["sku", "страница", "вх.", "название"], rows))
    L.append("")

    L.append(f"4. РАЗБОРЫ БЕЗ ТОВАРА (нет article-cta или битая ссылка): {len(g['no_product'])}")
    if g["no_product"]:
        L.append(table(["файл", "cta"],
                       [(f, ", ".join(g["cta_of"][f]) or "—") for f in g["no_product"]]))
    else:
        L.append("   нет")
    L.append("")

    L.append(f"5. АСИММЕТРИЯ — A → B, но B ↛ A: {len(g['asym'])} пар")
    if g["asym"]:
        L.append(table(["A (ссылается)", "B (не отвечает)"], g["asym"]))
    L.append("")

    L.append("6. КЛАСТЕРЫ")
    rows = []
    for name, cnt, members, prods in g["cluster_rows"]:
        inside = sum(
            1 for m in members for t in g["out_links"][m] if t in members
        )
        outside = sum(
            1 for m in members for t in g["out_links"][m] if t not in members
        )
        rows.append((name, cnt, inside, outside, ", ".join(prods) or "—"))
    L.append(table(["кластер", "статей", "связей внутри", "наружу", "товары"], rows))
    if g["unassigned"]:
        L.append(f"   вне кластеров: {', '.join(g['unassigned'])}")
    L.append("")

    L.append(f"7. БИТЫЕ ВНУТРЕННИЕ ССЫЛКИ: {len(g['broken'])}")
    if g["broken"]:
        L.append(table(["файл", "href"], g["broken"]))
    L.append("")
    return "\n".join(L)


VOID = {"br", "img", "meta", "link", "hr", "input", "source", "area", "base",
        "col", "embed", "param", "track", "wbr"}


class Nesting(HTMLParser):
    """Проверяет парность тегов и отсутствие вложенных <a>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        if tag == "a" and "a" in self.stack:
            self.problems.append(f"вложенный <a> внутри <a> (строка {self.getpos()[0]})")
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag not in self.stack:
            self.problems.append(f"</{tag}> без открывающего (строка {self.getpos()[0]})")
            return
        while self.stack:
            top = self.stack.pop()
            if top == tag:
                break
            self.problems.append(
                f"<{top}> не закрыт перед </{tag}> (строка {self.getpos()[0]})")


# --- сплошная целостность ссылок --------------------------------------------
#
# Отдельно от графа разборов выше. Тот отвечает на вопрос «как связаны статьи»,
# этот — на «ведёт ли хоть одна ссылка сайта в никуда», и по всем каталогам
# сразу. Разделение появилось из замера 14.08.2026: граф считал сирот и тупики
# и при этом молчал про кнопку покупки на materialy/akt-skrytyh-rabot.html,
# которая вела в несуществующий products/p4-akt-skrytyh-rabot-pto.html. Причина
# — граф обходил только префикс articles/. Здесь префиксов нет вовсе:
# проверяется любая локальная цель, включая src картинок и скриптов.

# Каталоги, которых нет на сервере: черновики, мастера продуктов, служебное.
# `data` — реестры и доказательства, на сервер не уезжает. Попал сюда
# замером 16.08.2026: в `data/legal/fixtures/pages/` легли сохранённые
# страницы официальных публикаторов, и проверка пошла по их разметке —
# 27 «битых ссылок» вида `/press_center/` и `about:blank` с чужого сайта.
# Гейт покраснел на первом же шаге, до собственных проверок репозитория.
# Чужая страница здесь доказательство, а не наша вёрстка: её ссылки к
# целостности сайта отношения не имеют.
NOT_DEPLOYED = {"content", "products-storage", "research", "tools", "tests",
                "data", ".git", ".github", ".claude", "node_modules"}

# Что не является внутренней целью и проверке не подлежит.
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "javascript:",
                     "data:", "//")

# Выдача покупателю лежит вне репозитория — файлы кладёт касса на сервере.
RUNTIME_PATHS = ("/orders/", "/download.php", "/pay.php")

# Собирается при деплое и в git не лежит (`.gitignore`). Пропускается по
# имени, а не по факту отсутствия: иначе исчезновение любого файла читалось
# бы как «наверное, генерируется». Счёт таких целей печатается — дыра в
# проверке должна быть видна, а не подразумеваться.
#
# Замер 14.08.2026: первый же прогон гейта на чистом checkout назвал
# `href="/rss.xml"` битой ссылкой на двух страницах. Локально прогон был
# зелёным — файл лежал в рабочей копии после прошлой сборки. То есть
# зелёный локальный прогон здесь ничего не значил, а гейт значил.
GENERATED_AT_DEPLOY = {"rss.xml"}


def site_html_files() -> list[Path]:
    """Все страницы, которые реально уезжают на сервер."""
    return sorted(
        p for p in ROOT.rglob("*.html")
        if not set(p.relative_to(ROOT).parts) & NOT_DEPLOYED
    )


def resolve_target(value: str, page: Path) -> Path | None:
    """Локальная ссылка → путь в репозитории. None — проверять нечего."""
    value = value.strip()
    if not value or value.startswith("#"):
        return None
    if value.startswith(EXTERNAL_PREFIXES):
        return None
    # Якорь и версия ассета к существованию файла отношения не имеют.
    clean = value.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return None
    if any(clean.startswith(r) or clean == r.rstrip("/") for r in RUNTIME_PATHS):
        return None
    base = ROOT if clean.startswith("/") else page.parent
    target = (base / clean.lstrip("/")).resolve()
    # Каталог — значит index.html внутри него.
    if clean.endswith("/") or (target.is_dir()):
        target = target / "index.html"
    return target


def is_generated(target: Path) -> bool:
    try:
        return target.relative_to(ROOT).as_posix() in GENERATED_AT_DEPLOY
    except ValueError:
        return False


def link_integrity(skipped: list[str] | None = None) -> list[str]:
    """Битые локальные цели по всему сайту: href, src, action, canonical.

    В `skipped`, если он передан, складываются цели, пропущенные как
    собираемые при деплое: они не дефект, но и не проверены.
    """
    fails: list[str] = []
    attr_re = re.compile(r'\b(href|src|action)="([^"]*)"')

    for page in site_html_files():
        rel = page.relative_to(ROOT).as_posix()
        raw = page.read_text(encoding="utf-8", errors="replace")
        # Содержимое <script> и <style> — не разметка. Замер 15.08.2026:
        # страница диагностики собирает адрес строками, и `href="' +
        # hit.core.url + '"` в скрипте читалось как битая ссылка. Проверка
        # обязана смотреть туда, где ссылка действительно есть.
        # Вырезается только содержимое, открывающий тег остаётся: у
        # <script src="..."> адрес живёт в атрибуте, и снятие элемента
        # целиком его теряет. Поймано регрессом: «проверка не увидела
        # битую цель: скрипт src».
        text = re.sub(r"(<(?:script|style)\b[^>]*>).*?</(?:script|style)>",
                      r"\1", raw, flags=re.S | re.I)
        seen: set[tuple[str, str]] = set()
        for attr, value in attr_re.findall(text):
            if (attr, value) in seen:
                continue
            seen.add((attr, value))
            target = resolve_target(value, page)
            if target is None:
                continue
            if not target.exists():
                if is_generated(target):
                    if skipped is not None:
                        skipped.append(f"{rel}: {value}")
                    continue
                fails.append(f"{rel}: {attr}=\"{value}\" — цели нет")

        # canonical обязан указывать на существующую страницу своего сайта.
        m = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', raw)
        if m:
            href = m.group(1)
            if href.startswith(SITE):
                target = resolve_target(href[len(SITE):] or "/", page)
                if target is not None and not target.exists():
                    fails.append(f"{rel}: canonical → {href} — страницы нет")
            elif href.startswith(("http://", "https://")):
                fails.append(f"{rel}: canonical на чужой хост — {href}")

    # Карта сайта не должна обещать роботу того, чего нет.
    sitemap = ROOT / "sitemap.xml"
    if sitemap.exists():
        for loc in re.findall(r"<loc>(.*?)</loc>",
                              sitemap.read_text(encoding="utf-8")):
            if not loc.startswith(SITE):
                fails.append(f"sitemap.xml: чужой хост — {loc}")
                continue
            target = resolve_target(loc[len(SITE):] or "/", sitemap)
            if target is not None and not target.exists() and not is_generated(target):
                fails.append(f"sitemap.xml: {loc} — страницы нет")
    return fails


def verify() -> int:
    """Проверки, которые обязаны пройти до коммита. 0 = всё чисто."""
    skipped: list[str] = []
    fails: list[str] = link_integrity(skipped)
    html_files = sorted(ARTICLES.glob("*.html")) + sorted(PRODUCTS.glob("*.html"))

    for path in html_files:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        n = Nesting()
        n.feed(text)
        n.close()
        for t in reversed(n.stack):
            if t not in ("html", "body", "head", "p", "li"):
                n.problems.append(f"<{t}> остался незакрытым в конце файла")
        for p in n.problems:
            fails.append(f"HTML {path.name}: {p}")

        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', text, re.S
        ):
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                fails.append(f"JSON-LD {path.name}: {e}")

        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            clean = href.split("#")[0].split("?")[0]
            if not clean or clean.endswith("/"):
                continue
            # rss.xml собирается при деплое (tools/build_rss.py) и в git не лежит.
            if clean == "/rss.xml":
                continue
            target = (ROOT / clean.lstrip("/")) if clean.startswith("/") \
                else (path.parent / clean)
            if not target.exists():
                fails.append(f"ССЫЛКА {path.name}: {href} → нет файла")

    # Витрина: непрерывные позиции ItemList, все разборы на месте.
    #
    # Требования CRLF здесь больше нет. Оно стояло с первого дня и было
    # неверным: `git show 54a99f5~1:articles/index.html | grep -c $'\r'` → 0,
    # то есть у витрины не было CR никогда. Проверка требовала свойства,
    # которого файл не имел, и держала verify() красным. CRLF значим для
    # `content/strategy/semantic-core.csv` — другой файл, другая проверка.
    text = INDEX.read_text(encoding="utf-8")
    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
    try:
        graph = json.loads(ld.group(1))["@graph"]
    except Exception as e:  # noqa: BLE001
        fails.append(f"ВИТРИНА JSON-LD: {e}")
        graph = []
    for node in graph:
        if node.get("@type") != "ItemList":
            continue
        pos = [i["position"] for i in node["itemListElement"]]
        if pos != list(range(1, len(pos) + 1)):
            fails.append(f"ВИТРИНА: позиции ItemList не непрерывны: {pos}")
        urls = {i["item"]["url"].rsplit("/", 1)[1] for i in node["itemListElement"]}
        missing = set(article_files()) - urls
        extra = urls - set(article_files())
        if missing:
            fails.append(f"ВИТРИНА: нет в ItemList: {sorted(missing)}")
        if extra:
            fails.append(f"ВИТРИНА: лишние в ItemList: {sorted(extra)}")
    # Между class и href стоит data-cluster с 54a99f5 («Витрина разборов —
    # фильтр по темам»). Регулярка требовала их рядом и с того дня не
    # находила ни одной карточки — проверка была красной три недели и никем
    # не запускалась. Атрибуты между ними допускаются намеренно.
    cards = set(re.findall(r'<a class="showcase-card"[^>]*href="([^"]+)"', text))
    missing = set(article_files()) - cards
    if missing:
        fails.append(f"ВИТРИНА: нет карточки: {sorted(missing)}")

    n = Nesting()
    n.feed(text)
    n.close()
    for p in n.problems:
        fails.append(f"HTML index.html: {p}")

    if fails:
        print("ПРОВЕРКИ НЕ ПРОЙДЕНЫ:")
        for f in fails:
            print("  ✗", f)
        return 1
    note = f", пропущено собираемых при деплое {len(skipped)}" if skipped else ""
    print(f"ПРОВЕРКИ ПРОЙДЕНЫ: страниц {len(site_html_files())}, битых локальных")
    print(f"целей 0{note} (href, src, action, canonical, карта сайта); HTML парсится,")
    print("теги парные, JSON-LD валиден, позиции ItemList непрерывны и")
    print("покрывают все разборы.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--verify", action="store_true",
                    help="только проверки целостности, без таблиц")
    args = ap.parse_args()
    if args.verify:
        return verify()
    g = build()
    print(report(g))
    # Целостность считается и в обычном прогоне: битая ссылка — дефект, а не
    # строка отчёта, и код возврата обязан о ней говорить.
    broken = link_integrity()
    if broken:
        print("\nБИТЫЕ ЛОКАЛЬНЫЕ ЦЕЛИ:")
        for f in broken:
            print("  ✗", f)
    else:
        print(f"\nЦелостность ссылок: страниц {len(site_html_files())}, "
              "битых локальных целей 0.")
    if args.json:
        serial = {
            k: (sorted(v) if isinstance(v, set) else v)
            for k, v in g.items() if k not in ("cluster_rows",)
        }
        serial["out_links"] = {k: sorted(v) for k, v in g["out_links"].items()}
        serial["in_links"] = {k: sorted(v) for k, v in g["in_links"].items()}
        serial["product_in"] = {k: sorted(v) for k, v in g["product_in"].items()}
        args.json.write_text(json.dumps(serial, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
