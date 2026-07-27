#!/usr/bin/env python3
"""Генерирует обложку статьи в фирменном стиле «Маржи в бетоне».

Стиль по strategy.md: графитовый/бетонный фон, акцентный жёлто-золотой
цвет, крупный короткий заголовок, обязательная рубрика (eyebrow).
Формат 1200x630 — стандарт og:image, с запасом выше минимума Дзена
480x320.

Использование:
    python3 tools/build_cover.py "РУБРИКА" "Заголовок обложки" out.png
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
# Цвета взяты из styles.css сайта, чтобы обложки не расходились с брендом
INK = (36, 38, 41)          # --ink, графит
INK_DARK = (22, 23, 25)
ACCENT = (255, 90, 0)       # --orange, акцент маржи
PAPER = (248, 246, 240)     # --white
CONCRETE = (169, 164, 154)  # --concrete

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
SANS_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
SANS = FONT_DIR / "DejaVuSans.ttf"


def wrapped(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
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


def build(category: str, title: str, out_path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(img)

    # Лёгкий градиент графит -> чуть темнее, для фактуры бетона
    for y in range(HEIGHT):
        shade = int(INK[0] + (INK_DARK[0] - INK[0]) * (y / HEIGHT))
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade, shade + 2))

    # Акцентная полоса слева
    draw.rectangle([0, 0, 14, HEIGHT], fill=ACCENT)

    margin = 90
    eyebrow_font = ImageFont.truetype(str(SANS_BOLD), 30)
    title_font = ImageFont.truetype(str(SANS_BOLD), 72)
    brand_font = ImageFont.truetype(str(SANS), 28)

    # Рубрика
    draw.text((margin, 90), category.upper(), font=eyebrow_font, fill=ACCENT)

    # Заголовок, перенесённый по словам
    lines = wrapped(draw, title, title_font, WIDTH - margin * 2)
    y = 150
    line_height = 84
    for line in lines[:4]:
        draw.text((margin, y), line, font=title_font, fill=PAPER)
        y += line_height

    # Марка внизу
    draw.text((margin, HEIGHT - 80), "МАРЖА В БЕТОНЕ", font=brand_font, fill=CONCRETE)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")


def main() -> int:
    if len(sys.argv) != 4:
        print("Использование: build_cover.py РУБРИКА 'Заголовок' out.png", file=sys.stderr)
        return 1
    category, title, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    build(category, title, out)
    print(f"Обложка сохранена: {out} ({WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
