#!/usr/bin/env python3
"""Сверка целей: что код шлёт против того, что объявлено инструментом.

Появилась 15.08.2026, и появилась не на пустом месте. В `CLAUDE.md` уже
записан случай: в `GOAL_ORDER` не было `calculator_use`,
`calculator_to_product` и `purchase`, страницы их слали, а Метрика по
необъявленной цели **молчит, а не ошибается**. Расхождение не давало ни
ошибки, ни пустого значения — цели просто не существовало, и нашлось это
живым прогоном. Там же записано: «сплошной сверки `GOAL_ORDER` с вызовами
`mvbTrackGoal` нет, и при добавлении следующей цели это повторится молча».

Повторилось. Замер 15.08.2026: `diagnostic_start` и `diagnostic_complete`
шлются страницей диагностики и в `GOAL_ORDER` отсутствуют. То есть вся
воронка диагностики — от входа до выбора комплекта — не считалась вовсе.

Проверка смотрит в обе стороны, и вторая важна не меньше первой:

  · цель шлётся кодом, но не объявлена → Метрика её молча теряет;
  · цель объявлена, но код её не шлёт → мёртвая цель, по ней всегда ноль,
    и этот ноль читается как «ничего не происходит», хотя означает
    «никто не звонит».

Имена целей берутся из вызовов `mvbTrackGoal(...)` и `trackGoal(...)`,
включая тернарную форму `cond ? 'a' : 'b'` — четыре цели живут именно так,
и разбор, который её не понимает, объявил бы их мёртвыми.

    python3 tools/check_goals.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRIKA = ROOT / "tools" / "metrika_report.py"

SKIP_DIRS = ("content/", ".claude/", "node_modules/", ".git/")

# Цели, которые объявлены намеренно и шлются не кодом сайта. Пусто:
# сегодня таких нет. Список существует, чтобы исключение записывалось
# сюда с причиной, а не пряталось ослаблением проверки.
DECLARED_WITHOUT_CODE: dict[str, str] = {}


def fired_goals() -> dict[str, set[str]]:
    """Имена целей, которые действительно уходят из кода, и где они стоят."""
    out: dict[str, set[str]] = {}
    for path in sorted(ROOT.glob("**/*")):
        if path.suffix not in (".html", ".js") or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(SKIP_DIRS):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for call in re.finditer(r"(?:mvbTrackGoal|trackGoal)\s*\(([^)]*)\)", text):
            for name in re.findall(r"['\"]([a-z][a-z0-9_]*)['\"]", call.group(1)):
                out.setdefault(name, set()).add(rel)
        # Прямой вызов счётчика в обход обёртки. Так уходит `purchase` из
        # success.html — вместе с параметрами заказа, которых обёртка не
        # принимает. Разбор, знающий только обёртку, объявил бы самую
        # денежную цель мёртвой; поймано первым же прогоном.
        for call in re.finditer(r"ym\s*\([^,]+,\s*['\"]reachGoal['\"]\s*,\s*['\"]([a-z][a-z0-9_]*)['\"]",
                                text):
            out.setdefault(call.group(1), set()).add(rel)
    return out


def declared_goals() -> list[str]:
    text = METRIKA.read_text(encoding="utf-8")
    block = re.search(r"GOAL_ORDER\s*=\s*\[(.*?)\]", text, re.S)
    if not block:
        raise SystemExit("в tools/metrika_report.py не найден GOAL_ORDER")
    return re.findall(r"['\"]([a-z][a-z0-9_]*)['\"]", block.group(1))


def main() -> int:
    fired = fired_goals()
    declared = declared_goals()

    undeclared = sorted(set(fired) - set(declared))
    dead = sorted(set(declared) - set(fired) - set(DECLARED_WITHOUT_CODE))
    duplicates = sorted({g for g in declared if declared.count(g) > 1})

    problems = 0
    if undeclared:
        problems += len(undeclared)
        print("ЦЕЛЬ ШЛЁТСЯ, НО НЕ ОБЪЯВЛЕНА — Метрика её молча теряет:")
        for name in undeclared:
            where = ", ".join(sorted(fired[name])[:3])
            print(f"   ✗ {name} — шлётся из {where}")
    if dead:
        problems += len(dead)
        print("ЦЕЛЬ ОБЪЯВЛЕНА, НО КОД ЕЁ НЕ ШЛЁТ — по ней всегда ноль:")
        for name in dead:
            print(f"   ✗ {name}")
    if duplicates:
        problems += len(duplicates)
        print("ЦЕЛЬ ОБЪЯВЛЕНА ДВАЖДЫ:")
        for name in duplicates:
            print(f"   ✗ {name}")

    print(f"\nЦелей в коде: {len(fired)}; объявлено: {len(declared)}; "
          f"расхождений: {problems}")
    if problems == 0:
        print("Дефектов нет: код и объявленный список сходятся.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
