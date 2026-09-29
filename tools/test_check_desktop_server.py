#!/usr/bin/env python3
"""Сервер `check_desktop.py` отдаёт страницу, пока одно соединение молчит.

Замер 29.09.2026, Draft PR #317: job `render` упал на
`Page.goto: Timeout 30000ms exceeded` при переходе на `katalog.html`. Диффа
в страницах, вёрстке и самой проверке у PR не было. Из последних 100
прогонов workflow упал только этот.

Причина — в `serve()`: сайт отдавал однопоточный `socketserver.TCPServer`.
Если браузер откроет соединение и ничего по нему не пошлёт (так ведут себя
предварительные соединения Chromium), единственный поток сервера
блокируется на чтении из него. Остальные запросы страницы стоят в очереди,
`load` не наступает, и проверка падает, хотя сайт исправен. Разбор —
`tools/candidates/MB001_R2_P5_317_RENDER_TIMEOUT.md`.

Проверяется ровно этот отказ, без браузера — только стандартная
библиотека:

1. сервер из `check_desktop.serve()` при открытом молчащем соединении
   отдаёт `katalog.html` целиком и быстро;
2. при том же молчащем соединении сервер останавливается `shutdown()`, и
   проверка не висит на выходе;
3. сторож: на однопоточном `socketserver.TCPServer` с тем же обработчиком
   тот же запрос обязан упереться в лимит. Иначе детектор ничего не ловит,
   и зелёный результат ничего не значит.

У каждого сетевого шага свой таймаут, так что тест не зависает сам.

    python3 tools/test_check_desktop_server.py
    python3 -m pytest tools/test_check_desktop_server.py -q
"""
from __future__ import annotations

import functools
import http.client
import http.server
import socket
import socketserver
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_desktop as cd                               # noqa: E402

СТРАНИЦА = "/katalog.html"
ЛИМИТ = 3.0            # секунд на ответ; обычный ответ — сотые доли секунды


def молчащее_соединение(port: int) -> socket.socket:
    """TCP-соединение без единого байта запроса — как предварительное у Chromium."""
    s = socket.create_connection(("127.0.0.1", port), timeout=ЛИМИТ)
    time.sleep(0.2)     # сервер успевает принять его и сесть читать
    return s


def запрос(port: int) -> tuple[int, int]:
    """Статус и длина ответа на GET страницы; при зависании — socket.timeout."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=ЛИМИТ)
    try:
        conn.request("GET", СТРАНИЦА)
        ответ = conn.getresponse()
        return ответ.status, len(ответ.read())
    finally:
        conn.close()


def остановить(httpd: socketserver.BaseServer) -> bool:
    """shutdown() в отдельном потоке: True, если сервер остановился в лимит."""
    поток = threading.Thread(target=httpd.shutdown, daemon=True)
    поток.start()
    поток.join(ЛИМИТ)
    остановился = not поток.is_alive()
    if остановился:
        httpd.server_close()
    return остановился


def однопоточный() -> tuple[socketserver.TCPServer, int]:
    """Прежняя реализация `serve()` — для сторожа."""
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    port = cd.free_port()
    httpd = socketserver.TCPServer(
        ("127.0.0.1", port), functools.partial(Quiet, directory=str(cd.ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def ответ_при_молчащем_соединении(сервер) -> tuple[str | None, bool]:
    """(ошибка или None, остановился ли сервер) для сервера из фабрики."""
    httpd, port = сервер()
    idle = молчащее_соединение(port)
    ошибка = None
    try:
        статус, длина = запрос(port)
        if статус != 200 or длина == 0:
            ошибка = f"{СТРАНИЦА}: статус {статус}, {длина} байт"
    except (socket.timeout, TimeoutError) as e:
        ошибка = f"{СТРАНИЦА}: нет ответа за {ЛИМИТ:.0f} с ({type(e).__name__})"
    остановился = остановить(httpd)
    idle.close()
    if not остановился:
        # Однопоточный сервер освобождается, когда закрыто молчащее
        # соединение; дать ему довести shutdown, чтобы не оставлять поток.
        остановить(httpd)
    return ошибка, остановился


# ─────────────────────────────── проверки ───────────────────────────────

def test_страница_отдаётся_при_молчащем_соединении() -> None:
    ошибка, _ = ответ_при_молчащем_соединении(cd.serve)
    assert ошибка is None, (
        f"сервер check_desktop.py завис на молчащем соединении — {ошибка}. "
        "Так job render падает на Page.goto: Timeout (PR #317, 29.09.2026)")


def test_сервер_останавливается_при_молчащем_соединении() -> None:
    _, остановился = ответ_при_молчащем_соединении(cd.serve)
    assert остановился, (
        f"shutdown() сервера check_desktop.py не вернулся за {ЛИМИТ:.0f} с "
        "при открытом молчащем соединении")


def test_детектор_ловит_однопоточный_сервер() -> None:
    """Сторож: прежняя реализация обязана падать, иначе тест пустой."""
    ошибка, _ = ответ_при_молчащем_соединении(однопоточный)
    assert ошибка is not None, (
        "однопоточный TCPServer ответил при молчащем соединении — "
        "детектор зависания ничего не проверяет")


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
