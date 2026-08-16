#!/usr/bin/env python3
"""Воронка продаж по уже объявленным целям счётчика.

Восемнадцать целей на сайте есть, снимки Метрики собираются
(`content/metrics/site-*.yaml`), и до сих пор ни один инструмент не
складывал их в воронку. Каждое число жило само по себе, а вопрос у
воронки один: где именно теряются люди.

Устройство отчёта держится на одном различении, и оно здесь главное.

**Ноль и «не измерено» — разные вещи, и путать их дороже, чем не считать
вовсе.** Метрика по необъявленной в счётчике цели молчит: в выгрузке её
просто нет. Пустое место читается как «никто не дошёл», а означает
«прибор не подключён». Снимок это различает полем
`goals_not_in_counter`, и отчёт обязан различать тоже: у такой ступени
стоит «не измерено», а не «0».

Второе: доля от малого знаменателя — не доля. При 34 визитах за неделю
конверсия шага «0 из 1» это не 0%, это отсутствие сигнала. Порог
знаменателя объявлен константой и назван в отчёте.

    python3 tools/funnel_report.py            # таблица
    python3 tools/funnel_report.py --write    # записать docs/FUNNEL.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "content" / "metrics"
OUT = ROOT / "docs" / "FUNNEL.md"

# Ниже этого знаменателя доля не называется. Число выбрано не «красивым»:
# при 34 визитах за неделю один клик даёт 3%, два — 6%, и разница между
# ними шум, а не рост. Тридцать — первая величина, при которой один
# случай перестаёт двигать долю на проценты.
MIN_DENOMINATOR = 30

# Дата, по которую включительно снимки считали переход на товар и на
# бесплатный материал неполно. Обработчик целей сверял подстроку
# '/products/' в атрибуте href, а 223 из 375 ссылок под целью записаны
# относительно, — считалась только часть сайта, и вся витрина в неё не
# входила. Дата стоит здесь, а не в тексте отчёта, потому что снимки
# накапливаются и граница нужна каждому следующему прогону.
BLIND_HREF_UNTIL = "2026-08-15"

# Воронка от входа до денег. Каждая ступень — набор целей: считается их
# сумма, потому что путей к ступени несколько, а ступень одна.
STEPS: list[tuple[str, list[str], str]] = [
    ("Пришли на сайт", [], "визиты за период"),
    ("Ушли с контента к товару или к бесплатному",
     ["article_to_product", "article_to_magnet", "cross_sell_click",
      "calculator_to_product", "calculator_diagnostic_click"],
     "разбор, калькулятор или допродажа по ситуации"),
    ("Открыли страницу товара", ["product_opened", "product_selected"],
     "страница товара или карточка каталога"),
    ("Положили в корзину", ["add_to_cart"], ""),
    ("Открыли оформление", ["checkout_open"], ""),
    ("Оплатили", ["purchase"], ""),
]

# Ветка бесплатного материала: она не ведёт к деньгам напрямую, и
# складывать её с покупкой в одну колонку значило бы считать разное.
MAGNET: list[tuple[str, list[str]]] = [
    ("Открыли бесплатный материал", ["magnet_opened"]),
    ("Скачали чек-лист", ["checklist_download"]),
    ("Оставили контакт", ["lead_sent"]),
]

# Диагностика — свой путь ко входу в товар.
DIAGNOSTIC: list[tuple[str, list[str]]] = [
    ("Начали диагностику", ["diagnostic_start"]),
    ("Дошли до сценария", ["diagnostic_complete"]),
    ("Считали калькулятором", ["calculator_use"]),
]

AFTER = [("Взяли предложение после покупки", ["upsell_click"])]


def snapshots() -> list[dict]:
    out = []
    for path in sorted(METRICS.glob("site-*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["_file"] = path.name
        out.append(data)
    return out


def value(snap: dict, goals: list[str]) -> tuple[int | None, list[str]]:
    """Сумма по целям ступени и список необъявленных.

    None означает «не измерено»: ни одна цель ступени в счётчике не
    объявлена, и ноль здесь был бы сообщением о мире, которого прибор не
    делал.
    """
    have = snap.get("goals") or {}
    missing = [g for g in goals if g not in have]
    known = [have[g] for g in goals if g in have]
    if not known:
        return None, missing
    return int(sum(known)), missing


def share(part: int | None, whole: int | None) -> str:
    if part is None or whole is None:
        return "—"
    if whole < MIN_DENOMINATOR:
        return f"нет сигнала (знаменатель {whole})"
    return f"{part / whole * 100:.1f}%"


def lines(snap: dict) -> list[str]:
    visits = int((snap.get("traffic") or {}).get("visits") or 0)
    out = [f"Снимок {snap['_file']}, период "
           f"{(snap.get('period') or {}).get('from')} — "
           f"{(snap.get('period') or {}).get('to')}; визитов {visits}", ""]

    prev: int | None = visits
    out.append(f"   {'ступень':<52}{'значение':>12}  доля от предыдущей")
    for name, goals, _note in STEPS:
        if not goals:
            out.append(f"   {name:<52}{visits:>12}  —")
            continue
        got, missing = value(snap, goals)
        shown = "не измерено" if got is None else str(got)
        # Ступень, у которой измерена часть путей, доли не имеет. «0 из 34»
        # при трёх неподключённых целях из пяти — это не ноль процентов,
        # это неполный прибор, и назвать это долей значило бы соврать
        # точным числом.
        if missing and got is not None:
            ratio = f"измерено не всё: молчат {', '.join(missing)}"
        else:
            ratio = share(got, prev)
        out.append(f"   {name:<52}{shown:>12}  {ratio}")
        prev = got if got is not None else prev

    for title, block in (("Ветка бесплатного материала", MAGNET),
                         ("Диагностика и калькулятор", DIAGNOSTIC),
                         ("После покупки", AFTER)):
        out.append("")
        out.append(f"   {title}")
        for name, goals in block:
            got, _missing = value(snap, goals)
            shown = "не измерено" if got is None else str(got)
            out.append(f"   {name:<52}{shown:>12}")
    return out


def summary(snaps: list[dict]) -> list[str]:
    if not snaps:
        return ["Снимков нет: сначала прогон .github/workflows/metrika.yml"]
    out = []
    if len(snaps) == 1:
        out.append("Снимок один. Ряда нет, сравнивать не с чем: любое число "
                   "здесь — точка, а не динамика.")
    else:
        out.append(f"Снимков {len(snaps)}: {snaps[0]['_file']} … "
                   f"{snaps[-1]['_file']}.")
    last = snaps[-1]
    visits = int((last.get("traffic") or {}).get("visits") or 0)
    if visits < MIN_DENOMINATOR:
        out.append(f"Визитов за период {visits} при пороге {MIN_DENOMINATOR}. "
                   "Доли по воронке не называются: один случай двигал бы их "
                   "на проценты, и это был бы шум, а не измерение.")
    unmeasured = []
    for name, goals, _n in STEPS:
        if not goals:
            continue
        got, missing = value(last, goals)
        if got is None:
            unmeasured.append(f"{name} ({', '.join(goals)})")
        elif missing:
            unmeasured.append(f"{name} — частично: {', '.join(missing)}")
    if unmeasured:
        out.append("Ступени, по которым прибор молчит, а не показывает ноль:")
        out.extend(f"  · {u}" for u in unmeasured)
        out.append("Цели заводит сам прогон `metrika.yml --create-goals`; "
                   "до этого пустое место в выгрузке — свойство счётчика, "
                   "а не поведение людей.")
    blind = [s["_file"] for s in snaps
             if str(s.get("snapshot_date") or "") <= BLIND_HREF_UNTIL]
    if blind:
        out.append("")
        out.append(f"Снимки до {BLIND_HREF_UNTIL} включительно считали переход "
                   "на товар и на бесплатный материал неполно, и их нули по "
                   "этим ступеням — не поведение людей:")
        out.extend(f"  · {name}" for name in blind)
        out.append("Обработчик сверял подстроку '/products/' в атрибуте href, "
                   "а 223 из 375 ссылок под целью записаны относительно "
                   "(`products/p1-…`, `../materialy/…`). Слепой была вся "
                   "витрина — главная и katalog.html. Исправлено 16.08.2026, "
                   "проверка `node tools/test_attribution_goals.js` в гейте; "
                   "сравнивать эти ступени можно только со снимками после "
                   "исправления.")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    snaps = snapshots()
    body: list[str] = []
    for snap in snaps:
        body.extend(lines(snap))
        body.append("")
    body.extend(summary(snaps))

    for line in body:
        print(line)

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        text = ["# Воронка по целям счётчика", "",
                "Собран `python3 tools/funnel_report.py --write` из снимков",
                "`content/metrics/site-*.yaml`. Каталог `content/` не",
                "деплоится, поэтому числа остаются внутренними, а отчёт —",
                "здесь.", "",
                "**Ноль и «не измерено» здесь разные вещи.** Метрика по цели,",
                "не объявленной в счётчике, молчит: в выгрузке её нет. Пустое",
                "место читается как «никто не дошёл», а означает «прибор не",
                "подключён».", "",
                f"**Доля от знаменателя меньше {MIN_DENOMINATOR} не",
                "называется.** При таком трафике один клик двигает её на",
                "проценты, и это шум, а не измерение.", "",
                "```"]
        text.extend(body)
        text.append("```")
        OUT.write_text("\n".join(text) + "\n", encoding="utf-8")
        print(f"\nзаписано: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
