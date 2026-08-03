#!/usr/bin/env python3
"""Собирает архивы бесплатных материалов в downloads/.

Платные комплекты собирает PHP при первой покупке; бесплатные отдаются
статикой сразу после формы, поэтому архив должен лежать готовым.

    python3 tools/build_free_zips.py

Соответствие «идентификатор материала → папка → архив» задано в lead.php:
здесь и там один и тот же список, и расходиться они не должны.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"
DOWNLOADS = ROOT / "downloads"

# Служебные файлы покупателю не отдаём — как в mvb_build_product_zip
SKIP = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess"}

MATERIALS = {
    "dengi": "00-free-ks-podpisany-deneg-net",
    "dop-raboty": "00-free-dopy-ne-v-podarok",
    "vozvrat-ks": "00-free-ks-bez-vozvrata",
    "uderzhaniya": "00-free-uderzhaniya-do-podpisi",
    "dogovor": "00-free-dogovor-do-podpisi",
}


def build(slug: str, folder: str) -> Path | None:
    source = STORAGE / folder
    if not source.is_dir():
        print(f"нет папки {source}", file=sys.stderr)
        return None

    target = DOWNLOADS / f"{slug}.zip"
    files = sorted(p for p in source.iterdir() if p.is_file() and p.name not in SKIP)

    # Пересобираем всегда: архив дешёвый, а расхождение с папкой дорогое
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)

    size = target.stat().st_size / 1024
    print(f"{target.name}: {len(files)} файлов, {size:.0f} КБ")
    return target


def main() -> int:
    DOWNLOADS.mkdir(exist_ok=True)
    built = [build(slug, folder) for slug, folder in MATERIALS.items()]
    if not all(built):
        return 1
    print(f"\nСобрано архивов: {len(built)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
