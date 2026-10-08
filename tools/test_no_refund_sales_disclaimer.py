#!/usr/bin/env python3
"""Не возвращает обсуждение возврата на продающие страницы товаров."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "index.html", *sorted((ROOT / "products").glob("*.html"))]
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
SUPPORT = "Если письмо не пришло или ссылка не открывается"


def main() -> None:
    assert len(PAGES) == 19, f"ожидалось 18 товаров и главная, найдено {len(PAGES)}"
    for page in PAGES:
        html = page.read_text(encoding="utf-8")
        for phrase in RETIRED:
            assert phrase not in html, f"{page.name}: вернулся дисклеймер {phrase!r}"
        assert SUPPORT in html and "marzhavbetone@yandex.ru" in html, (
            f"{page.name}: нет инструкции на случай проблем с получением файлов")
        for raw in re.findall(
            r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
        ):
            json.loads(raw)

    delivery = (ROOT / "payment-delivery.html").read_text(encoding="utf-8")
    assert "отправим файлы письмом" in delivery
    assert (ROOT / "refund.html").exists() and (ROOT / "offer.html").exists()
    print(f"Продающие страницы: {len(PAGES)}; дисклеймеров 0; помощь со скачиванием PASS")


if __name__ == "__main__":
    main()
