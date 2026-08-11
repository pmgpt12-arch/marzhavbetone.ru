#!/usr/bin/env python3
"""Приводит картинки сайта к весу, пригодному для телефона.

Замер 11.08.2026: `du -sh assets/` — 53 МБ; в HTML используются 36 файлов на
27 МБ, из них 15 тяжелее 300 КБ на 22,6 МБ. При этом часть обложек уже
приведена в порядок и весит 0,29–0,37 МБ при 1600×893 — то есть цель не
выдумана, она уже достигнута на части файлов и просто не доведена до конца.

Что делает:
  · уменьшает до MAX_WIDTH по ширине (обложка показывается в колонке 920px,
    полтора экрана запаса на плотные экраны хватает);
  · пережимает в JPEG качества QUALITY, прогрессивный;
  · PNG без прозрачности переводит в JPEG и переписывает ссылки — держать
    фотографию в PNG значит платить втрое ни за что;
  · PNG с прозрачностью не трогает: перевод в JPEG залил бы фон.

Мастера не сохраняются отдельно: файл в `assets/` и есть версия для сайта.
Прежние версии остаются в истории git, восстанавливаются оттуда.

    python3 tools/optimize_images.py            # показать, что будет сделано
    python3 tools/optimize_images.py --write    # сделать
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
MAX_WIDTH = 1600
QUALITY = 82
THRESHOLD = 300_000  # ниже этого веса трогать нечего

# Где могут встретиться имена файлов. Двоичное и служебное не читаем.
REFERENCE_GLOBS = ("**/*.html", "**/*.css", "**/*.xml", "**/*.md",
                   "**/*.yaml", "**/*.yml", "tools/*.py")
SKIP_DIRS = (".git/", "downloads/", "products-storage/", "orders/")


def reference_files() -> list[Path]:
    out = []
    for pattern in REFERENCE_GLOBS:
        for path in ROOT.glob(pattern):
            rel = path.relative_to(ROOT).as_posix()
            if any(rel.startswith(d) for d in SKIP_DIRS):
                continue
            if path.is_file():
                out.append(path)
    return sorted(set(out))


def used_assets(files: list[Path]) -> set[str]:
    used: set[str] = set()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        used |= set(re.findall(r"assets/([A-Za-z0-9._-]+\.(?:png|jpg|jpeg))", text))
    return used


def rename_references(files: list[Path], old: str, new: str, write: bool) -> int:
    touched = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old not in text:
            continue
        touched += 1
        if write:
            path.write_text(text.replace(old, new), encoding="utf-8")
    return touched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="записать изменения")
    parser.add_argument("--max-width", type=int, default=MAX_WIDTH)
    parser.add_argument("--quality", type=int, default=QUALITY)
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("Pillow не установлен — обработка НЕ ЗАПУСКАЛАСЬ.")
        print("  pip install pillow")
        return 2

    files = reference_files()
    used = used_assets(files)
    before = after = 0
    changed: list[tuple[str, int, int, str]] = []
    kept_alpha: list[str] = []
    skipped_small: list[str] = []

    for name in sorted(used):
        source = ASSETS / name
        if not source.exists():
            print(f"  ссылка есть, файла нет: {name}")
            continue
        size = source.stat().st_size
        if size < THRESHOLD:
            continue

        image = Image.open(source)
        has_alpha = image.mode in ("RGBA", "LA") and image.getchannel("A").getextrema()[0] < 255
        if has_alpha and source.suffix.lower() == ".png":
            kept_alpha.append(name)
            continue

        if image.width > args.max_width:
            height = round(image.height * args.max_width / image.width)
            image = image.resize((args.max_width, height), Image.LANCZOS)
        image = image.convert("RGB")

        target = source.with_suffix(".jpg")
        note = ""
        if target != source:
            if target.exists():
                print(f"  {name}: .jpg с таким именем уже есть, пропущено")
                continue
            note = f"→ {target.name}"

        # Повторное пережатие без выигрыша — это вторая потеря качества за
        # ничего. Четыре обложки уже приведены в порядок, и трогать их нельзя.
        if target == source:
            import io

            probe = io.BytesIO()
            image.save(probe, "JPEG", quality=args.quality, optimize=True, progressive=True)
            if probe.tell() > size * 0.9:
                skipped_small.append(name)
                continue

        before += size
        if args.write:
            image.save(target, "JPEG", quality=args.quality, optimize=True, progressive=True)
            new_size = target.stat().st_size
            if target != source:
                rename_references(files, f"assets/{name}", f"assets/{target.name}", True)
                source.unlink()
        else:
            import io

            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=args.quality, optimize=True, progressive=True)
            new_size = buffer.tell()
            if target != source:
                note += f" (ссылок в {rename_references(files, f'assets/{name}', '', False)} файлах)"
        after += new_size
        changed.append((name, size, new_size, note))

    for name, old, new, note in changed:
        print(f"  {old / 1024 / 1024:5.2f} → {new / 1024:6.0f} КБ  {name} {note}")
    if kept_alpha:
        print(f"  с прозрачностью, не тронуты: {', '.join(kept_alpha)}")
    if skipped_small:
        print(f"  уже сжаты, повторно не трогаем: {', '.join(skipped_small)}")

    print()
    print(f"Файлов обработано: {len(changed)}")
    if changed:
        print(f"Было {before / 1024 / 1024:.1f} МБ, стало {after / 1024 / 1024:.1f} МБ "
              f"(в {before / max(after, 1):.1f} раза легче)")
    if not args.write:
        print("Это показ. Записать: --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
