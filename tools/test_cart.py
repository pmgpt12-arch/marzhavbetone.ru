#!/usr/bin/env python3
"""Регресс корзины: кнопка на странице товара кладёт в корзину тот товар и ту цену.

Зачем отдельная проверка. Корзина связывает разметку с кассой двумя
строками — `data-sku` и `data-price` у кнопки — и связывает их **по
значению**, а не по ссылке. Пока цену назначает сервер (`test_price_authority.php`),
подделка через консоль ничего не даёт; но разошедшийся `data-sku` даёт
другое: покупатель кладёт в корзину не тот комплект, видит не ту цену и
уходит. Ни одна текстовая проверка этого не ловит — разметка правильная,
ссылки целы, цены в конфиге на месте.

Замер, из которого проверка появилась, — не гипотеза: при переносе
каталога на отдельную страницу 15.08.2026 сопоставление шло по
`item.name === button.dataset.product`, то есть по видимому названию.
Правка названия товара в разметке рвала корзину молча.

Проверяется на каждой странице товара: клик по кнопке даёт ровно одну
позицию, `sku` совпадает с описанным в кассе, сумма — с ценой оттуда же,
повторный клик позицию не удваивает.

    python3 tools/test_cart.py
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "products-config.php"


def catalog() -> dict[str, int]:
    """SKU → цена в копейках, из того же файла, откуда её берёт касса."""
    text = CONFIG.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^\s*'([a-z0-9]+)'\s*=>\s*\[(.*?)^\s*\],",
                         text, re.S | re.M):
        price = re.search(r"'price'\s*=>\s*(\d+)", m.group(2))
        if price:
            out[m.group(1)] = int(price.group(1))
    return out


def serve() -> tuple[subprocess.Popen, int]:
    """Сайт отдаётся встроенным сервером PHP, а не питоновским.

    Причина замером: `app.js` подключён через `app-script.php`, и питоновский
    http.server отдаёт этот файл исходником. Браузер получает PHP-текст
    вместо кода, падает на первом же `<`, корзина не инициализируется — и
    проверка краснеет на всех восемнадцати страницах, не найдя ни одного
    настоящего дефекта. Ложная краснота дешевле ложной зелени, но обе
    бесполезны.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        ["php", "-S", f"127.0.0.1:{port}", "-t", str(ROOT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.1)
    return proc, port


def chromium_nearby() -> Path | None:
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    for candidate in sorted(root.glob("chromium-*/chrome-linux/chrome"), reverse=True):
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Проверка не запускалась: нет playwright.", file=sys.stderr)
        return 2

    prices = catalog()
    pages = sorted((ROOT / "products").glob("*.html"))
    server, port = serve()
    bad: list[str] = []
    try:
        with sync_playwright() as p:
            near = chromium_nearby()
            try:
                browser = (p.chromium.launch(executable_path=str(near)) if near
                           else p.chromium.launch())
            except Exception as exc:
                print(f"Проверка не запускалась: браузер не стартовал — {exc}",
                      file=sys.stderr)
                return 2
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            for path in pages:
                rel = path.relative_to(ROOT).as_posix()
                page.goto(f"http://127.0.0.1:{port}/{rel}", wait_until="load")
                page.evaluate("localStorage.clear()")
                page.reload(wait_until="load")
                button = page.locator(".product-hero .add-to-cart").first
                if button.count() == 0:
                    bad.append(f"{rel}: кнопки покупки нет в первом экране")
                    continue
                sku = button.get_attribute("data-sku")
                # Страница обязана продавать тот товар, про который она.
                # Без этой строки проверка проходила на подменённом sku:
                # цена сходилась с кассой — просто с ценой чужого товара.
                # Имя файла здесь независимый свидетель: оно задано планом
                # линейки и проверяется `check_products.py`.
                expected = path.name.split("-", 1)[0]
                if sku != expected:
                    bad.append(f"{rel}: кнопка продаёт {sku!r}, "
                               f"страница про {expected!r}")
                button.click()
                # Первый клик открывает панель корзины, и её подложка
                # перехватывает следующий клик. Панель закрывается, и только
                # тогда проверяется, что повторное нажатие не удваивает позицию.
                page.click("#cart-close")
                button.click()
                page.wait_for_timeout(80)
                cart = page.evaluate(
                    "() => JSON.parse(localStorage.getItem('marzhavbetone-cart') || '[]')")
                count = page.inner_text("#cart-count")
                if len(cart) != 1:
                    bad.append(f"{rel}: в корзине {len(cart)} позиций вместо одной")
                    continue
                item = cart[0]
                if item.get("sku") != sku:
                    bad.append(f"{rel}: в корзину лёг sku {item.get('sku')!r}, "
                               f"на кнопке {sku!r}")
                if sku not in prices:
                    bad.append(f"{rel}: sku {sku!r} не описан в products-config.php")
                elif item.get("price") != prices[sku]:
                    bad.append(f"{rel}: цена в корзине {item.get('price')} коп., "
                               f"в кассе {prices[sku]} коп.")
                if count.strip() != "1":
                    bad.append(f"{rel}: счётчик корзины показывает {count!r}")
            browser.close()
    finally:
        server.terminate()

    if bad:
        print(f"Корзина: расхождений {len(bad)} на {len(pages)} страницах")
        for line in bad:
            print(f"  · {line}")
        return 1
    print(f"Корзина: {len(pages)} страниц товаров, sku и цена совпадают с кассой, "
          f"повторный клик позицию не удваивает")
    return 0


if __name__ == "__main__":
    sys.exit(main())
