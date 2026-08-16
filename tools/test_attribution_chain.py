#!/usr/bin/env python3
"""Сквозной регресс атрибуции: переход из канала → статья → товар → оформление.

Зачем отдельная проверка. Метку ставит `post_telegram.py`, принимает
`attribution.js`, несёт в заказ `app.js`, пишет `payment.php`, называет в
цели `success.html` — пять файлов, и разрыв в любом из них молча
обнуляет ответ на вопрос «какой канал принёс деньги». Ни одна текстовая
проверка этого не ловит: код на месте в каждом файле по отдельности.

Замер 16.08.2026, из которого проверка появилась: цепочка оказалась целой
— первое касание пережило переходы по сайту, `telegram` доехал до
параметров цели `purchase`. Регресс нужен, чтобы это осталось верным
после следующей правки корзины или счётчика.

Покупка не совершается: заказ не создаётся, `payment.php` не вызывается.
Проверяется пакет, который ушёл бы на сервер, и параметры цели, которые
ушли бы в счётчик, — собранные теми же выражениями, что в коде страниц.

    python3 tools/test_attribution_chain.py

Код возврата 2 — «не запускалась» (нет playwright, браузера или php),
а не «прошла».
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Сервер именно PHP и поиск соседнего хромиума — там же, где у корзины:
# причина в test_cart.py, повторять её второй раз незачем.
from test_cart import chromium_nearby, serve  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

LANDING = "/articles/srok-garantiynogo-uderzhaniya.html"
PRODUCT = "/products/p1-oplata-po-ks2.html"
CAMPAIGN = "srok-uderzhaniya"
VARIANT = "proba-tsepochki"

# Счётчик в проверке не поднимается: цели перехватываются заглушкой, иначе
# прогон слал бы в боевую Метрику выдуманные заказы.
YM_STUB = """
window.METRIKA_ID = 111149105;
window.__goals = [];
window.ym = function (id, action, name, params) {
  if (action === 'reachGoal') window.__goals.push(name);
};
window.dataLayer = window.dataLayer || [];
"""

PURCHASE_PARAMS = """(function () {
  var attribution = (typeof window.mvbAttribution === 'function'
    ? window.mvbAttribution() : {}) || {};
  var firstTouch = attribution.first || {};
  var lastTouch = attribution.last || {};
  return {
    first_touch_source: firstTouch.source || 'direct',
    first_touch_medium: firstTouch.medium || '',
    first_touch_campaign: firstTouch.campaign || '',
    last_touch_source: lastTouch.source || firstTouch.source || 'direct',
    landing_page: firstTouch.landing || ''
  };
})()"""

ORDER_PAYLOAD = """(function () {
  return {
    items: JSON.parse(localStorage.getItem('marzhavbetone-cart') || '[]'),
    attribution: typeof window.mvbAttribution === 'function' ? window.mvbAttribution() : {}
  };
})()"""


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Проверка не запускалась: нет playwright.", file=sys.stderr)
        return 2

    bad: list[str] = []
    server, port = serve()
    base = f"http://127.0.0.1:{port}"
    # Ссылка собирается так же, как её соберёт отправка поста.
    tg_url = (f"{base}{LANDING}?utm_source=telegram&utm_medium=post"
              f"&utm_campaign={urllib.parse.quote(CAMPAIGN)}"
              f"&utm_content={VARIANT}")
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
            page.add_init_script(YM_STUB)

            page.goto(tg_url, wait_until="load")
            first = (page.evaluate(
                "window.mvbAttribution ? window.mvbAttribution() : {}") or {}).get("first", {})
            for field, expected in (("source", "telegram"), ("medium", "post"),
                                    ("campaign", CAMPAIGN), ("content", VARIANT)):
                if first.get(field) != expected:
                    bad.append(f"лендинг не принял utm_{field}: "
                               f"{first.get(field)!r} вместо {expected!r}")
            if first.get("landing") != LANDING:
                bad.append(f"страница входа записана как {first.get('landing')!r}")

            # Переход по сайту не должен подменять источник: клик по своей же
            # ссылке приходит с собственным referrer, и наивная запись
            # последнего касания стёрла бы канал на «marzhavbetone.ru».
            page.goto(f"{base}{PRODUCT}", wait_until="load")
            after = page.evaluate("window.mvbAttribution()")
            if after.get("first", {}).get("source") != "telegram":
                bad.append("первое касание не пережило переход на товар")
            if after.get("last", {}).get("source") != "telegram":
                bad.append("последнее касание подменилось своим же переходом")

            page.click(".product-hero .add-to-cart")
            page.wait_for_timeout(200)
            checkout = page.locator("#cart-checkout")
            if checkout.count():
                checkout.first.click()
                page.wait_for_timeout(300)
            goals = page.evaluate("window.__goals")
            for goal in ("add_to_cart", "checkout_open"):
                if goal not in goals:
                    bad.append(f"цель {goal} не отправлена; отправлены: {goals}")

            payload = page.evaluate(ORDER_PAYLOAD)
            sent = payload.get("attribution", {}).get("first", {})
            if not payload.get("items"):
                bad.append("в пакете заказа нет позиций — корзина не собралась")
            for field in ("source", "medium", "campaign", "content"):
                if not sent.get(field):
                    bad.append(f"пакет заказа уходит без {field}")

            params = page.evaluate(PURCHASE_PARAMS)
            if params.get("first_touch_source") != "telegram":
                bad.append(f"цель purchase назвала бы источник "
                           f"{params.get('first_touch_source')!r}")
            if params.get("first_touch_campaign") != CAMPAIGN:
                bad.append("цель purchase уходит без кампании")

            browser.close()
    finally:
        server.terminate()

    if bad:
        print(f"## ДЕФЕКТЫ — {len(bad)}")
        for line in bad:
            print(f"   ✗ {line}")
        return 1
    print("Цепочка атрибуции цела: метка → лендинг → товар → корзина → "
          "оформление → параметры цели purchase.")
    print("   " + json.dumps(params, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
