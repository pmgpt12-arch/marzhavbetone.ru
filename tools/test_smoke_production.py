#!/usr/bin/env python3
"""Регресс на проверку подтверждённых роботов в боевом дымовом прогоне.

GitHub runner может подставить User-Agent OAI-SearchBot, но не может
подтвердить принадлежность IP сети настоящего робота. Cloudflare отклоняет
такую имитацию правилом Bot Management. Ответ 403 с заголовками Cloudflare
и CF-Ray поэтому означает «проба не подтверждена», а не «настоящий робот
закрыт от сайта».

Запуск без pytest: python3 tools/test_smoke_production.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import smoke_production as smoke  # noqa: E402


BODY = """<!doctype html>
<html lang="ru"><head><title>Проверка</title>
<link rel="canonical" href="https://marzhavbetone.ru/">
</head><body><h1>Проверка</h1></body></html>
"""


def проверить(отказы: dict[str, tuple[int, dict[str, str]]]) -> list[str]:
    исходный_fetch = smoke.fetch
    по_агенту = {agent: name for name, agent in smoke.AGENTS.items()}

    def подмена(url: str, agent: str) -> tuple[int, dict, str]:
        имя = по_агенту[agent]
        if имя in отказы:
            код, заголовки = отказы[имя]
            return код, заголовки, ""
        return 200, {}, BODY

    smoke.fetch = подмена
    try:
        расхождения: list[str] = []
        smoke.check("https://marzhavbetone.ru", "/", расхождения)
        return расхождения
    finally:
        smoke.fetch = исходный_fetch


def test_cloudflare_rejection_of_spoofed_oai_is_inconclusive() -> None:
    расхождения = проверить({
        "OAI-SearchBot": (403, {"Server": "cloudflare", "CF-Ray": "probe-AMS"}),
    })
    assert расхождения == [], расхождения


def test_oai_403_without_cf_ray_still_fails() -> None:
    расхождения = проверить({"OAI-SearchBot": (403, {"Server": "cloudflare"})})
    assert any("OAI-SearchBot получает код 403" in x for x in расхождения)


def test_oai_403_from_origin_still_fails() -> None:
    расхождения = проверить({
        "OAI-SearchBot": (403, {"Server": "nginx", "CF-Ray": "fake"}),
    })
    assert any("OAI-SearchBot получает код 403" in x for x in расхождения)


def test_other_bot_403_from_cloudflare_still_fails() -> None:
    расхождения = проверить({
        "Googlebot": (403, {"Server": "cloudflare", "CF-Ray": "probe-AMS"}),
    })
    assert any("Googlebot получает код 403" in x for x in расхождения)


def test_oai_server_error_still_fails() -> None:
    расхождения = проверить({
        "OAI-SearchBot": (500, {"Server": "cloudflare", "CF-Ray": "probe-AMS"}),
    })
    assert any("OAI-SearchBot получает код 500" in x for x in расхождения)


def main() -> int:
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as error:
            failed += 1
            print(f"  ✗ {test.__name__}: {error}")
        else:
            print(f"  ✓ {test.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
