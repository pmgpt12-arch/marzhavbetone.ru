#!/usr/bin/env python3
"""Приводит списки файлов в MANIFEST.md к тому, что лежит в папках.

Правит только строки состава: расширение и подпись формата у записей, где
файл на диске тот же, но в другом формате, и дописывает файлы, которых в
манифесте нет. Описания, ограничения и всё остальное не трогает — их писал
человек.

    python3 tools/fix_manifests.py --dry-run   # показать, что изменится
    python3 tools/fix_manifests.py             # записать
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "products-storage"

NOT_DELIVERED = {"00-PISMO-POSLE-POKUPKI.txt", ".htaccess"}
NOT_LISTED = {"MANIFEST.md"}

FORMAT = {".docx": "Word", ".xlsx": "Excel", ".pdf": "PDF", ".txt": "Текст"}
ENTRY = re.compile(r"^(\s*[-*]\s*)`([^`]+)`(\s*—\s*)([^:\n]*)(.*)$", re.M)


def fix(package: Path, write: bool) -> list[str]:
    manifest = package / "MANIFEST.md"
    if not manifest.is_file():
        return []

    text = manifest.read_text(encoding="utf-8")
    actual = {
        item.name for item in package.iterdir()
        if item.is_file() and item.name not in NOT_DELIVERED | NOT_LISTED
    }
    by_stem = {Path(name).stem: name for name in actual}
    changes: list[str] = []
    listed: set[str] = set()

    def replace(match: re.Match) -> str:
        prefix, name, dash, label, tail = match.groups()
        if name.endswith("/"):
            listed.add(name)
            return match.group(0)

        listed.add(name)
        if name in actual:
            return match.group(0)

        real = by_stem.get(Path(name).stem)
        if real is None:
            return match.group(0)

        listed.discard(name)
        listed.add(real)
        new_label = FORMAT.get(Path(real).suffix, label.strip())
        changes.append(f"{name} → {real} ({label.strip()} → {new_label})")
        return f"{prefix}`{real}`{dash}{new_label}{tail}"

    updated = ENTRY.sub(replace, text)

    # Файлы, которых в манифесте нет вовсе. Инструкция — первое, что
    # открывает покупатель, и её отсутствие в списке выглядит как ошибка
    missing = sorted(actual - listed)
    if missing:
        lines = "\n".join(
            f"- `{name}` — {FORMAT.get(Path(name).suffix, 'файл')}" for name in missing
        )
        anchor = re.search(r"^## Состав\s*\n(?:###[^\n]*\n)?", updated, re.M)
        if anchor:
            insert_at = anchor.end()
            updated = updated[:insert_at] + lines + "\n" + updated[insert_at:]
            changes.extend(f"дописан {name}" for name in missing)

    if changes and write:
        manifest.write_text(updated, encoding="utf-8")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Синхронизация манифестов с папками")
    parser.add_argument("--dry-run", action="store_true", help="только показать")
    args = parser.parse_args()

    total = 0
    for package in sorted(p for p in STORAGE.iterdir() if p.is_dir()):
        changes = fix(package, write=not args.dry_run)
        if changes:
            total += len(changes)
            print(f"{package.name}")
            for change in changes:
                print(f"    {change}")

    verb = "изменилось бы" if args.dry_run else "исправлено"
    print(f"\nЗаписей {verb}: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
