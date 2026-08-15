#!/usr/bin/env python3
"""Мастер-бэклог: зависимости, критерии приёмки, ворота фаз.

Держит третье требование этапа — не масштабироваться, пока предыдущий
слой не доказал работу. Правило проверяемое, а не декларативное: задача,
у которой зависимость не закрыта, не может стоять в работе.

Дефект (код 1):
  • зависимость указывает на несуществующую задачу;
  • задача в работе или закрыта, а её зависимость — нет;
  • закрытая задача без доказательства (`evidence`);
  • задача без критерия приёмки;
  • неизвестный статус или приоритет;
  • кольцевая зависимость.

Замечание (кода не меняет):
  • задача заблокирована решением владельца — это не дефект системы,
    но и не то, о чём можно молчать.

    python3 tools/check_backlog.py            # проверка
    python3 tools/check_backlog.py --next     # что можно брать сейчас
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "data" / "ops" / "backlog.csv"

COLS = ["task_id", "system", "cluster", "priority", "business_impact",
        "dependency", "owner", "status", "evidence", "expected_result",
        "acceptance_criteria", "metric", "deadline"]

STATUSES = {"todo", "in_progress", "blocked", "done", "dropped"}
PRIORITIES = {"P0", "P1", "P2"}
# Статусы, при которых зависимость обязана быть закрыта.
REQUIRES_DEPS = {"in_progress", "done"}


def load() -> list[dict]:
    with BACKLOG.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLS:
            print("СХЕМА РАЗОШЛАСЬ")
            print(f"  объявлено: {', '.join(COLS)}")
            print(f"  в файле:   {', '.join(reader.fieldnames or [])}")
            sys.exit(1)
        return list(reader)


def deps_of(row: dict) -> list[str]:
    raw = row["dependency"].strip()
    if not raw or raw == "-":
        return []
    return [d.strip() for d in raw.split(",") if d.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--next", action="store_true",
                    help="что можно брать в работу сейчас")
    args = ap.parse_args()

    rows = load()
    by_id = {r["task_id"]: r for r in rows}
    defects: list[str] = []
    notes: list[str] = []

    for row in rows:
        tid = row["task_id"]
        status = row["status"].strip()
        if status not in STATUSES:
            defects.append(f"{tid}: неизвестный статус «{status}»")
        if row["priority"].strip() not in PRIORITIES:
            defects.append(f"{tid}: неизвестный приоритет "
                           f"«{row['priority']}»")
        if not row["acceptance_criteria"].strip():
            defects.append(f"{tid}: нет критерия приёмки — «сделано» будет "
                           f"решаться на глаз")
        if status == "done" and not row["evidence"].strip():
            defects.append(f"{tid}: закрыта без доказательства")

        for dep in deps_of(row):
            if dep not in by_id:
                defects.append(f"{tid}: зависимость {dep} не существует")
                continue
            dep_status = by_id[dep]["status"].strip()
            if status in REQUIRES_DEPS and dep_status != "done":
                defects.append(
                    f"{tid}: статус «{status}» при незакрытой зависимости "
                    f"{dep} («{dep_status}») — слой не доказал работу")

        if status == "blocked" and row["owner"].strip() == "owner":
            notes.append(f"{tid}: ждёт решения владельца — "
                         f"{row['business_impact']}")

    # Кольца: задача не может зависеть от себя через цепочку.
    def ring(tid: str, seen: tuple[str, ...] = ()) -> list[str] | None:
        if tid in seen:
            return list(seen[seen.index(tid):]) + [tid]
        for dep in deps_of(by_id.get(tid, {"dependency": ""})):
            if dep in by_id:
                found = ring(dep, seen + (tid,))
                if found:
                    return found
        return None

    for row in rows:
        found = ring(row["task_id"])
        if found:
            defects.append(f"кольцевая зависимость: {' → '.join(found)}")
            break

    if args.next:
        ready = [r for r in rows
                 if r["status"].strip() in {"todo", "in_progress"}
                 and all(by_id.get(d, {}).get("status") == "done"
                         for d in deps_of(r))]
        ready.sort(key=lambda r: (r["priority"], r["deadline"]))
        print("Можно брать сейчас — зависимости закрыты:\n")
        for r in ready:
            print(f"  {r['priority']}  {r['task_id']}  {r['expected_result']}")
            print(f"        приёмка: {r['acceptance_criteria']}")
        if not ready:
            print("  ничего: всё либо закрыто, либо ждёт зависимости")
        return 0

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("Задач: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    if notes:
        print(f"\n## Ждут владельца — {len(notes)}")
        for n in notes:
            print(f"   • {n}")

    if defects:
        print(f"\n## ДЕФЕКТЫ — {len(defects)}")
        for d in defects:
            print(f"   ✗ {d}")
        return 1

    print("\nДефектов нет: у каждой задачи критерий приёмки, закрытые "
          "подтверждены, порядок фаз не нарушен.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
