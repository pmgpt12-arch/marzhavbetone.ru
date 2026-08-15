#!/usr/bin/env python3
"""Карта «страница контента → товар»: один основной выход, а не пять.

Обратное направление к `data/sales/product-map.csv`. Та карта отвечает на
вопрос «какой болью торгует товар»; эта — на вопрос, который задаёт себе
человек, дочитавший разбор: «мне-то что теперь делать». Ответов на него у
страницы должно быть не пять и не ноль, а один основной и, если он есть,
один запасной.

Замер 15.08.2026 по сорока разборам: на двадцати трёх упомянут один товар,
на четырнадцати — два, на трёх — три и четыре. Ссылка на каталог есть на
каждой, но это пункт шапки, а не выход: «пойдите посмотрите каталог» — не
ответ человеку, который только что прочитал про свою беду.

Что проверяется:

  · у страницы контента есть основной выход на товар — кнопка, а не
    упоминание в тексте;
  · основной выход ведёт на товар, а не в каталог;
  · товаров на странице не больше двух: основной и один названный
    запасной. Третий — это уже выбор вместо действия. Двух хватает и на
    ступень входа рядом с комплектом — на бесплатных материалах пара
    «вход 990 ₽ + комплект» стоит намеренно, и запрещать её нечем;
  · товар выхода на продаже в кассе.

Чего этот инструмент не делает: не решает, какой товар правильный для
страницы. Это делает `money_impact.py` по категории денежной проблемы, и
дублировать его вердикт здесь нечем.

    python3 tools/content_product_map.py            # таблица и расхождения
    python3 tools/content_product_map.py --write    # записать CSV
    python3 tools/content_product_map.py --check    # расхождение — код 1
    python3 tools/content_product_map.py --coverage  # покрытие товаров контентом
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sales" / "content-product-map.csv"
PRODUCT_MAP = ROOT / "data" / "sales" / "product-map.csv"
MONEY_IMPACT = ROOT / "data" / "business" / "money-impact.yaml"
MONEY_PAINS = ROOT / "data" / "business" / "money-pains.yaml"

FIELDS = ["content_url", "content_type", "money_pain", "stage",
          "primary_product", "secondary_product_or_free_tool", "primary_cta"]

# Ссылка на товар в разметке. Пути встречаются и абсолютные, и
# относительные — сравнивать их можно только приведёнными к SKU.
PRODUCT_HREF = re.compile(r'href="([^"]*products/([a-z0-9]+)-[^"#]*\.html)"')
FREE_HREF = re.compile(r'href="([^"]*materialy/([a-z0-9-]+)\.html)"')
# Действием считается кнопка и ссылка внутри карточки товара: карточка —
# это тоже предложение целиком, «Подробнее →» в ней читается как ход.
# Ссылка в абзаце действием не является, и складывать одно с другим
# значило бы считать не то.
#
# Ветвление считается отдельно, и это не поблажка. Калькулятор и
# диагностика показывают ровно один выход — тот, который выпал по ответам,
# — а остальные лежат в скрытых блоках или в данных сценария. Считать их
# конкурирующими значило бы наказать страницу за то, что она как раз и
# делает: выбирает за человека.
CATALOG_HREF = re.compile(r'href="([^"]*(?:katalog\.html|#catalog))"')
CARD_CLASSES = ("product-card", "cross-card")


class Links(HTMLParser):
    """Ссылки страницы с ответом на два вопроса: действие ли это и в ветке ли."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool]] = []   # тег, скрыт, карточка
        self.links: list[dict] = []
        self.in_main = False
        self.branches = 0

    def handle_starttag(self, tag, attrs):
        attr = {k: (v or "") for k, v in attrs}
        if tag == "main":
            self.in_main = True
        hidden = "hidden" in attr or any(
            h for _t, h, _c in self.stack if h)
        card = any(c in attr.get("class", "") for c in CARD_CLASSES) or any(
            c for _t, _h, c in self.stack if c)
        if tag == "a" and self.in_main:
            self.links.append({
                "href": attr.get("href", ""),
                "action": "button" in attr.get("class", "").split()
                          or "button" in attr.get("class", "") or card,
                "hidden": hidden,
            })
        if tag not in ("br", "img", "input", "meta", "link", "hr"):
            self.stack.append((tag, hidden, card))
        if "hidden" in attr and self.in_main:
            self.branches += 1

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def content_pages() -> list[tuple[str, Path]]:
    """Страницы, с которых человек может уйти к товару.

    Оглавления (`index.html`) сюда не входят: у списка нет своей денежной
    проблемы, и одного выхода у него быть не должно.
    """
    out: list[tuple[str, Path]] = []
    for path in sorted((ROOT / "articles").glob("*.html")):
        if path.name != "index.html":
            out.append(("разбор", path))
    for path in sorted((ROOT / "materialy").glob("*.html")):
        if path.name != "index.html":
            out.append(("бесплатный материал", path))
    for name in ("kalkulyator.html", "diagnostika.html"):
        path = ROOT / name
        if path.exists():
            out.append(("инструмент", path))
    for path in sorted((ROOT / "products").glob("*.html")):
        out.append(("товар", path))
    return out


