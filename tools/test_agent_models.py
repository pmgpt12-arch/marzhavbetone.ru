#!/usr/bin/env python3
"""Что проверка выбора модели обязана ловить. Сети не требует.

Реестр — единственное место, где виден выбор модели исполнителя, значит
единственное, через которое молчаливое наследование может вернуться
незамеченным: новым файлом рядом, режимом `unknown`, «наследуем» без
причины, `fixed` без модели. Здесь закреплено, что не может.

Схема и набор случаев общие с `ai-business-os/tests/test_agent_models.py`:
реестры разные, потому что исполнители разные, а правило одно.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_agent_models import разобрать  # noqa: E402

РЕЕСТР = ROOT / "data" / "ai" / "agent-model-policy.yaml"


def данные() -> dict:
    return yaml.safe_load(РЕЕСТР.read_text(encoding="utf-8"))


def имена() -> set[str]:
    return {з["agent"] for з in данные()["agents"]}


def test_репозиторий_сегодня_сходится():
    p = subprocess.run([sys.executable, "tools/check_agent_models.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr


def test_новый_исполнитель_без_записи_краснеет():
    """Мутация A. Так молчаливое наследование и возвращается — новым файлом."""
    дефекты = разобрать(данные(), имена() | {"новый-исполнитель"})
    assert any("новый-исполнитель" in d and "записи в реестре нет" in d
               for d in дефекты), дефекты


def test_режим_unknown_краснеет():
    """Мутация B. `unknown` — не способ отложить решение до зелёного теста."""
    d = данные()
    d["agents"][0]["mode"] = "unknown"
    assert any("unknown" in x for x in разобрать(d, имена()))


def test_fixed_без_модели_краснеет():
    """Мутация C."""
    d = данные()
    d["agents"][0].update(mode="fixed", reason="потому что", model=None)
    assert any("fixed без указания model" in x for x in разобрать(d, имена()))


def test_inherit_approved_без_причины_краснеет():
    """Мутация D. «Наследуем» без причины — то же наследование, но записанное."""
    d = данные()
    d["agents"][0].update(mode="inherit_approved", reason="")
    assert any("inherit_approved без причины" in x
               for x in разобрать(d, имена()))


def test_корректная_запись_проходит():
    """Мутация E, обратная: набор обязан уметь и зеленеть."""
    assert разобрать(данные(), имена()) == []


def test_снятая_запись_обнажает_исполнителя():
    d = данные()
    снят = d["agents"].pop(0)["agent"]
    assert any(снят in x and "записи в реестре нет" in x
               for x in разобрать(d, имена()))


def test_запись_без_исполнителя_краснеет():
    d = данные()
    d["agents"].append({"agent": "которого-нет", "mode": "router"})
    assert any("которого-нет" in x and "исполнителя нет" in x
               for x in разобрать(d, имена()))


def test_дубль_записи_краснеет():
    d = данные()
    d["agents"].append(dict(d["agents"][0]))
    assert any("объявлен дважды" in x for x in разобрать(d, имена()))


def test_неизвестный_режим_краснеет():
    d = данные()
    d["agents"][0]["mode"] = "cheap"
    assert any("не из" in x for x in разобрать(d, имена()))


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
