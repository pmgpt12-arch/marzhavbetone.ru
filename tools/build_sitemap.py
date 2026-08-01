#!/usr/bin/env python3
"""Собирает sitemap.xml из файлов сайта.

Раньше карта правилась руками, и это дважды за один день расходилось с
действительностью: адрес удалённой страницы оставался, адрес новой не
появлялся. Источник истины — сами файлы, поэтому карта не может разойтись с
сайтом.

Второе, чего не было: `lastmod`. Без него поисковик не знает, что страницу
переписали, и приходит к ней по своему расписанию. Дата берётся из последнего
коммита, изменившего файл, — то есть отражает правку содержания, а не время
сборки.

    python3 tools/build_sitemap.py            # собрать и записать
    python3 tools/build_sitemap.py --verify   # сравнить с записанным, не менять
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
BASE = "https://marzhavbetone.ru"

# Страницы, которых в карте быть не должно, и причина у каждой.
EXCLUDED = {
    "test-pokupka.html": "скрытая служебная покупка за 1 ₽, закрыта и в robots.txt",
    "success.html": "страница после оплаты, доступна только с токеном заказа",
    "fail.html": "страница неудачной оплаты",
    "404.html": "страница ошибки",
}

# Раздел → (частота обновления, приоритет). Приоритет — относительный вес
# внутри сайта, а не обещание поисковику: он говорит, что обходить первым,
# когда бюджет обхода ограничен.
SECTIONS = [
    ("index.html",     "weekly",  "1.0"),
    ("products/",      "monthly", "0.9"),
    ("articles/",      "monthly", "0.8"),
    ("materialy/",     "monthly", "0.7"),
    ("kalkulyator.html", "monthly", "0.9"),
]
LEGAL = {"privacy.html": "0.2", "offer.html": "0.3", "payment-delivery.html": "0.3",
         "refund.html": "0.3", "contacts.html": "0.3", "rekvizity.html": "0.3"}


def git_date(path: Path) -> str:
    """Дата последнего коммита, изменившего файл. Для незакоммиченного — сегодня."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path.relative_to(SITE))],
            cwd=SITE, capture_output=True, text=True, timeout=15).stdout.strip()
        return out or date.today().isoformat()
    except Exception:
        return date.today().isoformat()


def classify(rel: str) -> tuple[str, str] | None:
    name = rel.split("/")[-1]
    if name in EXCLUDED:
        return None
    if rel in LEGAL:
        return "yearly", LEGAL[rel]
    if rel == "index.html":
        return "weekly", "1.0"
    if rel == "kalkulyator.html":
        return "monthly", "0.9"
    if rel == "articles/index.html":
        return "weekly", "0.9"
    if rel.startswith("products/"):
        # Полный комплект и договор — точки, с которых начинают чаще прочего
        return "monthly", "1.0" if name in {"p6-polniy-komplekt.html",
                                            "p7-dogovor-podryada.html"} else "0.9"
    if rel.startswith("articles/"):
        return "monthly", "0.8"
    if rel.startswith("materialy/"):
        return "monthly", "0.7"
    return None


def collect() -> list[tuple[str, str, str, str]]:
    rows = []
    for path in sorted(SITE.glob("*.html")) + sorted(SITE.glob("products/*.html")) \
            + sorted(SITE.glob("articles/*.html")) + sorted(SITE.glob("materialy/*.html")):
        rel = str(path.relative_to(SITE))
        kind = classify(rel)
        if not kind:
            continue
        freq, prio = kind
        loc = f"{BASE}/" if rel == "index.html" else \
              f"{BASE}/articles/" if rel == "articles/index.html" else f"{BASE}/{rel}"
        rows.append((loc, git_date(path), freq, prio))
    # Порядок: главная, разделы, статьи, материалы, правовые — как читается человеком
    order = {"1.0": 0, "0.9": 1, "0.8": 2, "0.7": 3, "0.3": 4, "0.2": 5}
    rows.sort(key=lambda r: (order.get(r[3], 9), r[0]))
    return rows


def render(rows) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mod, freq, prio in rows:
        lines.append(f"  <url><loc>{loc}</loc><lastmod>{mod}</lastmod>"
                     f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = collect()
    fresh = render(rows)
    target = SITE / "sitemap.xml"
    current = target.read_text(encoding="utf-8") if target.exists() else ""

    def urls(text): return set(re.findall(r"<loc>(.*?)</loc>", text))
    was, now = urls(current), urls(fresh)

    if "--verify" in sys.argv:
        added, gone = sorted(now - was), sorted(was - now)
        if added or gone:
            for u in added:
                print(f"  нет в записанной карте: {u}")
            for u in gone:
                print(f"  лишний в записанной карте: {u}")
            print(f"РАСХОЖДЕНИЕ: карта не совпадает с файлами сайта "
                  f"(+{len(added)} / -{len(gone)})")
            return 1
        print(f"Карта совпадает с файлами сайта: {len(now)} адресов.")
        return 0

    target.write_text(fresh, encoding="utf-8")
    print(f"sitemap.xml собран: {len(now)} адресов, "
          f"добавлено {len(now - was)}, убрано {len(was - now)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
