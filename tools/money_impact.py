#!/usr/bin/env python3
"""Money Impact Layer: какая страница про какую денежную проблему.

Отвечает на первые шесть из десяти вопросов, которыми владелец задал
критерий завершения этапа: какая проблема, какой бесплатный материал,
какой продукт ей соответствует. На оставшиеся четыре — сколько переходят,
сколько покупают, какая выручка, усиливать или нет — отвечают числа, и
их нет: ни один из трёх токенов не заведён (см. CLAUDE.md, раздел про
замер 14.08.2026).

Отсюда устройство: структурные колонки заполняются здесь и сейчас,
колонки метрик остаются пустыми. Пусто значит «не измерено», а не «ноль»
— спутать эти два дороже, чем не иметь таблицы вовсе.

    python3 tools/money_impact.py            # разбор и разрывы
    python3 tools/money_impact.py --write    # записать money-impact.csv

Что считается разрывом:
  • страница без денежной категории — непонятно, чью проблему решает;
  • категория без бесплатного материала — начать нечем;
  • **PRODUCT OPPORTUNITY**: у категории есть страницы, но комплекта,
    закрывающего проблему, в каталоге нет;
  • Product-Content Fit: страница ведёт на комплект чужой категории.

Код 1 — только на первых двух: страница без категории и страница без
единого комплекта. Остальное — сигналы владельцу, а не поломка сайта:
какой именно комплект должна продавать страница и заводить линовый  продукт
под категорию — состав каталога, то есть решение владельца (Р-006).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "data" / "business" / "money-impact.yaml"
OUT = ROOT / "data" / "business" / "money-impact.csv"
CONFIG = ROOT / "products-config.php"

COLUMNS = [
    "money_cluster", "problem", "query", "landing_url", "free_material",
    "product", "impressions", "clicks", "product_clicks", "checkout_starts",
    "purchases", "revenue", "conversion_rate", "revenue_per_visitor",
    "confidence", "updated_at",
]


def load_rules() -> tuple[dict, dict]:
    """(категории, бесплатные материалы). Разбор узкий — правит человек."""
    cats: dict[str, dict] = {}
    free: dict[str, list[str]] = {}
    section = None
    key = None
    for raw in RULES.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        if indent == 0 and text.endswith(":"):
            section = text[:-1]
            continue
        if section == "categories":
            if indent == 2 and text.endswith(":"):
                key = text[:-1]
                cats[key] = {"title": key, "priority": 99,
                             "products": [], "markers": []}
            elif indent == 4 and text.startswith("title:"):
                cats[key]["title"] = text.split(":", 1)[1].strip()
            elif indent == 4 and text.startswith("priority:"):
                cats[key]["priority"] = int(text.split(":", 1)[1])
            elif indent == 4 and text.startswith("products:"):
                cats[key]["products"] = [
                    s.strip() for s in
                    text.split("[", 1)[1].rstrip("]").split(",") if s.strip()]
            elif indent == 6 and text.startswith("- "):
                cats[key]["markers"].append(text[2:].strip().strip('"'))
        elif section == "free_materials" and indent == 2:
            name, rest = text.split(":", 1)
            free[name.strip()] = [s.strip() for s in
                                  rest.strip().strip("[]").split(",")
                                  if s.strip()]
    return cats, free


def catalogue() -> dict[str, str]:
    """sku → название. Истина по каталогу — конфиг кассы, а не страницы."""
    text = CONFIG.read_text(encoding="utf-8")
    body = text.split("function mvb_products(): array", 1)[1]
    body = body.split("/** Ищет продукт", 1)[0]
    out = {}
    for m in re.finditer(
            r"'([a-z0-9]+)'\s*=>\s*\[\s*\n\s*'name'\s*=>\s*'((?:[^']|'')*)'",
            body):
        out[m.group(1)] = m.group(2).replace("''", "'")
    return out


def page_parts(path: Path) -> tuple[str, str]:
    """(заголовок, лид). Разделены, потому что весят по-разному."""
    raw = path.read_text(encoding="utf-8", errors="replace")

    def grab(pattern: str) -> str:
        m = re.search(pattern, raw, re.S)
        return re.sub(r"<[^>]+>", " ", m.group(1)).lower() if m else ""

    head = grab(r"<title>(.*?)</title>") + " " + grab(r"<h1[^>]*>(.*?)</h1>")
    return head, grab(r'<p class="lead">(.*?)</p>')


def page_text(path: Path) -> str:
    """Заголовок и лид: по ним определяется проблема, а не по всему тексту.

    Весь текст статьи упоминает половину категорий — по нему страница
    отнеслась бы куда угодно. Название и первый абзац называют, о чём она.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    parts = []
    for pattern in (r"<title>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>",
                    r'<p class="lead">(.*?)</p>'):
        m = re.search(pattern, raw, re.S)
        if m:
            parts.append(re.sub(r"<[^>]+>", " ", m.group(1)))
    return " ".join(parts).lower()


