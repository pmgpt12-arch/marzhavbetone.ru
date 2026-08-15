#!/usr/bin/env python3
"""Сверяет четыре места, где описан один и тот же бесплатный материал.

Материал живёт в четырёх файлах сразу, и они связаны только словом в
комментарии «расходиться они не должны»:

    products-storage/00-free-*/     файлы, которые получит читатель
    lead.php                        ключ формы → архив и заголовок
    tools/build_free_zips.py        ключ → папка, из которой собран архив
    materialy/<ключ>.html           страница: форма и перечень «что внутри»
    tools/insert_lead_blocks.py     врезка в статьи: заголовок и перечень
    katalog.html                    карточка на витрине
    sitemap.xml                     адрес для поисковых систем

Расхождение здесь тихое и дорогое одновременно. Три страницы полгода
перечисляли файлы чужого материала — ссылки при этом были живыми, формы
работали, архивы отдавались, и ни одна проверка ничего не заметила:
неверным было только содержание перечня.

    python3 tools/check_free_materials.py

Код возврата 1 при любом расхождении.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"

# Не папка, а один PDF, и лежит он в downloads/ сам по себе: форма на
# главной работает с ним давно и остаётся ключом по умолчанию в lead.php.
STANDALONE = {"checklist"}
# Служебные файлы читателю не отдаются — тот же список, что в build_free_zips
SKIP = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess", "MANIFEST.md"}


def keys_from_lead() -> dict[str, str]:
    """Ключ материала → путь архива, как их видит форма."""
    text = (ROOT / "lead.php").read_text(encoding="utf-8")
    block = re.search(r"const MVB_MATERIALS = \[(.*?)^\];", text, re.M | re.S)
    if not block:
        raise SystemExit("lead.php: не найден MVB_MATERIALS")
    return dict(re.findall(r"'([\w-]+)' => \[\s*'file'\s*=>\s*'([^']+)'",
                           block.group(1)))


def keys_from_builder() -> dict[str, str]:
    """Ключ материала → папка, из которой собирается архив."""
    text = (ROOT / "tools" / "build_free_zips.py").read_text(encoding="utf-8")
    block = re.search(r"^MATERIALS = \{(.*?)^\}", text, re.M | re.S)
    if not block:
        raise SystemExit("build_free_zips.py: не найден MATERIALS")
    return dict(re.findall(r'"([\w-]+)":\s*"([^"]+)"', block.group(1)))


def keys_from_blocks() -> dict[str, list[str]]:
    """Ключ материала → перечень файлов, который видит читатель статьи."""
    text = (ROOT / "tools" / "insert_lead_blocks.py").read_text(encoding="utf-8")
    block = re.search(r"^FREE = \{(.*?)^\}", text, re.M | re.S)
    if not block:
        raise SystemExit("insert_lead_blocks.py: не найден FREE")
    return {key: re.findall(r"'([^']+)'", files) for key, files in
            re.findall(r"'([\w-]+)': \{.*?'files': \[(.*?)\],", block.group(1), re.S)}


def titles_from_pages() -> dict[str, str]:
    """Ключ материала → его заголовок на собственной странице."""
    out: dict[str, str] = {}
    for page in sorted((ROOT / "materialy").glob("*.html")):
        html = page.read_text(encoding="utf-8")
        found = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if found:
            out[page.stem] = re.sub(
                r"\s+", " ", re.sub(r"<[^>]+>", "", found.group(1))).strip()
    return out


def check_article_offers(titles: dict[str, str]) -> list[str]:
    """Врезка в статье зовёт туда же, куда и называет.

    Проверка появилась после разбора 10.08.2026. Пятнадцать статей несли
    рукописную врезку на `/index.html#checklist`, которая обещала «7 причин,
    почему не платят по КС-2» и шаблон письма; по ссылке отдавался чек-лист
    закрытия работ, где ни того, ни другого нет. Все проверки при этом
    молчали: ключи, папки и архивы сходились, а на текст обещания не
    смотрел никто. Вдобавок в тех же статьях уже стоял генерируемый блок —
    предложение показывалось дважды, в шести случаях на разные материалы.

    Отсюда три условия: одно предложение на статью, ссылка на существующий
    материал, заголовок врезки — тот же, что у страницы материала.
    """
    problems: list[str] = []
    offer = re.compile(
        r'<div class="article-(?:lead|cta)"(?:(?!</div>).)*?'
        r'>\s*БЕСПЛАТНО[^<]*<(?:(?!</div>).)*?</div>', re.S)

    for path in sorted((ROOT / "articles").glob("*.html")):
        if path.name == "index.html":       # витрина списка, не статья
            continue
        html = path.read_text(encoding="utf-8")
        blocks = offer.findall(html)
        if not blocks:
            problems.append(f"{path.name}: нет врезки бесплатного материала")
            continue
        if len(blocks) > 1:
            problems.append(f"{path.name}: врезок бесплатного материала "
                            f"{len(blocks)} — читателю предложено дважды")
        for block in blocks:
            href = re.search(r'href="/materialy/([\w-]+)\.html"', block)
            if not href:
                bad = re.search(r'href="([^"]+)"', block)
                problems.append(
                    f"{path.name}: врезка ведёт не на страницу материала — "
                    f"{bad.group(1) if bad else 'ссылки нет'}")
                continue
            key = href.group(1)
            if key not in titles:
                problems.append(f"{path.name}: врезка ведёт на неизвестный "
                                f"материал «{key}»")
                continue
            head = re.search(r"<h3>(.*?)</h3>", block, re.S)
            said = re.sub(r"\s+", " ",
                          re.sub(r"<[^>]+>", "", head.group(1))).strip() if head else ""
            if said != titles[key]:
                problems.append(
                    f"{path.name}: врезка называет материал иначе, чем его "
                    f"страница\n        врезка:  «{said}»\n"
                    f"        {key}.html: «{titles[key]}»")
    return problems


def main() -> int:
    lead = keys_from_lead()
    builder = keys_from_builder()
    blocks = keys_from_blocks()
    # Витрина переехала на katalog.html 15.08.2026
    # (tools/split_catalog_2026-08-15.py): на главной каталог давал
    # 33 экрана длины и распирал страницу вбок.
    home = (ROOT / "katalog.html").read_text(encoding="utf-8")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    problems: list[str] = []

    # 1. Один и тот же набор ключей в форме, сборщике архивов и врезке
    expected = set(lead) - STANDALONE
    for name, actual in (("build_free_zips.py", set(builder)),
                         ("insert_lead_blocks.py", set(blocks))):
        for key in sorted(expected - actual):
            problems.append(f"{key}: есть в lead.php, нет в {name}")
        for key in sorted(actual - expected):
            problems.append(f"{key}: есть в {name}, нет в lead.php")

    for key in sorted(expected):
        folder = STORAGE / builder.get(key, "")
        if key not in builder:
            continue                    # уже названо выше
        if not folder.is_dir():
            problems.append(f"{key}: нет папки {folder.name}")
            continue

        files = sorted(p.name for p in folder.iterdir()
                       if p.is_file() and p.name not in SKIP)

        # 2. Архив собран и содержит ровно то, что лежит в папке
        archive = ROOT / lead[key].lstrip("/")
        if not archive.is_file():
            problems.append(f"{key}: нет архива {archive.name} — "
                            f"запустите tools/build_free_zips.py")
        else:
            inside = sorted(zipfile.ZipFile(archive).namelist())
            if inside != files:
                problems.append(
                    f"{key}: архив расходится с папкой — в архиве "
                    f"{len(inside)}, в папке {len(files)}; "
                    f"лишнее {sorted(set(inside) - set(files))}, "
                    f"недостаёт {sorted(set(files) - set(inside))}")

        # 3. Страница материала существует, её форма шлёт этот же ключ,
        #    и перечень «что внутри» совпадает по числу с составом папки
        page = ROOT / "materialy" / f"{key}.html"
        if not page.is_file():
            problems.append(f"{key}: нет страницы materialy/{key}.html")
        else:
            html = page.read_text(encoding="utf-8")
            sent = re.search(r'name="material"[^>]*value="([^"]+)"', html)
            if not sent:
                problems.append(f"{key}: на странице нет поля material")
            elif sent.group(1) != key:
                problems.append(f"{key}: форма страницы шлёт "
                                f"«{sent.group(1)}» — страница скопирована "
                                f"и не дописана")
            listed = re.findall(r'<article class="doc-item"><h3>(.*?)</h3>', html)
            if len(listed) != len(files):
                problems.append(f"{key}: страница обещает {len(listed)} "
                                f"файлов, в папке {len(files)}")
            # Перечень на странице и перечень во врезке — один и тот же
            # список, написанный в двух местах. Сравнение дословное: именно
            # оно ловит скопированную и не дописанную страницу, где число
            # файлов совпало, а названы файлы чужого материала. Числом такое
            # не поймать — их всюду по четыре.
            if key in blocks and listed != blocks[key]:
                problems.append(
                    f"{key}: перечень на странице не совпадает с врезкой в "
                    f"статьях\n        страница: {listed}\n"
                    f"        врезка:   {blocks[key]}")

        # 4. Врезка в статьи обещает столько же файлов, сколько отдаётся
        if key in blocks and len(blocks[key]) != len(files):
            problems.append(f"{key}: врезка в статьях обещает "
                            f"{len(blocks[key])} файлов, в папке {len(files)}")

        # 5. Материал виден не только из статьи: карточка на витрине и
        #    адрес в карте сайта. Ровно это и забылось при седьмом
        #    материале — страница была готова, а с главной на неё не вело
        #    ничего, и поисковые системы о ней не знали.
        if f"materialy/{key}.html" not in home:
            problems.append(f"{key}: нет карточки на главной")
        if f"/materialy/{key}.html</loc>" not in sitemap:
            problems.append(f"{key}: нет в sitemap.xml — "
                            f"запустите tools/build_sitemap.py")

    # 6. Врезка в статье зовёт туда же, куда и называет, и она одна
    problems += check_article_offers(titles_from_pages())

    for line in problems:
        print(f"РАСХОЖДЕНИЕ  {line}")
    print(f"\nБесплатных материалов: {len(expected)}, "
          f"расхождений: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