def catalog() -> dict[str, dict]:
    with PRODUCT_MAP.open(encoding="utf-8") as fh:
        return {row["product_id"]: row for row in csv.DictReader(fh)}


def pains() -> list[tuple[str, str, list[str]]]:
    """Признаки категорий, приведённые к словарю болей (MP-*).

    Категории денежного влияния (MI-*) и боли лестницы (MP-*) — два
    словаря об одном и том же, и смешивать их в одной колонке нельзя:
    таблица с MP-5 в одной строке и MI-1 в другой не машиночитаема, чем
    бы она ни выглядела. Соответствие объявлено в `money-pains.yaml`, а не
    выведено из совпадения номеров.
    """
    impact = yaml.safe_load(MONEY_IMPACT.read_text(encoding="utf-8"))["categories"]
    ladder = yaml.safe_load(MONEY_PAINS.read_text(encoding="utf-8"))["pains"]
    to_pain = {val["money_impact"]: key for key, val in ladder.items()
               if val.get("money_impact")}
    order = sorted(impact.items(), key=lambda kv: kv[1].get("priority", 99))
    return [(to_pain.get(key, key), val["title"],
             [m.lower() for m in val.get("markers", [])])
            for key, val in order]


def visible(raw: str) -> str:
    body = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))).lower()


def money_pain(raw: str, sku: str | None, cat: dict, table) -> str:
    """Категория денежной проблемы страницы.

    Сначала по товару, на который страница выводит: у товара категория
    задана картой и не зависит от слов в тексте. Если выхода нет — по
    признакам, в порядке приоритета от денег назад по процессу.
    """
    if sku and sku in cat:
        first = (cat[sku].get("money_pain") or "").split(";")[0]
        if first:
            return first
    text = visible(raw)
    for key, _title, markers in table:
        if any(m in text for m in markers):
            return key
    return ""


