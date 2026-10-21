#!/usr/bin/env python3
"""Не возвращает обсуждение возврата на продающие страницы товаров."""
from __future__ import annotations

import json
import re
import tempfile
from urllib.parse import urlsplit
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


def check_page(page: Path, root: Path = ROOT) -> None:
    html = page.read_text(encoding="utf-8")
    for phrase in RETIRED:
        assert phrase not in html, f"{page.name}: вернулся дисклеймер {phrase!r}"
    refresh = re.search(r'<meta\s+http-equiv="refresh"\s+content="0;url=([^"<>]+)"', html)
    if refresh:
        # Архивная страница должна вести к действующей системе с помощью
        # покупателю. Требовать продающий FAQ от самого редиректа бессмысленно.
        target_url = refresh.group(1)
        assert target_url.startswith("/products/") and ".." not in target_url
        assert 'name="robots" content="noindex,follow"' in html
        assert f'rel="canonical" href="https://nastoronepodryadchika.ru{target_url}"' in html
        target = root / urlsplit(target_url).path.lstrip("/")
        assert target != page and target.is_file(), f"{page.name}: цель редиректа отсутствует"
        target_html = target.read_text(encoding="utf-8")
        assert 'http-equiv="refresh"' not in target_html, "цепочка архивных редиректов"
        check_page(target, root)
    else:
        assert SUPPORT in html and "nastoronepodryadchika@yandex.ru" in html, (
            f"{page.name}: нет инструкции на случай проблем с получением файлов")
    for raw in re.findall(
        r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
    ):
        json.loads(raw)


def check_negative_cases() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "products").mkdir()
        page = root / "products" / "probe.html"
        page.write_text("<p>nastoronepodryadchika@yandex.ru</p>")
        try:
            check_page(page, root)
        except AssertionError:
            pass
        else:
            raise AssertionError("продающая страница без помощи ошибочно принята")
        page.write_text('<meta http-equiv="refresh" content="0;url=/products/missing.html">'
                        '<meta name="robots" content="noindex,follow">'
                        '<link rel="canonical" href="https://nastoronepodryadchika.ru/products/missing.html">')
        try:
            check_page(page, root)
        except AssertionError:
            pass
        else:
            raise AssertionError("битый архивный редирект ошибочно принят")


def main() -> None:
    check_negative_cases()
    assert len(PAGES) == 19, f"ожидалось 18 товаров и главная, найдено {len(PAGES)}"
    for page in PAGES:
        check_page(page)

    delivery = (ROOT / "payment-delivery.html").read_text(encoding="utf-8")
    assert "отправим файлы письмом" in delivery
    assert (ROOT / "refund.html").exists() and (ROOT / "offer.html").exists()
    print(f"Продающие страницы: {len(PAGES)}; дисклеймеров 0; помощь со скачиванием PASS")


if __name__ == "__main__":
    main()
