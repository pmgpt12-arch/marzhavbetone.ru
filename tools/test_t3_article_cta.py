#!/usr/bin/env python3
"""Ступень t3 доступна из статей, где разобрана её ситуация, и по своей цене.

Комплект «Односторонний акт или зачёт: возражения в срок» — входная ступень
двух кластеров диагностики: «Работы выполнены, но не приняты» (S-2) и
«Часть суммы удержана» (S-4). До 19.09.2026 из статей на него не вело ни
одной ссылки.

Проверка закрывает этот разрыв и держит две вещи, обе — состояние сайта:

  · в двух статьях, где связка доказана, ссылка на карточку t3 есть;
  · названная рядом с ней цена совпадает с ценой в `products-config.php` —
    иначе статья и страница оплаты разойдутся молча.

Своей копии названия, адреса и цены у проверки нет: всё берётся из
конфигурации, единственного места, где это задано.

Списка «сюда ссылку не ставить» здесь нет намеренно. Где ставить ссылку, а
где нет, в спорных случаях решает владелец; проверка, запрещающая ему
поставить её, подменяет решение и делает его правку красным CI. Поэтому
список только положительный и только из доказанных случаев.

Требования к тексту подписи ссылки проверка тоже не предъявляет: соседние
строки-ступени на сайте сокращают названия товаров («Заказчик не
оплачивает работы» вместо полного), и правило «подпись = полное имя»
действовало бы на два выхода из сорока одной статьи.

    python3 tools/test_t3_article_cta.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"

SKU = "t3"

# Статьи, где связка с t3 доказана содержанием и графом продукта.
ОБЯЗАНЫ_ВЕСТИ = {
    "raboty-ne-prinyaty":
        "разбирает односторонний акт и называет действие t3 — возражение в срок",
    "garantiynoe-uderzhanie-v-ks-2-i-ks-3":
        "разбирает переименование удержания в зачёт по ст. 410 ГК РФ",
}


def канон() -> tuple[str, int]:
    """Адрес карточки и цена t3 — из конфигурации сайта, а не отсюда."""
    config = (ROOT / "products-config.php").read_text(encoding="utf-8")
    block = config[config.index("function mvb_products()"):]
    m = re.search(rf"'{SKU}'\s*=>\s*\[\s*\n\s*'name'\s*=>\s*'[^']*',"
                  rf"\s*\n\s*'price'\s*=>\s*(\d+)", block)
    assert m, f"{SKU} не найден в products-config.php"

    карточки = sorted(p.name for p in (ROOT / "products").glob(f"{SKU}-*.html"))
    assert len(карточки) == 1, f"ожидалась одна карточка {SKU}, найдено {карточки}"
    return f"/products/{карточки[0]}", int(m.group(1)) // 100


def статья(slug: str) -> str:
    return html.unescape((ARTICLES / f"{slug}.html").read_text(encoding="utf-8"))


def _цифры(текст: str) -> str:
    return re.sub(r"\D", "", текст)


def test_утверждённые_статьи_ведут_на_t3() -> None:
    адрес, _ = канон()
    нет = [f"{slug}: нет ссылки на {адрес} — {причина}"
           for slug, причина in sorted(ОБЯЗАНЫ_ВЕСТИ.items())
           if адрес not in статья(slug)]
    assert not нет, "\n      ".join([""] + нет)


def test_цена_рядом_со_ссылкой_совпадает_с_конфигурацией() -> None:
    """Цена в CTA — не независимый литерал, а то же число, что в каталоге.

    Без этой сверки правка цены в `products-config.php` оставляет в статьях
    прежнюю, и расхождение видит только покупатель на странице оплаты.
    """
    адрес, цена = канон()
    беды = []
    for slug in sorted(ОБЯЗАНЫ_ВЕСТИ):
        текст = статья(slug)
        названо = re.findall(
            rf'href="{re.escape(адрес)}"[^>]*>.*?</a>\s*,\s*([\d\s  ]+)\s*₽',
            текст, re.S)
        if not названо:
            беды.append(f"{slug}: рядом со ссылкой на t3 цена не названа")
            continue
        for найдено in названо:
            if _цифры(найдено) != str(цена):
                беды.append(f"{slug}: в статье «{найдено.strip()} ₽», "
                            f"в products-config.php {цена} ₽")
    assert not беды, "\n      ".join([""] + беды)


def test_t3_остаётся_входной_ступенью_своих_кластеров() -> None:
    """Основание связки — граф продукта, а не память автора.

    Перестанет t3 быть входной ступенью кластеров ks и uderzhanie —
    основание ставить его в эти статьи исчезнет, и проверка это назовёт.
    """
    адрес, _ = канон()
    source = (ROOT / "diagnostika.html").read_text(encoding="utf-8")
    scenarios = json.loads(re.search(r"const SCENARIOS = (\[.*?\]);",
                                     source, re.S).group(1))
    кластеры = {sc["pain_id"] for sc in scenarios
                if (sc.get("entry") or {}).get("url") == адрес}
    assert {"ks", "uderzhanie"} <= кластеры, кластеры


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {str(e)[:400]}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