def read_page(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    parser = Links()
    parser.feed(raw)

    def sku_of(href: str) -> str | None:
        found = PRODUCT_HREF.search(f'href="{href}"')
        return found.group(2) if found else None

    products, frees = [], []
    actions, branch_actions = [], []
    for link in parser.links:
        sku = sku_of(link["href"])
        free = FREE_HREF.search(f'href="{link["href"]}"')
        if free and free.group(2) not in frees:
            frees.append(free.group(2))
        if not sku:
            continue
        if sku not in products:
            products.append(sku)
        if link["action"]:
            (branch_actions if link["hidden"] else actions).append(
                (sku, "/" + link["href"].lstrip("./")))

    primary, primary_cta = ("", "")
    if actions:
        primary, primary_cta = actions[0]
    elif branch_actions:
        primary, primary_cta = branch_actions[0]
    elif products:
        primary = products[0]

    # Диагностика строит выход сценария на лету: разметки со ссылкой на
    # товар в файле нет, есть таблица сценариев в данных страницы. Считать
    # это «выхода нет» — ошибка прибора, а не находка; сборка страницы
    # проверяется своим инструментом (`build_diagnostic.py`).
    scripted = "hit.core.url" in raw
    if scripted and not products:
        for sku in set(re.findall(r'"/products/([a-z0-9]+)-[^"]*\.html"', raw)):
            products.append(sku)

    open_products = [sku for sku, _ in actions]
    return {"raw": raw, "products": products, "frees": frees, "scripted": scripted,
            "primary": primary, "primary_cta": primary_cta,
            "has_button": bool(actions or branch_actions),
            "open_actions": open_products,
            "branching": len(branch_actions) > 1,
            "catalog_only": not products}


def build() -> tuple[list[dict], list[str]]:
    cat = catalog()
    table = pains()
    rows, bad = [], []

    for kind, path in content_pages():
        rel = "/" + path.relative_to(ROOT).as_posix()
        page = read_page(path)

        if kind == "товар":
            sku = re.search(r'data-sku="([^"]+)"', page["raw"])
            primary = sku.group(1) if sku else ""
            others = [p for p in page["products"] if p != primary]
            secondary = others[0] if others else (
                page["frees"][0] if page["frees"] else "")
            cta = rel
        else:
            primary = page["primary"]
            others = [p for p in page["products"] if p != primary]
            secondary = others[0] if others else (
                "/materialy/" + page["frees"][0] + ".html" if page["frees"] else "")
            cta = page["primary_cta"]

            if page["scripted"] or page["branching"]:
                # Ветвящаяся страница показывает один выход — тот, который
                # выпал по ответам. Требование «один товар на странице» к
                # ней неприменимо; применимо другое — чтобы выход был.
                if not page["products"]:
                    bad.append(f"{rel}: сценарии есть, а выхода на товар нет")
            elif not primary:
                bad.append(f"{rel}: выхода на товар нет вовсе"
                           + (" — только каталог" if page["catalog_only"] else ""))
            elif not page["has_button"]:
                bad.append(f"{rel}: товар {primary} упомянут ссылкой в тексте, "
                           f"кнопки покупки нет — действие не читается как действие")
            elif len(page["products"]) > 2:
                bad.append(f"{rel}: товаров на странице {len(page['products'])} "
                           f"({', '.join(page['products'])}) — вместо действия "
                           f"предложен выбор")

        if primary and primary not in cat:
            bad.append(f"{rel}: выход на {primary}, которого нет в карте товаров")
        elif primary and cat[primary].get("status") != "active":
            bad.append(f"{rel}: выход на {primary} — он не на продаже "
                       f"({cat[primary].get('status')})")

        rows.append({
            "content_url": rel,
            "content_type": kind + (" (ветвление)" if page.get("scripted")
                                    or page.get("branching") else ""),
            "money_pain": money_pain(page["raw"], primary, cat, table),
            "stage": cat.get(primary, {}).get("stage", ""),
            "primary_product": primary,
            "secondary_product_or_free_tool": secondary,
            "primary_cta": cta,
        })
    return rows, bad


def coverage(rows: list[dict]) -> list[tuple[str, int, int]]:
    """Сколько страниц трафика ведёт на каждый товар.

    Считается отдельно основной выход и запасной: товар, который называют
    только «а ещё есть вот такой», трафика не получает — его видят те, кто
    и так пришёл за другим.

    Страницы товаров в счёт не идут: собственная страница есть у каждого
    из восемнадцати, и включать её значило бы поднять всем по единице и
    спрятать нули.
    """
    traffic = [r for r in rows if r["content_type"] != "товар"]
    skus = [r["primary_product"] for r in rows if r["content_type"] == "товар"]
    out = []
    for sku in skus:
        primary = sum(1 for r in traffic if r["primary_product"] == sku)
        secondary = sum(1 for r in traffic
                        if r["secondary_product_or_free_tool"] == sku)
        out.append((sku, primary, secondary))
    return sorted(out, key=lambda row: (row[1], row[2]))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--coverage", action="store_true",
                        help="сколько страниц трафика ведёт на каждый товар")
    args = parser.parse_args()

    rows, bad = build()

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Записано: {OUT.relative_to(ROOT)}, строк {len(rows)}")

    kinds: dict[str, int] = {}
    for row in rows:
        kinds[row["content_type"]] = kinds.get(row["content_type"], 0) + 1
    print("Страниц контента: " + ", ".join(f"{k} {v}" for k, v in kinds.items()))
    without = [r["content_url"] for r in rows if not r["primary_product"]]
    print(f"С названным выходом на товар: {len(rows) - len(without)} из {len(rows)}")
    if without:
        # Пустая клетка здесь значит «выход выбирается по ответам», а не
        # «выхода нет». Разница существенная, и молчать о ней нельзя:
        # пустое поле в таблице читается как дефект.
        print("   выход по сценарию, а не один на страницу: "
              + ", ".join(without))

    if args.coverage:
        print("\nПокрытие товаров контентом (страницы товаров не в счёт):")
        print(f"   {'товар':<6} {'основной':>9} {'запасной':>9}")
        for sku, primary, secondary in coverage(rows):
            mark = "  ← нет трафика" if primary == 0 else ""
            print(f"   {sku:<6} {primary:>9} {secondary:>9}{mark}")

    if bad:
        print(f"Расхождений: {len(bad)}")
        for line in bad:
            print(f"   · {line}")
        return 1
    print("Дефектов нет: у каждой страницы один основной выход на товар, "
          "он ведёт на товар в продаже, конкурирующих предложений нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
