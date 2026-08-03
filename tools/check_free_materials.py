#!/usr/bin/env python3
"""Сверяет четыре места, где описан один и тот же бесплатный материал.

Материал живёт в четырёх файлах сразу, и они связаны только словом в
комментарии «расходиться они не должны»:

    products-storage/00-free-*/     файлы, которые получит читатель
    lead.php                        ключ формы → архив и заголовок
    tools/build_free_zips.py        ключ → папка, из которой собран архив
    materialy/<ключ>.html           страница: форма и перечень «что внутри»
    tools/insert_lead_blocks.py     врезка в статьи: заголовок и перечень

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


def main() -> int:
    lead = keys_from_lead()
    builder = keys_from_builder()
    blocks = keys_from_blocks()
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

    for line in problems:
        print(f"РАСХОЖДЕНИЕ  {line}")
    print(f"\nБесплатных материалов: {len(expected)}, "
          f"расхождений: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
