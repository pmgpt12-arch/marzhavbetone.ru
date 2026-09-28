#!/usr/bin/env python3
"""Собирает архивы бесплатных материалов в downloads/.

Платные комплекты собирает PHP при первой покупке; бесплатные отдаются
статикой сразу после формы, поэтому архив должен лежать готовым.

    python3 tools/build_free_zips.py            # все архивы
    python3 tools/build_free_zips.py dengi      # только названные

Архив воспроизводим: у всех элементов одна фиксированная дата и одни права,
порядок — по имени. Одинаковые файлы в папке дают побайтово одинаковый ZIP,
сколько раз и когда его ни пересобирай.

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

# Служебные файлы покупателю не отдаём — тот же список, что в
# mvb_build_product_zip. MANIFEST.md сюда добавлен 03.08.2026: он внутренний
# документ с логикой воронки и границей платного, а страницы обещают четыре
# файла — архив с пятым обещанию не соответствовал.
SKIP = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess", "MANIFEST.md"}

# Дата элементов архива. Время изменения файла на диске зависит от того, когда
# сделан checkout, — в архив оно не попадает.
ZIP_DATE = (2026, 9, 28, 0, 0, 0)

MATERIALS = {
    "dengi": "00-free-ks-podpisany-deneg-net",
    "dop-raboty": "00-free-dopy-ne-v-podarok",
    "vozvrat-ks": "00-free-ks-bez-vozvrata",
    "uderzhaniya": "00-free-uderzhaniya-do-podpisi",
    "dogovor": "00-free-dogovor-do-podpisi",
    "bankrotstvo": "00-free-bankrotstvo-proverka",
    "avans": "00-free-avans-do-podpisi",
    "raschet-metrami": "00-free-raschet-metrami",
    "ispolnitelnaya-dokumentaciya": "00-free-id-do-peredachi",
    "akt-skrytyh-rabot": "00-free-akt-skrytyh-rabot",
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
            info = zipfile.ZipInfo(file.name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, file.read_bytes())

    size = target.stat().st_size / 1024
    print(f"{target.name}: {len(files)} файлов, {size:.0f} КБ")
    return target


def main(argv: list[str]) -> int:
    unknown = [slug for slug in argv if slug not in MATERIALS]
    if unknown:
        print(f"нет такого материала: {', '.join(unknown)}", file=sys.stderr)
        return 2
    DOWNLOADS.mkdir(exist_ok=True)
    selected = {slug: MATERIALS[slug] for slug in argv} if argv else MATERIALS
    built = [build(slug, folder) for slug, folder in selected.items()]
    if not all(built):
        return 1
    print(f"\nСобрано архивов: {len(built)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
