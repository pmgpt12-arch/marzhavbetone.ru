#!/usr/bin/env python3
"""Версия в ссылках на CSS и JS: правка стилей доезжает до телефона.

Зачем. `.htaccess` отдаёт css и js с `Cache-Control: max-age=604800,
immutable`. `immutable` — это не «храни неделю», а «неделю не спрашивай
сервер вовсе»: браузер не шлёт даже условный запрос и не смотрит ни на
ETag, ни на Last-Modified. Пока адрес файла не изменился, деплой до
открытого раньше телефона не доезжает.

Замер 11.08.2026, из-за которого инструмент и написан: правка пропорций
картинок ушла в main и была залита на сервер прогоном deploy.yml (09:11
UTC, success), а на айфоне владельца вёрстка осталась прежней. Ссылки на
стили версии не несли ни в одном файле; у скрипта версия была —
`attribution.js?v=4`.

Версия — восемь знаков sha1 от содержимого файла. Отсюда два свойства:
меняется только когда меняется сам файл, и повторный прогон ничего не
дублирует. Ручной счётчик `?v=5` этих свойств не даёт: его забывают
поднять ровно тогда, когда правка срочная.

    python3 tools/asset_versions.py           # показать, что изменится
    python3 tools/asset_versions.py --write   # проставить
    python3 tools/asset_versions.py --check   # код 1, если версии разошлись

Порядок: прогон делается последним перед коммитом — после правок стилей,
иначе версия встанет от предыдущего содержимого.

`--check` стоит в гейте выкладки, и стоит он там по замеру 16.08.2026.
Правка каталога ef05517 сменила catalog.css и desktop.css, а версии в
ссылках остались докоммитные — то есть правка доехала до сервера и не
доехала ни до одного браузера, открывавшего сайт в предыдущую неделю.
Дефект держался в main сутки, и ни одна проверка про него не сказала:
прогоны рендером стартуют с чистым браузером и кэша не видят. Инструмент
без кода возврата инструментом гейта не является — отсюда `--check`.
"""

import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Каталоги, которых на сервере нет и которые правкой ссылок не лечатся.
# `data` — сюда сохраняются страницы-фикстуры правового контура, снятые в
# кодировке источника: 26 файлов в data/legal/fixtures/pages не читаются как
# utf-8, и прогон падал на первом из них, не проставив версии нигде
# (замер 16.08.2026: `python3 tools/asset_versions.py` → UnicodeDecodeError).
SKIP_DIRS = ("content", ".git", "products-storage", "orders", "tools",
             "node_modules", ".claude", ".github", "data")

# href="styles.css" и src="/attribution.js" — вместе с уже стоящей версией,
# чтобы прогон её заменял, а не приписывал вторую.
LINK = re.compile(
    r'(?P<attr>\b(?:href|src)=")(?P<path>[^"?#]+\.(?:css|js))(?:\?[^"#]*)?(?P<tail>[^"]*)"'
)


def asset_path(html_file: str, url: str) -> str | None:
    """Файл на диске, на который указывает ссылка. None — если внешний."""
    if url.startswith(("http://", "https://", "//")):
        return None
    if url.startswith("/"):
        return os.path.join(ROOT, url.lstrip("/"))
    return os.path.normpath(os.path.join(os.path.dirname(html_file), url))


def version_of(path: str, cache: dict) -> str | None:
    if path not in cache:
        try:
            with open(path, "rb") as fh:
                cache[path] = hashlib.sha1(fh.read()).hexdigest()[:8]
        except OSError:
            cache[path] = None
    return cache[path]


def html_files() -> list[str]:
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name.endswith(".html"):
                out.append(os.path.join(base, name))
    return sorted(out)


def main() -> int:
    write = "--write" in sys.argv
    check = "--check" in sys.argv
    cache: dict = {}
    missing: set = set()
    stale: list = []
    changed_files = 0
    changed_links = 0

    for html in html_files():
        with open(html, encoding="utf-8") as fh:
            text = fh.read()

        def repl(m: re.Match) -> str:
            nonlocal changed_links
            path = asset_path(html, m.group("path"))
            if path is None:
                return m.group(0)
            version = version_of(path, cache)
            if version is None:
                missing.add(os.path.relpath(path, ROOT))
                return m.group(0)
            new = f'{m.group("attr")}{m.group("path")}?v={version}{m.group("tail")}"'
            if new != m.group(0):
                changed_links += 1
                was = (m.group(0).split("?v=", 1)[1].rstrip('"')
                       if "?v=" in m.group(0) else "нет версии")
                stale.append((os.path.relpath(html, ROOT), m.group("path"),
                              was, version))
            return new

        updated = LINK.sub(repl, text)
        if updated != text:
            changed_files += 1
            if write:
                with open(html, "w", encoding="utf-8") as fh:
                    fh.write(updated)

    if missing:
        print("не найдены на диске, версия не проставлена:")
        for name in sorted(missing):
            print(f"  {name}")

    if not changed_links:
        print("версии на месте, менять нечего")
        return 0

    verb = "проставлено" if write else "будет проставлено"
    print(f"{verb}: {changed_links} ссылок в {changed_files} файлах")

    if check:
        # `--check` блокирует, и вот чем это оплачено. Замер 16.08.2026:
        # правка каталога ef05517 меняла catalog.css (413a7fa0 → aa40453f) и
        # desktop.css (91aea4b6 → 4828cd8b), а katalog.html так и остался со
        # старыми версиями в ссылках. `.htaccess` отдаёт css с
        # `max-age=604800, immutable` — адрес не изменился, значит браузер
        # неделю не спрашивает сервер вовсе. Правка доехала до боевого
        # сервера и не доехала до владельца: на его экране осталась
        # докоммитная вёрстка, а любая проверка рендером стартует с чистым
        # браузером и потому всегда зелёная. Прибор мерял не то, что видит
        # глаз, ровно на этом месте.
        print()
        print("Версии в ссылках разошлись с содержимым файлов.")
        print("Стили доехали до сервера, но не доедут до открытого раньше "
              "браузера: css отдаётся immutable на неделю.")
        for html, asset, was, now in stale[:20]:
            print(f"  · {html}: {asset} {was} → {now}")
        if len(stale) > 20:
            print(f"  … и ещё {len(stale) - 20}")
        print("Починка: python3 tools/asset_versions.py --write")
        return 1

    if not write:
        print("прогон без изменений; чтобы записать — --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
