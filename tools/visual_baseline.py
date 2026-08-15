#!/usr/bin/env python3
"""Снимки и замеры главной: до правок и после, одним и тем же способом.

Смысл в том, чтобы «стало лучше» было утверждением с числом, а не
впечатлением. Инструмент делает пять ширин, полностраничные снимки,
снимки отдельных блоков и `measurements.json` — высоту страницы, высоту
окна и число экранов на каждой ширине, плюс высоту каждой секции.

Число экранов считается как `scrollHeight / innerHeight` и записывается
отдельно от пикселей: порог в пикселях не наказывает за низкий монитор,
но и не показывает, сколько человек реально прокрутит на 1366×768.
Нужны оба.

    python3 tools/visual_baseline.py --out reports/visual-.../baseline
    python3 tools/visual_baseline.py --out ... --page katalog.html
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import socket
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VIEWPORTS = [(1366, 768), (1440, 900), (1920, 1080), (430, 932), (390, 844)]

# Блоки, которые снимаются отдельно: по ним и оценивается визуальный класс.
BLOCKS = {
    "hero": ".hero",
    "situations": "#situations",
    "cases": "#cases",
    "analyses": "#materials",
    "products": "#catalog",
}


def serve() -> tuple[socketserver.TCPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    httpd = socketserver.TCPServer(("127.0.0.1", port),
                                   functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def chromium() -> str | None:
    import os
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    for c in sorted(root.glob("chromium-*/chrome-linux/chrome"), reverse=True):
        return str(c)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--page", default="index.html")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Не запускалось: нет playwright", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    httpd, port = serve()
    data: dict = {"page": args.page, "viewports": {}, "sections": {}, "order": []}

    try:
        with sync_playwright() as p:
            exe = chromium()
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"http://127.0.0.1:{port}/{args.page}", wait_until="load")
                page.wait_for_timeout(400)

                measured = page.evaluate("""() => ({
                    scrollHeight: document.documentElement.scrollHeight,
                    scrollWidth: document.documentElement.scrollWidth,
                    innerHeight: window.innerHeight,
                    innerWidth: window.innerWidth,
                })""")
                measured["screens"] = round(
                    measured["scrollHeight"] / measured["innerHeight"], 2)
                data["viewports"][f"{width}x{height}"] = measured

                page.screenshot(path=str(out / f"full-{width}.png"), full_page=True)

                if width == 1440:
                    data["order"] = page.evaluate(
                        """() => [...document.querySelectorAll('main > section')]
                             .map(s => s.id || s.className)""")
                    data["sections"] = page.evaluate(
                        """() => Object.fromEntries(
                             [...document.querySelectorAll('main > section')].map(s =>
                               [s.id || s.className.split(' ')[0],
                                Math.round(s.getBoundingClientRect().height)]))""")
                    for name, selector in BLOCKS.items():
                        node = page.locator(selector).first
                        if node.count():
                            try:
                                node.screenshot(path=str(out / f"{name}-1440.png"))
                            except Exception as exc:
                                print(f"  {name}: снимок не сделан — {exc}")
                page.close()
            browser.close()
    finally:
        httpd.shutdown()

    (out / "measurements.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Снимки и замеры: {out}")
    for key, m in data["viewports"].items():
        flag = " ← уходит вбок" if m["scrollWidth"] > m["innerWidth"] else ""
        print(f"  {key:<10} {m['scrollHeight']:>6}px / {m['innerHeight']}px "
              f"= {m['screens']:>5} экрана{flag}")
    if data["sections"]:
        print("\nВысота секций на 1440:")
        for name, h in sorted(data["sections"].items(), key=lambda kv: -kv[1]):
            print(f"  {h:>5}px  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
