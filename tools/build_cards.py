#!/usr/bin/env python3
"""Собирает карточки карусели для Instagram из файла content/social/<slug>.md.

Текст карточек уже написан в разделе «Instagram: карусель». Скрипт только
раскладывает его по картинкам 1080x1350 в фирменном стиле — том же, что у
обложек статей, чтобы карусель и сайт выглядели одним проектом.

Использование:
    python3 tools/build_cards.py vsyo-vklyucheno-v-cenu
    python3 tools/build_cards.py vsyo-vklyucheno-v-cenu --out /tmp/cards

Размер 1080x1350 — вертикальный формат ленты (4:5). Он занимает больше
экрана, чем квадрат, и на телефоне текст читается без увеличения.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SOCIAL_DIR = ROOT / "content" / "social"
DEFAULT_OUT = SOCIAL_DIR / "cards"

WIDTH, HEIGHT = 1080, 1350
# Цвета из styles.css сайта — карусель не должна расходиться с брендом
INK = (36, 38, 41)
INK_DARK = (22, 23, 25)
ACCENT = (255, 90, 0)
PAPER = (248, 246, 240)
CONCRETE = (169, 164, 154)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
SANS_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
SANS = FONT_DIR / "DejaVuSans.ttf"

MARGIN = 90
# Крупный кегль для обложки и финала, спокойный — для середины карусели
COVER_SIZES = [96, 84, 72, 64, 56]
BODY_SIZES = [64, 58, 52, 46, 42, 38]


def parse_cards(path: Path) -> list[dict]:
    """Достаёт карточки из раздела «Instagram: карусель»."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"## Instagram: карусель\n(.*?)(?=\n## |\Z)", text, re.S)
    if not match:
        raise ValueError(f"{path.name}: нет раздела «## Instagram: карусель»")

    cards: list[dict] = []
    for block in re.finditer(r"### Карточка (\d+)([^\n]*)\n(.*?)(?=\n### |\Z)",
                             match.group(1), re.S):
        body = " ".join(block.group(3).split())
        if not body:
            raise ValueError(f"{path.name}: карточка {block.group(1)} пустая")
        cards.append({
            "number": int(block.group(1)),
            "kind": block.group(2).strip(" —-").lower(),
            "text": body,
        })
    if not cards:
        raise ValueError(f"{path.name}: в разделе карусели нет карточек")
    return cards


def wrapped(draw: ImageDraw.ImageDraw, text: str,
            font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit(draw: ImageDraw.ImageDraw, text: str, sizes: list[int],
        max_width: int, max_height: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Подбирает самый крупный кегль, при котором текст помещается целиком.

    Обрезать текст нельзя: карточка с оборванной фразой бесполезна, поэтому
    при нехватке места берётся минимальный кегль, а вызывающий код
    предупреждает о переполнении.
    """
    for size in sizes:
        font = ImageFont.truetype(str(SANS_BOLD), size)
        lines = wrapped(draw, text, font, max_width)
        if len(lines) * int(size * 1.25) <= max_height:
            return font, lines
    font = ImageFont.truetype(str(SANS_BOLD), sizes[-1])
    return font, wrapped(draw, text, font, max_width)


def build_card(card: dict, total: int, out_path: Path) -> bool:
    """Рисует одну карточку. Возвращает False, если текст не поместился."""
    img = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        shade = int(INK[0] + (INK_DARK[0] - INK[0]) * (y / HEIGHT))
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade, shade + 2))

    draw.rectangle([0, 0, 14, HEIGHT], fill=ACCENT)

    is_cover = card["kind"].startswith("обложк")
    is_action = card["kind"].startswith("действ")

    small_font = ImageFont.truetype(str(SANS_BOLD), 30)
    brand_font = ImageFont.truetype(str(SANS), 28)

    # Верхняя строка: рубрика на обложке, номер карточки на остальных
    top = "МАРЖА В БЕТОНЕ" if is_cover else f"{card['number']} / {total}"
    draw.text((MARGIN, 80), top, font=small_font, fill=ACCENT)

    sizes = COVER_SIZES if is_cover or is_action else BODY_SIZES
    max_width = WIDTH - MARGIN * 2
    max_height = HEIGHT - 340
    font, lines = fit(draw, card["text"], sizes, max_width, max_height)

    line_height = int(font.size * 1.25)
    block_height = len(lines) * line_height
    y = max(180, (HEIGHT - block_height) // 2)
    for line in lines:
        draw.text((MARGIN, y), line, font=font, fill=PAPER)
        y += line_height

    # Финальная карточка обозначает действие, остальные — источник
    bottom = "ССЫЛКА В ОПИСАНИИ ПРОФИЛЯ" if is_action else "MARZHAVBETONE.RU"
    draw.text((MARGIN, HEIGHT - 90), bottom, font=brand_font,
              fill=ACCENT if is_action else CONCRETE)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return y <= HEIGHT - 140


def main() -> int:
    parser = argparse.ArgumentParser(description="Карточки карусели для Instagram")
    parser.add_argument("slug", help="имя файла в content/social без .md")
    parser.add_argument("--out", type=Path, default=None,
                        help=f"куда складывать картинки (по умолчанию {DEFAULT_OUT}/<slug>)")
    args = parser.parse_args()

    source = SOCIAL_DIR / f"{args.slug}.md"
    if not source.is_file():
        available = ", ".join(sorted(p.stem for p in SOCIAL_DIR.glob("*.md")))
        print(f"ОШИБКА: нет файла {source.relative_to(ROOT)}. Доступны: {available}",
              file=sys.stderr)
        return 1

    try:
        cards = parse_cards(source)
    except ValueError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 1

    out_dir = args.out or (DEFAULT_OUT / args.slug)
    overflow = []
    for card in cards:
        path = out_dir / f"{card['number']:02d}.png"
        if not build_card(card, len(cards), path):
            overflow.append(card["number"])
        print(f"  {path.name} — {card['text'][:60]}")

    print(f"Готово: {len(cards)} карточек в {out_dir}")
    if overflow:
        print(f"ВНИМАНИЕ: текст не помещается на карточках {overflow} — сократите его "
              f"в {source.relative_to(ROOT)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
