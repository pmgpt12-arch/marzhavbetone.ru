#!/usr/bin/env python3
"""Заголовки и описания страниц: что дефект, а что замечание.

Критерий задан владельцем 14.08.2026 и записан здесь, потому что расходится
с привычным SEO-правилом. Фиксированного предела длины описания не
существует: сниппет режется по-разному на разных устройствах, а поисковик
вправе собрать его из текста страницы вместо `description`. Поэтому длина
здесь — замечание, а не ошибка.

Дефект (код 1):
  • одинаковое описание на двух и более страницах — обещание в выдаче
    перестаёт различать страницы;
  • одинаковый `<title>` на двух и более страницах;
  • пустой `<title>` или пустой `<h1>`.

Замечание (кода не меняет):
  • описание длиннее 200 знаков — хвост в выдачу может не попасть, и
    важное надо переносить в начало, а не механически резать до предела;
  • описания нет на странице, которая продвигается.

Служебные страницы (оферта, возврат, политика) в список «продвигается» не
входят: они нужны в индексе как подтверждение продавца, а не как точка
входа из поиска.

    python3 tools/check_meta.py
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLOBS = ("*.html", "articles/*.html", "products/*.html",
         "materialy/*.html", "demo/*.html")

# Не для поиска: служебные ответы кассы и тестовая страница.
NOT_FOR_SEARCH = {"success.html", "fail.html", "test-pokupka.html"}

# Продвигаются: разборы, товары, бесплатные материалы, витрины, калькулятор.
# Юридические страницы сюда не входят — см. заголовок файла.
SERVICE = {"offer.html", "payment-delivery.html", "privacy.html",
           "refund.html", "contacts.html"}

LONG = 200

RE_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
RE_DESC = re.compile(r'<meta\s+name="description"\s+content="([^"]*)"')
RE_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def pages() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for pattern in GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.name in NOT_FOR_SEARCH:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(ROOT).as_posix()
            title = RE_TITLE.search(text)
            desc = RE_DESC.search(text)
            h1 = RE_H1.search(text)
            out[rel] = {
                "title": title.group(1).strip() if title else "",
                "desc": desc.group(1).strip() if desc else "",
                "h1": (re.sub(r"<[^>]+>", "", h1.group(1)).strip()
                       if h1 else ""),
                "service": path.name in SERVICE,
            }
    return out


def main() -> int:
    data = pages()
    defects: list[str] = []
    notes: list[str] = []

    for rel, page in sorted(data.items()):
        if not page["title"]:
            defects.append(f"/{rel}: нет title")
        if not page["h1"]:
            defects.append(f"/{rel}: нет h1")
        if not page["desc"]:
            notes.append(f"/{rel}: нет описания"
                         + (" (служебная)" if page["service"] else ""))
        elif len(page["desc"]) > LONG:
            notes.append(f"/{rel}: описание {len(page['desc'])} знаков — "
                         f"хвост может не попасть в выдачу, важное в начало")

    for field, label in (("title", "одинаковый title"),
                         ("desc", "одинаковое описание")):
        groups: dict[str, list[str]] = defaultdict(list)
        for rel, page in data.items():
            if page[field]:
                groups[page[field]].append(rel)
        for value, rels in sorted(groups.items()):
            if len(rels) > 1:
                defects.append(
                    f"{label} на {len(rels)} страницах: "
                    f"{', '.join('/' + r for r in sorted(rels))}\n"
                    f"      «{value[:80]}»")

    print(f"Страниц проверено: {len(data)}")

    if notes:
        print(f"\n## Замечания — {len(notes)}")
        for n in notes:
            print(f"   • {n}")

    if defects:
        print(f"\n## ДЕФЕКТЫ — {len(defects)}")
        for d in defects:
            print(f"   ✗ {d}")
        return 1

    print("\nДефектов нет: title и h1 на месте, дублирующихся заголовков и "
          "описаний нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
