#!/usr/bin/env python3
"""Buyer support on live NSP storefront: actionable contact, not old-brand copy.

Current active product pages must explain help after unsuccessful delivery;
retired T6 must redirect new sales to P11 and retain a support contact for
historical orders. All 19 source pages must reject old-brand email.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "index.html", *sorted((ROOT / "products").glob("*.html"))]
SUPPORT = "Если письмо не пришло или ссылка не открывается"
ALT_SUPPORT = "Вопросы по получению:"
EMAIL = "nastoronepodryadchika@yandex.ru"
OLD_EMAIL = "marzhavbetone@yandex.ru"
RETIRED_NAME = "t6-kvartiry-vmesto-deneg.html"
RETIRED_MARKER = 'data-retired-route="t6-to-p11"'
RETIRED_DEST = 'href="/products/p11-raschet-metrami.html"'
RETIRED = (
    "А если не подойдёт",
    "Как устроен возврат?",
    "Можно ли вернуть цифровой продукт?",
    "Это юридическая консультация?",
    "Это заменяет юриста?",
    "не юридическая консультация",
    "Эти шесть документов — типовые шаблоны, а не гарантия взыскания",
    "Порядок возврата зависит от того, отправлена",
    "При технической проблеме в первую очередь восстанавливается",
)


def clean_body(html: str) -> str:
    """Avoid a FAQ JSON-LD claim falsely standing in for visible buyer help."""
    return re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.I)


def check_support(name: str, html: str) -> str:
    assert EMAIL in html and OLD_EMAIL not in html, (
        f"{name}: клиентская поддержка не использует новый адрес НСП")
    body = clean_body(html)
    assert f'mailto:{EMAIL}' in body, f"{name}: нет рабочей ссылки на поддержку"
    if RETIRED_MARKER in body:
        assert name == RETIRED_NAME, f"{name}: неожиданный закрытый маршрут"
        assert "Отдельная покупка T6 недоступна." in body
        assert "По ранее оформленному заказу" in body
        assert RETIRED_DEST in body
        assert "add-to-cart" not in body, f"{name}: закрытый товар снова продаётся"
        return "RETIRED_WITH_HISTORICAL_SUPPORT"
    assert name != RETIRED_NAME, "T6 active new-sales route reintroduced"
    if SUPPORT not in body:
        assert name == "p8-avans-po-dogovoru-subpodryada.html"
        assert ALT_SUPPORT in body, f"{name}: нет помощи при получении товара"
        return "ACTIVE_ALTERNATE_WORDING"
    return "ACTIVE_STANDARD_SUPPORT"


def negative_gates(pages: dict[str, str]) -> int:
    """Prove wrong contact, missing help and retired misrouting fail closed."""
    standard = pages["index.html"]
    assert SUPPORT in clean_body(standard)
    p8 = pages["p8-avans-po-dogovoru-subpodryada.html"]
    assert ALT_SUPPORT in clean_body(p8)
    legacy = pages[RETIRED_NAME]
    variants = [
        ("index.html", standard.replace(EMAIL, OLD_EMAIL)),
        ("index.html", standard.replace(f"mailto:{EMAIL}", "mailto:unknown@example.invalid")),
        ("index.html", standard.replace(SUPPORT, "Связь с поддержкой недоступна")),
        ("p8-avans-po-dogovoru-subpodryada.html", p8.replace(ALT_SUPPORT, "Нет поддержки:")),
        (RETIRED_NAME, legacy.replace(RETIRED_DEST, 'href="/products/t6-kvartiry-vmesto-deneg.html"')),
        (RETIRED_NAME, legacy.replace("По ранее оформленному заказу", "По вопросам")),
    ]
    for name, candidate in variants:
        assert candidate != pages[name], f"NEGATIVE_FIXTURE_UNCHANGED_{name}"
        try:
            check_support(name, candidate)
        except AssertionError:
            continue
        raise AssertionError("SUPPORT_NEGATIVE_GATE_FALSE_PASS_" + name)
    return len(variants)


def main() -> None:
    assert len(PAGES) == 19, f"ожидалось 18 товаров и главная, найдено {len(PAGES)}"
    pages: dict[str, str] = {}
    types: dict[str, int] = {}
    for page in PAGES:
        html = page.read_text(encoding="utf-8")
        pages[page.name] = html
        for phrase in RETIRED:
            assert phrase not in html, f"{page.name}: вернулся дисклеймер {phrase!r}"
        result = check_support(page.name, html)
        types[result] = types.get(result, 0) + 1
        for raw in re.findall(
            r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
        ):
            json.loads(raw)

    assert types == {
        "ACTIVE_STANDARD_SUPPORT": 17,
        "ACTIVE_ALTERNATE_WORDING": 1,
        "RETIRED_WITH_HISTORICAL_SUPPORT": 1,
    }, "SUPPORT_PAGE_CLASSIFICATION_DRIFT"
    delivery = (ROOT / "payment-delivery.html").read_text(encoding="utf-8")
    assert "отправим файлы письмом" in delivery
    assert f"mailto:{EMAIL}" in delivery and OLD_EMAIL not in delivery
    assert (ROOT / "refund.html").exists() and (ROOT / "offer.html").exists()
    negatives = negative_gates(pages)
    print(json.dumps({
        "status": "PASS", "buyer_pages": len(PAGES),
        "active_with_standard_support": types["ACTIVE_STANDARD_SUPPORT"],
        "active_with_alternate_support": types["ACTIVE_ALTERNATE_WORDING"],
        "retired_routes_with_historical_support": types["RETIRED_WITH_HISTORICAL_SUPPORT"],
        "old_brand_contacts": 0, "negative_gates": negatives,
        "production_writes": 0, "payments_created": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
