#!/usr/bin/env python3
"""Сервер `check_mobile.py` отдаёт страницу, пока одно соединение молчит.

Тот же отказ, что у `check_desktop.py` (`tools/test_check_desktop_server.py`,
разбор — `tools/candidates/MB001_R2_P5_317_RENDER_TIMEOUT.md`).
`check_mobile.py` отдавал сайт однопоточным `socketserver.TCPServer`.
Соединение, по которому браузер ничего не прислал, занимало единственный
поток, и `Page.goto` падал по таймауту при исправном сайте. Шаг «Телефон —
390px» идёт в job `render` первым.

Проверяется при открытом молчащем TCP-соединении:
1. сервер из `check_mobile.serve()` отдаёт `katalog.html`;
2. `shutdown()` возвращается, и проверка не висит на выходе.

Детектор общий с `test_check_desktop_server.py`. Там же сторож: на
однопоточном `TCPServer` детектор обязан сработать. У каждого сетевого
шага свой таймаут, так что тест не зависает сам.

    python3 tools/test_check_mobile_server.py
    python3 -m pytest tools/test_check_mobile_server.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_mobile as cm                                # noqa: E402
from test_check_desktop_server import (                  # noqa: E402
    ЛИМИТ, ответ_при_молчащем_соединении)


def test_страница_отдаётся_при_молчащем_соединении() -> None:
    ошибка, _ = ответ_при_молчащем_соединении(cm.serve)
    assert ошибка is None, (
        f"сервер check_mobile.py завис на молчащем соединении — {ошибка}. "
        "Так job render падает на Page.goto: Timeout (разбор #317, 29.09.2026)")


def test_сервер_останавливается_при_молчащем_соединении() -> None:
    _, остановился = ответ_при_молчащем_соединении(cm.serve)
    assert остановился, (
        f"shutdown() сервера check_mobile.py не вернулся за {ЛИМИТ:.0f} с "
        "при открытом молчащем соединении")


def main() -> int:
    провал = 0
    for имя, проверка in sorted(globals().items()):
        if not имя.startswith("test_"):
            continue
        try:
            проверка()
        except AssertionError as ошибка:
            провал += 1
            print(f"ПРОВАЛ  {имя}\n  {ошибка}")
        else:
            print(f"ок      {имя}")
    return 1 if провал else 0


if __name__ == "__main__":
    sys.exit(main())
