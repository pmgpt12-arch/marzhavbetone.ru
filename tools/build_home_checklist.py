#!/usr/bin/env python3
"""Бесплатный PDF главной — только чек-лист, без листа снятой линейки.

Форма на главной (`index.html#checklist`, кнопка «Получить PDF») отдаёт
`downloads/checklist-zakrytiya-rabot.pdf`. Страница 1 этого файла — сам
чек-лист: 20 контрольных пунктов в четырёх группах. Страница 2 — реклама
линейки, которой больше нет: «Закрытие работ — 10 документов», «Допработы
без потерь — 10 документов», «Договор подряда — 10 документов», «Полный
комплект ПТО — 40 документов» (снят с продажи 11.08.2026) и ссылка
`/#catalog`, которая с 15.08.2026 ведёт не в каталог. Аудит MB001, G-01.

Исходника у файла нет ни в одном репозитории (MB001_Free_Materials_
Technical_Fix_2026-09, Б-1), поэтому текст не пересобирается и не
правится: инструмент берёт страницу 1 байт в байт средствами poppler и
кладёт её отдельным файлом. Исходный PDF не трогается — из него же
собирается шаблон бота `templates/zakrytie.pdf` в ai-business-os, и эта
выдача живёт по своему решению.

Требует `pdfseparate` (пакет poppler-utils).

    python3 tools/build_home_checklist.py           # показать
    python3 tools/build_home_checklist.py --write   # собрать
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "downloads" / "checklist-zakrytiya-rabot.pdf"
TARGET = ROOT / "downloads" / "checklist-zakrytiya-rabot-20-punktov.pdf"
PAGE = 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    print(f"источник: {SOURCE.relative_to(ROOT)}, страница {PAGE}")
    print(f"выдача:   {TARGET.relative_to(ROOT)}")
    if not args.write:
        print("\nпоказ, файл не изменён. Собрать — с --write")
        return 0
    if not shutil.which("pdfseparate"):
        print("нет pdfseparate: apt-get install poppler-utils", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "page.pdf"
        subprocess.run(["pdfseparate", "-f", str(PAGE), "-l", str(PAGE),
                        str(SOURCE), str(out)], check=True)
        shutil.copyfile(out, TARGET)
    print(f"\nзаписано: {TARGET.relative_to(ROOT)} ({TARGET.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