def classify(head: str, lead: str, cats: dict) -> str:
    """Категория по числу совпавших признаков, приоритет — только тай-брейк.

    Первая версия брала первое совпадение в порядке приоритета, и это
    оказалось слишком грубо: разбор про банкротство генподрядчика уезжал в
    MI-1, потому что в лиде раньше встречалось «не заплатят». Категория
    определяется тем, о чём страница, а не тем, какое слово попалось
    первым. При равном счёте выигрывает более денежная — там порядок
    «от денег назад по процессу» верен.
    """
    scored = []
    for key, cat in cats.items():
        weight = 0
        for marker in cat["markers"]:
            m = marker.lower()
            # Длина признака — мера его точности: «передачи строительной
            # площадки» говорит о странице больше, чем «замечания».
            if m in head:
                weight += len(m) * 3
            elif m in lead:
                weight += len(m)
        if weight:
            scored.append((-weight, cat["priority"], key))
    return sorted(scored)[0][2] if scored else ""


def product_links(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r"/products/([a-z0-9]+)-[a-z0-9-]*\.html",
                                 raw)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    cats, free = load_rules()
    skus = catalogue()
    today = date.today().isoformat()

    defects: list[str] = []
    signals: list[str] = []
    rows: list[dict] = []
    by_cat: dict[str, list[str]] = {k: [] for k in cats}

    for path in sorted((ROOT / "articles").glob("*.html")):
        if path.name == "index.html":
            continue
        rel = "articles/" + path.name
        head, lead = page_parts(path)
        key = classify(head, lead, cats)
        if not key:
            defects.append(f"/{rel}: денежная категория не определена — "
                           f"непонятно, чью проблему страница решает")
            continue
        by_cat[key].append(rel)

        linked = product_links(path)
        expected = cats[key]["products"]
        fit = [s for s in linked if s in expected]
        if not linked:
            defects.append(f"/{rel}: не ведёт ни на один комплект — "
                           f"цепочка обрывается на странице")
        elif not fit:
            # Не дефект, а решение владельца: какой комплект должна
            # продавать страница — состав каталога (Р-006). Инструмент
            # называет расхождение и рекомендацию, вердикт не выносит.
            signals.append(
                f"PRODUCT-CONTENT FIT: /{rel} — {key} "
                f"«{cats[key]['title']}», ведёт на {', '.join(linked)}; "
                f"по категории ожидался бы любой из "
                f"{', '.join(expected)}")

        rows.append({
            "money_cluster": key,
            "problem": cats[key]["title"],
            # Запрос приходит из Вебмастера; сопоставление с URL — там же.
            "query": "",
            "landing_url": "/" + rel,
            "free_material": ";".join("/" + f for f in free.get(key, [])),
            "product": ";".join(fit or expected),
            "impressions": "", "clicks": "", "product_clicks": "",
            "checkout_starts": "", "purchases": "", "revenue": "",
            "conversion_rate": "", "revenue_per_visitor": "",
            # Уверенность в строке: структура известна, метрики нет.
            "confidence": "структура",
            "updated_at": today,
        })

    for key, cat in sorted(cats.items(), key=lambda kv: kv[1]["priority"]):
        pages = by_cat[key]
        have = [s for s in cat["products"] if s in skus]
        missing = [s for s in cat["products"] if s not in skus]
        if pages and not have:
            signals.append(
                f"PRODUCT OPPORTUNITY: {key} «{cat['title']}» — страниц "
                f"{len(pages)}, комплекта в каталоге нет")
        if missing:
            signals.append(
                f"{key}: в правилах названы отсутствующие в каталоге "
                f"комплекты: {', '.join(missing)}")
        if not free.get(key):
            signals.append(f"{key} «{cat['title']}»: нет бесплатного "
                           f"материала — человеку нечем начать")

    print("Money Impact по разборам\n")
    for key, cat in sorted(cats.items(), key=lambda kv: kv[1]["priority"]):
        products = ", ".join(cat["products"])
        print(f"  {key}  {cat['title']}")
        print(f"        страниц {len(by_cat[key])}, комплекты: {products}, "
              f"бесплатных {len(free.get(key, []))}")

    # Перекос портфеля: денежный приоритет против покрытия. Это не
    # метрика, а структура — считается без единого замера и уже отвечает
    # на вопрос «где незакрытая ценность». Числа лишь уточнят порядок.
    ranked = sorted(cats.items(), key=lambda kv: kv[1]["priority"])
    thin = [(k, c, len(by_cat[k])) for k, c in ranked[:3]
            if len(by_cat[k]) < 4]
    if thin:
        print("\n## Перекос портфеля")
        widest = max(by_cat.items(), key=lambda kv: len(kv[1]))
        for key, cat, count in thin:
            print(f"   • {key} «{cat['title']}» — приоритет "
                  f"{cat['priority']}, страниц {count}; при этом "
                  f"{widest[0]} держит {len(widest[1])}")

    print(f"\nВсего разборов размечено: {len(rows)}")
    print("Метрики: ни одной — токенов нет, колонки пусты намеренно.")

    if signals:
        print(f"\n## Сигналы владельцу — {len(signals)}")
        for s in signals:
            print(f"   • {s}")

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nЗаписано: {OUT.relative_to(ROOT)}, строк {len(rows)}")

    if defects:
        print(f"\n## ДЕФЕКТЫ — {len(defects)}")
        for d in defects:
            print(f"   ✗ {d}")
        return 1

    print("\nДефектов нет: у каждого разбора определена денежная проблема, "
          "и он ведёт на комплект своей категории.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
