#!/usr/bin/env python3
"""Мост сайта: четыре поисковых исполнителя не уходят на модель среды.

Богатая приёмка живёт у соседа (`ai-business-os/tests/test_agent_bridge.py`)
вместе с логикой решения. Здесь проверяется то, что своё: реестр сайта,
поиск соседа и — главное — что запрет держится, когда соседа рядом нет.

    python3 tools/test_agent_bridge.py
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import agent_bridge as мост          # noqa: E402


def реестр() -> dict:
    return yaml.safe_load(мост.РЕЕСТР.read_text(encoding="utf-8"))


class Реестр(unittest.TestCase):

    def test_все_четверо_объявлены(self):
        имена = {з["agent"] for з in реестр()["agents"]}
        файлы = {p.stem for p in (ROOT / ".claude" / "agents").glob("*.md")}
        self.assertEqual(имена, файлы)
        self.assertEqual(len(имена), 4)

    def test_все_четверо_router(self):
        режимы = {з["agent"]: з["mode"] for з in реестр()["agents"]}
        self.assertEqual(set(режимы.values()), {"router"})

    def test_у_каждого_объявлен_тип_работы(self):
        for з in реестр()["agents"]:
            self.assertTrue(з.get("task_type"), з["agent"])


class ЗапретБезСоседа(unittest.TestCase):
    """Отсутствие соседнего репозитория не должно открывать нативный путь."""

    def test_router_отклоняется_и_без_маршрутизатора(self):
        for з in реестр()["agents"]:
            р = мост.запрет_без_соседа({"subagent_type": з["agent"]}, реестр())
            self.assertEqual(р["permission"], "deny", з["agent"])
            self.assertEqual(р["code"], "ROUTER_UNAVAILABLE")

    def test_причина_называет_проверяемую_команду(self):
        р = мост.запрет_без_соседа({"subagent_type": "marzha-seo-auditor"},
                                   реестр())
        self.assertIn("ls ../ai-business-os", р["reason"])

    def test_свой_исполнитель_мимо_реестра_отклоняется(self):
        """Файл в .claude/agents есть, записи нет — так наследование и
        возвращается. Берём настоящее имя и убираем его из реестра."""
        д = реестр()
        д["agents"] = [з for з in д["agents"]
                       if з["agent"] != "marzha-seo-auditor"]
        р = мост.запрет_без_соседа({"subagent_type": "marzha-seo-auditor"}, д)
        self.assertEqual(р["code"], "UNKNOWN_AGENT")

    def test_встроенный_агент_среды_не_блокируется(self):
        """Explore и general-purpose не наши: определения в репозитории нет."""
        for имя in ("Explore", "general-purpose", "Plan"):
            р = мост.запрет_без_соседа({"subagent_type": имя}, реестр())
            self.assertEqual(р["permission"], "allow", имя)
            self.assertEqual(р["code"], "BUILTIN_AGENT", имя)

    def test_ограниченный_инструментом_пропускается(self):
        д = {"agents": [{"agent": "x", "mode": "inherit_approved",
                         "reason": "браузер"}]}
        р = мост.запрет_без_соседа({"subagent_type": "x"}, д)
        self.assertEqual(р["permission"], "allow")

    def test_без_имени_исполнителя_мост_не_вмешивается(self):
        р = мост.запрет_без_соседа({"prompt": "поискать"}, реестр())
        self.assertEqual(р["permission"], "pass")


def запустить(*аргументы, вход="", сосед=True):
    """Прогон настоящим процессом. `сосед=False` — как в гейте сайта.

    Гейт разворачивает один репозиторий, соседнего там нет вовсе. Проверять
    мост только рядом с соседом значило бы не проверять его в той среде,
    где он и работает чаще всего.
    """
    env = {**__import__("os").environ}
    if not сосед:
        env["AI_BUSINESS_OS"] = "/nonexistent-neighbour"
    p = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "agent_bridge.py"), *аргументы],
        input=вход, capture_output=True, text=True, cwd=ROOT, env=env)
    return p


class Хук(unittest.TestCase):

    def прогон(self, вход: dict, сосед=True) -> dict:
        p = запустить("hook", вход=json.dumps(вход), сосед=сосед)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else {}

    def test_поисковый_исполнитель_отклоняется(self):
        о = self.прогон({"session_id": "t", "tool_name": "Agent",
                         "tool_input": {"subagent_type": "marzha-seo-auditor",
                                        "prompt": "разбор"}})
        решение = о["hookSpecificOutput"]
        self.assertEqual(решение["hookEventName"], "PreToolUse")
        self.assertEqual(решение["permissionDecision"], "deny")

    def test_отклоняется_и_когда_соседа_нет(self):
        о = self.прогон({"session_id": "t", "tool_name": "Agent",
                         "tool_input": {"subagent_type": "marzha-seo-auditor",
                                        "prompt": "разбор"}}, сосед=False)
        решение = о["hookSpecificOutput"]
        self.assertEqual(решение["permissionDecision"], "deny")
        self.assertIn("ROUTER_UNAVAILABLE", решение["permissionDecisionReason"])

    def test_чужой_инструмент_проходит_молча(self):
        self.assertEqual(
            self.прогон({"session_id": "t", "tool_name": "Bash",
                         "tool_input": {"command": "ls"}}), {})

    def test_мусор_на_входе_не_блокирует_работу(self):
        p = запустить("hook", вход="не json")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip(), "")


class Матрица(unittest.TestCase):
    """Итог одинаков в обеих средах: сосед меняет подробности, не вердикт."""

    def проверить(self, сосед: bool):
        p = запустить("--matrix", сосед=сосед)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("нативный путь закрыт у 4 из 4", p.stdout)
        self.assertNotIn(" ДА ", p.stdout)

    def test_с_маршрутизатором(self):
        self.проверить(сосед=True)

    def test_без_маршрутизатора(self):
        self.проверить(сосед=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
