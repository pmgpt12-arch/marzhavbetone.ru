#!/usr/bin/env python3
"""Сверяет состав комплектов с тем, что лежит в папках.

MANIFEST.md — это то, что покупатель видит внутри архива. Если там написано
«PDF», а внутри Word, человек считает, что ему прислали не то. Расхождение
возникает молча: манифесты собраны генератором один раз, файлы менялись
отдельно.

    python3 tools/check_packages.py

Код возврата 1, если хотя бы один комплект расходится с манифестом.
"""
from __future__ import annotations

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


def declared(manifest: Path) -> list[str]:
    """Состав комплекта. Другие разделы манифеста могут ссылаться на файлы,
    которых в папке нет намеренно — например перечислять смежные бесплатные
    материалы, — и составом они не являются."""
    text = manifest.read_text(encoding="utf-8")
    section = re.search(r"^## Состав\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return LISTED.findall(section.group(1) if section else "")


def main() -> int:
    packages = sorted(p for p in STORAGE.iterdir() if p.is_dir())
    if not packages:
        print("Комплектов не найдено", file=sys.stderr)
        return 1

    broken = 0
    for package in packages:
        manifest = package / "MANIFEST.md"
        if not manifest.is_file():
            print(f"НЕТ МАНИФЕСТА  {package.name}")
            broken += 1
            continue

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

    print(f"\nКомплектов: {len(packages)}, с расхождениями: {broken}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
