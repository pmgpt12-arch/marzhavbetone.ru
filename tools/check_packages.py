#!/usr/bin/env python3
"""Сверяет состав комплектов с тем, что лежит в папках.

MANIFEST.md — это то, что покупатель видит внутри архива. Если там написано
«PDF», а внутри Word, человек считает, что ему прислали не то. Расхождение
возникает молча: манифесты собраны генератором один раз, файлы менялись
отдельно.

Вторая сверка — вложенные пакеты. «Полный комплект» обещает базовые
комплекты целиком, но держит это обещание копией файлов, а не ссылкой.
Копия не отстаёт от оригинала ровно до первой правки любого из шести:
манифест при этом сходится с папкой, потому что папка и правда такая,
какой её описали, — расходятся между собой два места на диске. Поэтому
копия сверяется с оригиналом по содержимому, а не по перечню имён.

    python3 tools/check_packages.py

Код возврата 1, если хотя бы один комплект расходится с манифестом или
вложенная копия расходится с отдельным комплектом.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"

# Файлы, которые не попадают в архив покупателю (см. mvb_build_product_zip)
NOT_DELIVERED = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess"}
# Манифест описывает состав, себя он не описывает
NOT_LISTED = {"MANIFEST.md"}

LISTED = re.compile(r"^\s*[-*]\s*`([^`]+)`", re.M)
# Вложенная копия и комплект-источник: `путь/копии/` ← `имя-комплекта`.
# Стрелка нужна там, где имена разошлись: папка ПТО внутри полного комплекта
# называется 06-id-blokiruet-oplatu, а лежит в ней 08-pto-bez-zamechaniy.
# Переименовать её нельзя — это имя уже в выданных покупателям архивах.
SOURCE = re.compile(r"^\s*[-*]\s*`([^`]+/)`\s*←\s*`([^`]+)`", re.M)


def declared(manifest: Path) -> list[str]:
    """Состав комплекта. Другие разделы манифеста могут ссылаться на файлы,
    которых в папке нет намеренно — например перечислять смежные бесплатные
    материалы, — и составом они не являются."""
    text = manifest.read_text(encoding="utf-8")
    section = re.search(r"^## Состав\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return LISTED.findall(section.group(1) if section else "")


def sources(manifest: Path) -> dict[str, str]:
    """Откуда скопирован каждый вложенный пакет.

    Умолчание — комплект того же имени: `.../03-dogovor-podryada/` берётся
    из `03-dogovor-podryada`. Стрелкой объявляются исключения, и объявлены
    они в манифесте, а не в этом файле: состав комплекта решает манифест,
    проверка его только читает.
    """
    text = manifest.read_text(encoding="utf-8")
    section = re.search(r"^## Состав\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return dict(SOURCE.findall(section.group(1) if section else ""))


def delivered(root: Path) -> dict[str, str]:
    """Что покупатель получит из этой папки: путь внутри неё → хэш файла.

    Служебные файлы исключаются на любой глубине — так же, как в
    `mvb_build_product_zip`, где отбор идёт по `basename`. Поэтому
    MANIFEST.md внутри вложенной копии на сверку не влияет: покупатель его
    не видит, и требовать его наличия значило бы сравнивать то, чего
    в архиве нет.
    """
    skip = NOT_DELIVERED | NOT_LISTED
    return {
        item.relative_to(root).as_posix():
            hashlib.sha256(item.read_bytes()).hexdigest()
        for item in root.rglob("*")
        if item.is_file() and item.name not in skip
    }


def check_copies(package: Path, manifest: Path) -> int:
    """Сверяет вложенные копии базовых пакетов с отдельными комплектами.

    Возвращает число разошедшихся копий. Сравнивается содержимое: файл,
    переписанный в отдельном комплекте и не перенесённый в копию, по именам
    неотличим от целого, а покупатель полного получает старую редакцию.
    """
    broken = 0
    explicit = sources(manifest)
    nested = [name for name in declared(manifest) if name.endswith("/")]
    for name in nested:
        copy = package / name.rstrip("/")
        origin = STORAGE / explicit.get(name, Path(name.rstrip("/")).name)
        if not copy.is_dir():
            continue          # отсутствие папки ловит основная проверка
        if not origin.is_dir():
            print(f"НЕТ ИСТОЧНИКА  {package.name}: {name} ← {origin.name}")
            broken += 1
            continue

        here, there = delivered(copy), delivered(origin)
        missing = sorted(set(there) - set(here))
        extra = sorted(set(here) - set(there))
        changed = sorted(key for key in set(here) & set(there)
                         if here[key] != there[key])
        if not (missing or extra or changed):
            continue

        broken += 1
        print(f"КОПИЯ ОТСТАЛА  {package.name}: {name} ← {origin.name}")
        for item in missing:
            print(f"    {item} — есть в комплекте, нет в копии")
        for item in extra:
            print(f"    {item} — есть в копии, нет в комплекте")
        for item in changed:
            print(f"    {item} — содержимое разное")
    return broken


def main() -> int:
    packages = sorted(p for p in STORAGE.iterdir() if p.is_dir())
    if not packages:
        print("Комплектов не найдено", file=sys.stderr)
        return 1

    broken = 0
    stale = 0
    for package in packages:
        manifest = package / "MANIFEST.md"
        if not manifest.is_file():
            print(f"НЕТ МАНИФЕСТА  {package.name}")
            broken += 1
            continue

        # До проверки состава: комплект может сойтись с манифестом и при этом
        # отставать от оригиналов — это два разных расхождения.
        stale += check_copies(package, manifest)

        actual = {
            item.name for item in package.iterdir()
            if item.is_file() and item.name not in NOT_DELIVERED | NOT_LISTED
        }
        listed = declared(manifest)

        # Запись со слэшем — вложенный пакет, а не файл: так «Полный комплект»
        # ссылается на базовые. Проверяем существование папки по этому пути
        missing = [
            name for name in listed
            if name.endswith("/")
            and not (package / name.rstrip("/")).is_dir()
        ]
        listed = [name for name in listed if not name.endswith("/")]
        actual -= {name for name in actual if (package / name).is_dir()}

        missing += [name for name in listed if name not in actual]
        extra = sorted(actual - set(listed))

        if not missing and not extra:
            continue

        broken += 1
        print(f"РАСХОЖДЕНИЕ  {package.name}")
        for name in missing:
            # Самый частый случай: в манифесте .pdf, на диске .docx
            stem = Path(name).stem
            near = [item for item in extra if Path(item).stem == stem]
            if near:
                print(f"    {name} → на диске {near[0]}")
            else:
                print(f"    {name} — обещан, но файла нет")
        for name in extra:
            if any(Path(name).stem == Path(item).stem for item in missing):
                continue
            print(f"    {name} — есть на диске, но не описан")

    print(f"\nКомплектов: {len(packages)}, с расхождениями: {broken}, "
          f"отставших копий: {stale}")
    return 1 if broken or stale else 0


if __name__ == "__main__":
    sys.exit(main())
