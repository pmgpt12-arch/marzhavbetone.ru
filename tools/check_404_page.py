#!/usr/bin/env python3
"""Своя страница 404 стоит и объявлена в обоих конфигах веб-сервера.

Дефект, ради которого написана проверка, был виден только снаружи:
несуществующий адрес на живом сайте отвечал кодом 404, но телом страницы
хостинга reg.ru — 769 КБ, ссылки на покупку домена, хостинга и VPS,
одна ссылка назад. nginx-конфиг репозитория называл `error_page 404
/404.html`, а сам файл не существовал; `.htaccess` про 404 молчал вовсе.
Из репозитория дефект не виден никак — проверка запирает то, что
существует здесь: файл, объявление в .htaccess, объявление в nginx-конфиге,
и то, что страница ведёт читателя назад своими ссылками.

Проверяется:

  1. 404.html существует в корне и закрыт от индексации (noindex);
  2. .htaccess объявляет ErrorDocument 404 /404.html — на reg.ru сайт
     обслуживает Apache, nginx-конфиг у владельца не активен;
  3. nginx-marzhavbetone.conf держит то же объявление — конфиги не
     расходятся, если владелец перенесёт сайт под свой nginx;
  4. страница несёт каноническую шапку (это отдельно сторожит check_nav)
     и все её ссылки абсолютные: Apache отдаёт 404.html под исходным
     адресом, и относительная ссылка с глубины /articles/... уводила бы
     читателя в несуществующий путь;
  5. цели ссылок страницы существуют в репозитории — 404, ведущая в 404,
     недопустима.

    python3 tools/check_404_page.py

Код возврата 1, если страница отсутствует, не объявлена или ведёт в никуда.
"""
from __future__ import annotations

import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parents[1]
СТРАНИЦА = SITE / "404.html"
HTACCESS = SITE / ".htaccess"
NGINX = SITE / "nginx-marzhavbetone.conf"

АДРЕС = "/404.html"


def цель_существует(путь: str) -> bool:
    """Путь вида /diagnostika.html или /articles/ — файл внутри репозитория."""
    чистый = путь.split("#")[0].split("?")[0]
    # pathlib: присоединение пути с ведущим «/» даёт абсолютный путь мимо
    # корня — снимаем его, корень и есть SITE.
    чистый = чистый.lstrip("/")
    if чистый in ("",):
        return (SITE / "index.html").is_file()
    if чистый.endswith("/"):
        return (SITE / чистый / "index.html").is_file()
    return (SITE / чистый).is_file()


def main() -> int:
    беды = []
    if not СТРАНИЦА.is_file():
        print(f"  ✗ {АДРЕС} не существует — посетитель чужого 404 получает "
              "страницу хостинга (замер 21.09.2026: reg.ru, 769 КБ, "
              "ссылки на продажу хостинга)")
        return 1

    html = СТРАНИЦА.read_text(encoding="utf-8")
    if not re.search(r'<meta name="robots" content="[^"]*noindex', html):
        беды.append("404.html отдаётся на любом мусорном адресе — без noindex "
                    "она бы индексировалась и вытесняла живые страницы")

    ht = HTACCESS.read_text(encoding="utf-8") if HTACCESS.is_file() else ""
    if not re.search(rf"^\s*ErrorDocument\s+404\s+{re.escape(АДРЕС)}\s*$", ht, re.M):
        беды.append(".htaccess не объявляет ErrorDocument 404 /404.html — "
                    "на reg.ru сайт обслуживает Apache, и без строки в "
                    ".htaccess страница не подключена")

    ngx = NGINX.read_text(encoding="utf-8") if NGINX.is_file() else ""
    if f"error_page 404 {АДРЕС}" not in ngx:
        беды.append("nginx-marzhavbetone.conf не объявляет error_page 404 "
                    "/404.html — конфиги расходятся")

    if "<header" not in html:
        беды.append("404.html без канонической шапки — читатель чужого "
                    "адреса не имеет ни одного пути в разделы сайта")

    относительные = [
        h for h in re.findall(r'(?:href|src)="([^"]+)"', html)
        if not h.startswith(("/", "#", "mailto:", "http")) and h
    ]
    if относительные:
        беды.append("404.html несёт относительные ссылки " + ", ".join(относительные[:5]) +
                    " — Apache отдаёт страницу под исходным адресом, и ссылка "
                    "с глубины /articles/... ведёт в несуществующий путь")

    цели = [h for h in re.findall(r'href="([^"]+)"', html)
            if h.startswith("/") and not h.startswith("//")]
    битые = [ц for ц in цели if not цель_существует(ц)]
    if битые:
        беды.append("404.html ведёт в несуществующие цели: " + ", ".join(битые))

    for беда in беды:
        print(f"  ✗ {беда}")
    проверено = 5
    print(f"\nПроверок страницы 404: {проверено}, дефектов: {len(беды)}")
    if not беды:
        print("404.html стоит, объявлена в .htaccess и nginx-конфиге, "
              "ссылки назад ведут в существующие цели.")
    return 1 if беды else 0


if __name__ == "__main__":
    sys.exit(main())
