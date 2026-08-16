#!/usr/bin/env python3
"""Запускает проверки репозитория после правки файла.

Проверки перечислены в CLAUDE.md, и до сих пор они запускались по памяти —
то есть иногда. Хук делает это без участия человека: правка попала в файл,
относящийся к проверке, — проверка прошла.

На вход подаётся JSON хука из stdin. Скрипт ничего не блокирует: он выводит
результат в поле systemMessage, чтобы расхождение стало видно сразу, а не на
коммите.

    echo '{"tool_input":{"file_path":"products-config.php"}}' | \
        python3 tools/hook_checks.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Какая правка какую проверку запускает. Порядок важен: первая подошедшая
# запись выигрывает, поэтому частные шаблоны стоят выше общих.
ROUTES: list[tuple[tuple[str, ...], str]] = [
    (("products-config.php", "content/strategy/products.csv",
      "products-storage/SERVER-MANIFEST.txt"), "check_products.py"),
    (("lead.php", "materialy/", "downloads/", "build_free_zips.py",
      "insert_lead_blocks.py"), "check_free_materials.py"),
    # Страницы товаров сверяются здесь же: число файлов в шапке страницы
    # стоит против папки выдачи, и правка страницы должна красить так же,
    # как правка папки.
    (("products-storage/", "products/"), "check_packages.py"),
    (("content/reels/",), "check_reel.py"),
    (("articles/", "assets/", "content/covers/"), "check_covers.py"),
    (("articles/", "tools/build_rss.py"), "check_rss.py"),
    # Открытый кусок документа сверяется и при правке страницы, и при
    # пересборке самого документа: расходятся они именно во втором случае
    (("demo/", "products-storage/"), "check_demo.py"),
    # Один документ в двух папках выдачи обязан быть одной редакцией.
    # Разделение комплекта 11.08.2026 собрало новую папку копированием с
    # витрины и увезло в продажу редакцию, снятую нормативной сверкой
    (("products-storage/",), "check_editions.py"),
    # Витрина главной против каталога кассы: разметка ItemList уже разошлась
    # с витриной однажды на семь позиций, и молча
    (("index.html",), "sync_catalog.py"),
    # Замеренный спрос против опубликованного. Расхождение накапливается
    # молча: новая страница не попадает в карту сайта, а целевой URL из
    # семантики так и остаётся планом
    (("sitemap.xml", "content/strategy/semantic-core.csv",
      "articles/", "products/"), "check_seo.py"),
    # Вёрстка на телефоне. Проверка тяжелее прочих — поднимает браузер, — и
    # ходит по выборке из шести страниц, по одной на шаблон. Без playwright
    # говорит «не запускалась», а не «прошла».
    ((".css", "attribution.js", "article_ui.py"), "check_mobile.py"),
    # Цели перехода на ссылках витрины. Правка обработчика и правка разметки
    # ломают счёт одинаково: 223 из 375 ссылок под целью записаны
    # относительно, и подстрочная сверка их не видела
    (("attribution.js", ".html"), "test_attribution_goals.js"),
    # Любая правка страницы или карты сайта. Стоит последней и без привязки
    # к каталогу намеренно: ровно привязка к каталогу и была дефектом —
    # проверка смотрела articles/ и не видела кнопку покупки в 404 на
    # materialy/. Тот же прогон стоит гейтом в deploy.yml: хук можно не
    # запустить, гейт — нет.
    ((".html", "sitemap.xml"), "check_links.py"),
]

TIMEOUT = 60


def checks_for(path: str) -> list[str]:
    return [script for patterns, script in ROUTES if any(p in path for p in patterns)]


def run(script: str) -> tuple[int, str]:
    # Проверка целей перехода написана на JavaScript, потому что проверяет
    # JavaScript: обработчик прогоняется настоящий, а не пересказанный на
    # питоне. Пересказ разошёлся бы с оригиналом молча — ровно тот дефект,
    # который она и ловит.
    if script.endswith(".js"):
        command = ["node", str(ROOT / "tools" / script)]
    else:
        command = [sys.executable, str(ROOT / "tools" / script)]
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=TIMEOUT, cwd=ROOT,
        )
    except FileNotFoundError:
        # Без node проверка не запускалась — это не «прошла»
        return 1, f"{script}: не запускалась, нет node"
    except subprocess.TimeoutExpired:
        return 1, f"{script}: не уложился в {TIMEOUT} с"
    except OSError as exc:
        return 1, f"{script}: не запустился ({exc})"
    return done.returncode, (done.stdout or done.stderr).strip()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response") or {}
    path = str(response.get("filePath") or tool_input.get("file_path") or "")
    if not path:
        return 0

    failures = []
    for script in checks_for(path):
        code, output = run(script)
        if code != 0:
            failures.append(f"{script}:\n{output}")

    if failures:
        print(json.dumps({
            "systemMessage": "Проверки не прошли:\n\n" + "\n\n".join(failures),
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n\n".join(failures),
            },
        }, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
