#!/usr/bin/env python3
"""Мост сайта: нативный запуск исполнителя не проходит мимо маршрутизатора.

Логика решения канонически живёт в соседнем репозитории —
`ai-business-os/tools/agent_bridge.py`, второго её изложения здесь нет.
Реестр при этом свой (`data/ai/agent-model-policy.yaml`), как и у проверки
`check_agent_models.py`: увидеть нового исполнителя можно только там, где
он лежит.

ПОЧЕМУ НЕ ПОЛНАЯ КОПИЯ. Копия на четыреста строк разъезжается на первой
правке. Здесь только то, что действительно своё: путь к реестру и путь к
соседу.

ЗАЩИТА НЕ ЗАВИСИТ ОТ СОСЕДА. Если `ai-business-os` рядом не оказалось,
богатое решение построить нечем — но запрет остаётся: режим `router`
получает отказ всё равно. Иначе отсутствие соседнего репозитория само
становилось бы лазейкой, а лазейка, открывающаяся от условий среды, — это
ровно тот дефект, ради которого мост и написан.

    python3 tools/agent_bridge.py --matrix
    python3 tools/agent_bridge.py hook
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
РЕЕСТР = ROOT / "data" / "ai" / "agent-model-policy.yaml"
ЖУРНАЛ = ROOT / "data" / "ai" / "bridge"
# Реестр называется явно: исполнители сайта живут здесь, маршруты и
# исполнение — у соседа. Без `--registry` названная команда не сработала бы,
# а отказ с нерабочей командой это петля, а не защита.
КОМАНДА = ("python3 ../ai-business-os/tools/agent_bridge.py run "
           "--registry " + str(ROOT / "data" / "ai" / "agent-model-policy.yaml") +
           " --agent {agent} --task-type {tt}")


def где_искали() -> list[Path]:
    """Указанное явно старше догадки: неверный указатель — это ответ «нет».

    Иначе опечатка в AI_BUSINESS_OS молча уводила бы на случайную копию
    рядом, а проверить отсутствие соседа стало бы нечем.
    """
    явный = os.environ.get("AI_BUSINESS_OS")
    if явный:
        return [Path(явный)]
    кандидаты = [ROOT.parent / "ai-business-os", Path("/home/user/ai-business-os")]
    видели, итог = set(), []
    for к in кандидаты:
        if str(к) not in видели:
            видели.add(str(к))
            итог.append(к)
    return итог


def сосед() -> Path | None:
    """Где лежит канонический мост. Наличие проверяется, а не предполагается."""
    for к in где_искали():
        if (к / "tools" / "agent_bridge.py").exists():
            return к
    return None


def канонический():
    к = сосед()
    if not к:
        return None
    sys.path.insert(0, str(к / "tools"))
    try:
        import agent_bridge as ab
    except ImportError:
        return None
    ab.настроить(реестр_путь=РЕЕСТР,
                 лестница_путь=к / "docs" / "Model_Ladder.yaml",
                 агенты=ROOT / ".claude" / "agents",
                 журнал=ЖУРНАЛ, команда=КОМАНДА)
    return ab


# ── Запасное решение: только запрет, без маршрутов ──────────────────────

def запрет_без_соседа(tool_input: dict, данные: dict) -> dict:
    """Соседа нет — маршрут назвать нечем, но наследование всё равно закрыто."""
    имя = str((tool_input or {}).get("subagent_type") or "").strip()
    if not имя:
        return {"permission": "pass", "code": "NO_SUBAGENT_TYPE"}
    записи = {str(з.get("agent")): з for з in (данные.get("agents") or [])
              if з.get("agent")}
    з = записи.get(имя)
    if з is None:
        # Определение есть, записи нет — новый исполнитель, положенный мимо
        # реестра: отказ. Определения нет вовсе — встроенный агент среды
        # (Explore, general-purpose и прочие), реестр про них не знает и
        # запрещать их незачем.
        свои = {p.stem for p in (ROOT / ".claude" / "agents").glob("*.md")}
        if имя not in свои:
            return {"permission": "allow", "code": "BUILTIN_AGENT",
                    "agent": имя, "mode": "builtin",
                    "reason": f"«{имя}» — встроенный агент среды"}
        return {"permission": "deny", "code": "UNKNOWN_AGENT", "agent": имя,
                "reason": f"исполнителя «{имя}» нет в реестре {РЕЕСТР.name}, "
                          f"а определение .claude/agents/{имя}.md есть"}
    режим = str(з.get("mode") or "")
    if режим == "inherit_approved":
        return {"permission": "allow", "code": "NATIVE_ALLOWED", "agent": имя,
                "mode": режим, "reason": str(з.get("reason") or "")}
    return {"permission": "deny", "code": "ROUTER_UNAVAILABLE", "agent": имя,
            "mode": режим, "task_type": з.get("task_type"),
            "reason": f"{имя}: режим «{режим}», маршрутизатор рядом не найден. "
                      f"Нативный запуск дал бы модель от среды, и отсутствие "
                      f"соседнего репозитория этого не оправдывает. "
                      f"Проверить: ls ../ai-business-os/tools/agent_bridge.py "
                      f"или задать AI_BUSINESS_OS."}


def реестр() -> dict:
    return yaml.safe_load(РЕЕСТР.read_text(encoding="utf-8")) or {}


def main() -> int:
    ab = канонический()

    if len(sys.argv) > 1 and sys.argv[1] == "hook":
        if ab:
            return ab.команда_hook()
        try:
            вход = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            return 0
        if вход.get("tool_name") != "Agent":
            return 0
        р = запрет_без_соседа(вход.get("tool_input") or {}, реестр())
        if р["permission"] == "pass":
            return 0
        вывод = {"hookEventName": "PreToolUse",
                 "permissionDecision": р["permission"],
                 "permissionDecisionReason": f"[{р['code']}] {р.get('reason','')}"}
        print(json.dumps({"hookSpecificOutput": вывод}, ensure_ascii=False))
        return 0

    д = реестр()
    ш = "{:<26} {:<12} {:<17} {:<7} {:<14} {}"
    print(ш.format("ИСПОЛНИТЕЛЬ", "ТИП РАБОТЫ", "РЕЖИМ", "NATIVE",
                   "МАРШРУТ", "ЗАПАСНОЙ ПУТЬ"))

    if ab:
        строки = ab.матрица(д, ab.лестница())
    else:
        # Итог тот же и считается так же: сводка не должна зависеть от того,
        # развёрнут ли рядом сосед, иначе гейт сайта проверял бы другое.
        print(f"# маршрутизатор рядом не найден "
              f"({', '.join(str(p) for p in где_искали())}) — "
              f"маршруты назвать нечем, запрет остаётся")
        строки = []
        for з in sorted(д["agents"], key=lambda з: з["agent"]):
            р = запрет_без_соседа({"subagent_type": з["agent"]}, д)
            строки.append({
                "agent": з["agent"], "task_type": з.get("task_type") or "—",
                "mode": з.get("mode") or "", "route": "недоступен",
                "native": "ДА" if р["permission"] == "allow" else "НЕТ",
                "fallback": "SAFE FAIL, наследования нет"})

    for с in строки:
        print(ш.format(с["agent"], с["task_type"], с["mode"], с["native"],
                       с["route"], с["fallback"]))
    роутеров = sum(1 for с in строки if с["mode"] == "router")
    закрыто = sum(1 for с in строки
                  if с["mode"] == "router" and с["native"] == "НЕТ")
    print(f"\nrouter-исполнителей {роутеров}, нативный путь закрыт у "
          f"{закрыто} из {роутеров}")
    return 0 if закрыто == роутеров else 1


if __name__ == "__main__":
    sys.exit(main())
