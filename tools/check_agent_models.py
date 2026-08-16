#!/usr/bin/env python3
"""У каждого исполнителя объявлен режим выбора модели. Сети не требует.

Политика канонически живёт в ai-business-os/docs/AI_Execution_Policy.md;
здесь её исполняемая часть по исполнителям этого репозитория.

Правило 3 политики Р-060: молчаливое наследование модели — риск, а не
умолчание. Замер 16.08.2026, из которого правило выросло: в шестнадцати
определениях из шестнадцати модель не задана, и в инциденте правового
контура P1 это дало 804 вызова исполнителей из 843 на `claude-opus-5`.

Проверка отвечает на один вопрос: **виден ли выбор**. Хороша ли выбранная
модель — вопрос следующего слоя, здесь он не задаётся и задаваться не
может: замеров качества по типам задач пока нет.

Главное свойство — новый исполнитель не проходит молча. Определение
появилось, записи в реестре нет — красный. Именно так молчаливое
наследование и возвращается: не правкой реестра, а новым файлом рядом.

    python3 tools/check_agent_models.py
    python3 tools/check_agent_models.py --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
РЕЕСТР = ROOT / "data" / "ai" / "agent-model-policy.yaml"
РЕЖИМЫ = {"router", "fixed", "inherit_approved", "unknown"}


def каталог(agents_dir: Path) -> set[str]:
    """Имена исполнителей по файлам, а не по списку: список устаревает."""
    return {p.stem for p in sorted(agents_dir.glob("*.md"))}


def разобрать(данные: dict, найденные: set[str]) -> list[str]:
    """Чистая функция: реестр против каталога → перечень дефектов."""
    дефекты: list[str] = []
    записи = данные.get("agents") or []

    объявленные: set[str] = set()
    for i, з in enumerate(записи):
        имя = str(з.get("agent") or "").strip()
        if not имя:
            дефекты.append(f"запись {i + 1}: нет поля agent")
            continue
        if имя in объявленные:
            дефекты.append(f"{имя}: объявлен дважды")
            continue
        объявленные.add(имя)

        режим = str(з.get("mode") or "").strip()
        if режим not in РЕЖИМЫ:
            дефекты.append(f"{имя}: режим «{режим or '—'}» не из "
                           f"{sorted(РЕЖИМЫ)}")
            continue
        if режим == "unknown":
            дефекты.append(f"{имя}: режим unknown — выбор модели не определён")
            continue
        if режим == "fixed":
            if not str(з.get("model") or "").strip():
                дефекты.append(f"{имя}: режим fixed без указания model")
            if not str(з.get("reason") or "").strip():
                дефекты.append(f"{имя}: режим fixed без причины")
        if режим == "inherit_approved" and not str(з.get("reason") or "").strip():
            # Без причины «наследуем» — это и есть молчаливое наследование,
            # только записанное. Ровно то, что правило запрещает.
            дефекты.append(f"{имя}: режим inherit_approved без причины")

    for имя in sorted(найденные - объявленные):
        дефекты.append(f"{имя}: исполнитель есть, записи в реестре нет")
    for имя in sorted(объявленные - найденные):
        дефекты.append(f"{имя}: запись в реестре есть, исполнителя нет")
    return дефекты


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="показать режимы")
    args = ap.parse_args()

    данные = yaml.safe_load(РЕЕСТР.read_text(encoding="utf-8"))
    agents_dir = ROOT / (данные.get("meta", {}).get("agents_dir")
                         or ".claude/agents")
    if not agents_dir.is_dir():
        print(f"Каталога исполнителей нет: {agents_dir}")
        return 1
    найденные = каталог(agents_dir)
    дефекты = разобрать(данные, найденные)

    if args.list:
        for з in данные.get("agents") or []:
            хвост = f" → {з['model']}" if з.get("model") else ""
            print(f"  {з.get('agent'):<22} {з.get('mode')}{хвост}")

    if дефекты:
        print(f"ВЫБОР МОДЕЛИ НЕ ОБЪЯВЛЕН: {len(дефекты)}\n")
        for д in дефекты:
            print(f"  • {д}")
        print("\nКаждый исполнитель обязан иметь запись в "
              "data/ai/agent-model-policy.yaml с режимом router, fixed или")
        print("inherit_approved. Наследование главной сессии — тоже решение,")
        print("и у него должна быть причина, которую можно предъявить.")
        return 1

    сводка: dict[str, int] = {}
    for з in данные.get("agents") or []:
        сводка[з["mode"]] = сводка.get(з["mode"], 0) + 1
    строка = ", ".join(f"{k} {v}" for k, v in sorted(сводка.items()))
    print(f"Исполнителей: {len(найденные)}, выбор модели объявлен у всех "
          f"({строка}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
