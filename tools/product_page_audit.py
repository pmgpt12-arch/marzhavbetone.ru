#!/usr/bin/env python3
"""Разбор страниц товаров по смыслу блоков, а не по буквальным заголовкам.

Задание требует проверить тринадцать блоков и прямо оговаривает: не искать
дословный H2 с этими названиями, оценивать смысл. Отсюда устройство —
каждый блок ищется несколькими признаками сразу: заголовком, служебным
классом, характерной конструкцией текста. Совпал любой — блок есть.

Что это **не** делает: не оценивает качество текста. Инструмент отвечает
на вопрос «есть ли на странице ответ покупателю», а не «хорош ли он».
Второе — работа человека, и подменять её счётом блоков нельзя.

Статусы:

    GOOD        нет ни одного пропущенного обязательного блока
    MINOR FIX   пропущены только неденежные блоки — продаётся, но хуже
    MAJOR FIX   нет цены, кнопки или состава — то есть покупать нечем

    python3 tools/product_page_audit.py            # таблица
    python3 tools/product_page_audit.py --write    # записать отчёт
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "PRODUCT_PAGE_AUDIT.md"

# Блок → (признаки, обязателен ли, денежный ли). Признаки — регулярные
# выражения по видимому тексту и по разметке.
BLOCKS: list[tuple[str, list[str], bool, bool]] = [
    ("PROBLEM", [r"проблем", r"если у вас", r"когда заказчик", r"не оплачива",
                 r"не подписыва", r"вернул", r"удержал", r"требуют", r"банкрот"], True, False),
    ("RESULT", [r"что вы получ", r"результат", r"на выходе", r"чтобы получить",
                r"поможет", r"закрыва"], True, False),
    ("WHO", [r"кому подойдёт", r"кому подходит", r"берите, если", r"для кого",
             r"подойдёт"], True, False),
    ("WHEN", [r"когда применя", r"когда брать", r"если .{0,40}ещё не",
              r"на каком этапе", r"берите, если"], True, False),
    ("MECHANISM", [r"как это работает", r"порядок действий", r"алгоритм",
                   r"механизм", r"пошагов"], True, False),
    ("CONTENTS", [r"что входит", r"состав комплекта", r"product-documents",
                  r"файл(?:ов|а)? в word"], True, True),
    ("WHY DOCS", [r"зачем нужен", r"зачем каждый", r"почему именно",
                  r"что делает каждый", r"словарь полей", r"памятк"], False, False),
    ("LIMITATIONS", [r"ограничени", r"не является юридическ", r"не гаранти",
                     r"важно, прочитайте", r"это типовые шаблоны"], True, False),
    ("PRICE", [r"<strong>[\d\s]+\s*₽", r"data-price=", r"\d[\d\s]*₽"], True, True),
    ("CTA", [r"add-to-cart", r"добавить в корзину", r"купить"], True, True),
    ("FREE ENTRY", [r"materialy/", r"бесплатн"], False, False),
    ("RELATED ARTICLE", [r"\.\./articles/", r"полезные материалы"], False, False),
    ("CROSS-SELL", [r"cross-sell", r"если ваша ситуация также"], True, False),
]


def visible(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    # Разметка нужна для признаков вроде data-price и класса блока,
    # поэтому в поиске участвует и она.
    return (html.unescape(re.sub(r"\s+", " ", text)) + " " + raw).lower()


def audit(path: Path) -> tuple[list[str], str]:
    text = visible(path)
    missing = []
    for name, patterns, required, _money in BLOCKS:
        if not any(re.search(p, text, re.I) for p in patterns):
            if required:
                missing.append(name)
    money_missing = [m for m in missing
                     if any(m == n and money for n, _p, _r, money in BLOCKS)]
    # MAJOR — только когда покупать нечем: нет цены, кнопки или состава.
    # Прежняя версия ставила MAJOR за три пропущенных блока любого рода, и
    # это расходилось с описанием тут же в файле: страница без «кому
    # подойдёт» продаётся, просто хуже. Расхождение кода с собственной
    # документацией — тот же дефект, что и с чужой.
    if money_missing:
        status = "MAJOR FIX"
    elif not missing:
        status = "GOOD"
    else:
        status = "MINOR FIX"
    return missing, status


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    pages = sorted((ROOT / "products").glob("*.html"))
    rows = []
    for path in pages:
        missing, status = audit(path)
        rows.append((path.name, status, missing))

    counts = {"GOOD": 0, "MINOR FIX": 0, "MAJOR FIX": 0}
    for _n, status, _m in rows:
        counts[status] += 1
    print(f"Страниц товаров: {len(rows)} — "
          f"GOOD {counts['GOOD']}, MINOR FIX {counts['MINOR FIX']}, "
          f"MAJOR FIX {counts['MAJOR FIX']}")
    for name, status, missing in rows:
        if missing:
            print(f"   {status:<10} {name}: нет — {', '.join(missing)}")

    if args.write:
        lines = ["# Разбор страниц товаров — 15.08.2026", "",
                 "Собран `tools/product_page_audit.py`. Блоки ищутся по смыслу:",
                 "заголовком, служебным классом или характерной конструкцией —",
                 "дословного H2 не требуется, как и оговорено в задании.", "",
                 "**Чего этот разбор не делает:** он не оценивает качество текста.",
                 "Ответ на вопрос «есть ли на странице ответ покупателю» —",
                 "машинный; «хорош ли ответ» — работа человека, и подменять её",
                 "счётом блоков нельзя.", "",
                 f"Итог: страниц {len(rows)} — GOOD {counts['GOOD']}, "
                 f"MINOR FIX {counts['MINOR FIX']}, MAJOR FIX {counts['MAJOR FIX']}.",
                 "", "| страница | статус | чего не найдено |", "|---|---|---|"]
        for name, status, missing in rows:
            lines.append(f"| `{name}` | **{status}** | "
                         f"{', '.join(missing) if missing else '—'} |")
        lines += ["", "## Как читать пропуски", "",
                  "`WHY DOCS`, `FREE ENTRY` и `RELATED ARTICLE` объявлены",
                  "необязательными: у входной ступени за 990 ₽ отдельный разбор",
                  "каждого файла избыточен, а бесплатный вход есть не у каждой",
                  "боли. Их отсутствие в таблице не показано.", "",
                  "`MAJOR FIX` ставится только когда нет цены, кнопки или",
                  "состава — то есть когда покупать буквально нечем."]
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"записано: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
