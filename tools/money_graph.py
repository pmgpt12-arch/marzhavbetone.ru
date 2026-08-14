#!/usr/bin/env python3
"""Проверка money graph: ведёт ли страница вперёд по процессу.

Ссылка «читайте также» отвечает на вопрос «о чём ещё есть текст».
Подрядчику нужен ответ «что у меня дальше»: допработы → фиксация →
объёмы → КС-2 → приёмка → срок оплаты → неоплата → претензия. Маршруты
объявлены в `data/seo/money-graph.yaml`, здесь они сверяются с реальными
ссылками страниц.

Что считается разрывом цепочки:
  1. шаг маршрута без страницы (`page: ~`) — кандидат на CREATE;
  2. страница шага не существует — маршрут указывает в никуда;
  3. страница не ссылается на следующий шаг — человек доходит до конца
     текста и остаётся без следующего действия;
  4. страница без бесплатного материала или без товара — цепочка
     «спрос → материал → продукт» обрывается на ней.

Каждый разрыв печатается задачей: адрес, чего не хватает, куда ставить.

    python3 tools/money_graph.py            # разрывы цепочек
    python3 tools/money_graph.py --map      # маршруты целиком

Код 1 — есть разрывы 2-го или 4-го вида (дефект). Разрыв 1-го и 3-го вида
кодом не отражается: первый — решение владельца о новой странице, третий
— вопрос перелинковки, который решается правкой, но не обязан блокировать
выкладку.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "data" / "seo" / "money-graph.yaml"


def load_chains() -> dict:
    """Разбор объявленных маршрутов. Формат узкий — намеренно."""
    chains: dict[str, dict] = {}
    key = None
    for raw in GRAPH.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        if indent == 2 and text.endswith(":"):
            key = text[:-1]
            chains[key] = {"title": key, "steps": []}
        elif indent == 4 and text.startswith("title:"):
            chains[key]["title"] = text.split(":", 1)[1].strip()
        elif indent == 6 and text.startswith("- step:"):
            chains[key]["steps"].append(
                {"step": text.split(":", 1)[1].strip(), "page": None})
        elif indent == 8 and text.startswith("page:"):
            value = text.split(":", 1)[1].strip()
            chains[key]["steps"][-1]["page"] = None if value == "~" else value
    return chains


def links_of(page: Path) -> set[str]:
    """Локальные цели страницы, приведённые к пути от корня сайта."""
    text = page.read_text(encoding="utf-8", errors="replace")
    out = set()
    base = page.parent
    for value in re.findall(r'\bhref="([^"]*)"', text):
        value = value.split("#")[0].split("?")[0].strip()
        if not value or value.startswith(("http", "mailto:", "tel:", "//")):
            continue
        target = (ROOT / value.lstrip("/")) if value.startswith("/") \
            else (base / value)
        try:
            out.add(target.resolve().relative_to(ROOT).as_posix())
        except ValueError:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", action="store_true", help="показать маршруты")
    args = ap.parse_args()

    chains = load_chains()
    tasks: list[str] = []   # дефекты, влияют на код возврата
    notes: list[str] = []   # разрывы-решения и перелинковка

    covered: set[str] = set()
    for name, chain in chains.items():
        steps = chain["steps"]
        if args.map:
            print(f"\n## {chain['title']}")
        for i, step in enumerate(steps):
            page_rel = step["page"]
            nxt = steps[i + 1]["page"] if i + 1 < len(steps) else None
            if page_rel is None:
                notes.append(
                    f"{chain['title']}: шага «{step['step']}» нет страницы — "
                    f"кандидат на CREATE, решение владельца")
                if args.map:
                    print(f"  {i+1}. [нет страницы] {step['step']}")
                continue
            covered.add(page_rel)
            page = ROOT / page_rel
            if not page.exists():
                tasks.append(f"{page_rel}: маршрут «{chain['title']}» "
                             f"указывает на несуществующую страницу")
                continue

            links = links_of(page)
            if args.map:
                print(f"  {i+1}. /{page_rel}  ← {step['step']}")

            # 3. Ведёт ли вперёд.
            if nxt and nxt not in links:
                notes.append(
                    f"/{page_rel}: нет ссылки на следующий шаг /{nxt} "
                    f"(«{steps[i+1]['step']}») — читатель доходит до конца "
                    f"и остаётся без следующего действия")

            # 4. Цепочка к деньгам.
            if not any(t.startswith("materialy/") for t in links):
                tasks.append(f"/{page_rel}: нет выхода на бесплатный материал")
            if not any(t.startswith("products/") for t in links):
                tasks.append(f"/{page_rel}: нет выхода на товар")

    articles = {p.relative_to(ROOT).as_posix()
                for p in (ROOT / "articles").glob("*.html")
                if p.name != "index.html"}
    outside = sorted(articles - covered)

    print(f"\nМаршрутов: {len(chains)}, шагов со страницей: {len(covered)}, "
          f"статей вне маршрутов: {len(outside)}")

    if outside:
        print("\n## Статьи вне маршрутов — процесс для них не объявлен")
        for name in outside:
            print(f"   /{name}")

    if notes:
        print(f"\n## Разрывы, требующие решения или правки — {len(notes)}")
        for n in notes:
            print(f"   • {n}")

    if tasks:
        print(f"\n## ДЕФЕКТЫ — {len(tasks)}")
        for t in tasks:
            print(f"   ✗ {t}")
        return 1

    print("\nДефектов цепочки нет: у каждого шага маршрута есть страница, "
          "бесплатный материал и товар.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
