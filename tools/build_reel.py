#!/usr/bin/env python3
"""Собирает вертикальный ролик 1080x1920 из сценария content/reels/<файл>.md.

Тайминг и текст на экран уже написаны в сценарии, поэтому монтаж не требует
отдельного файла проекта: скрипт читает кадры из разметки и накладывает их
на видео.

Два режима:

    # поверх отснятого материала — текст ложится на ваше видео
    python3 tools/build_reel.py content/reels/01-uderzhanie-5-millionov.md \
        --footage sedmoy-dubl.mp4 --out reel-01.mp4

    # без съёмки — текстовые кадры на фирменном фоне, без звука
    python3 tools/build_reel.py content/reels/01-uderzhanie-5-millionov.md \
        --out reel-01.mp4

Текст держится в безопасной зоне: сверху 320 px и снизу 480 px закрывает
интерфейс Instagram — имя автора, описание, кнопки. Написанное там зритель
просто не увидит.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
# Интерфейс Instagram перекрывает края кадра
SAFE_TOP, SAFE_BOTTOM = 320, 480

INK = (36, 38, 41)
INK_DARK = (22, 23, 25)
ACCENT = (255, 90, 0)
PAPER = (248, 246, 240)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
SANS_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"

HOOK_SIZES = [92, 80, 72, 64, 56]
BEAT_SIZES = [72, 64, 58, 52, 46, 42]

TIME_IN_HEADER = re.compile(r"\((\d+)\s*[–—-]\s*(\d+)\s*с\)")
TIME_IN_BEAT = re.compile(r"\*\*(\d+)\s*[–—-]\s*(\d+)\s*с\*\*")
FENCED = re.compile(r"```\n(.*?)\n```", re.S)


def parse_script(path: Path) -> list[dict]:
    """Достаёт кадры: (начало, конец, текст на экран)."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    sections = re.split(r"\n## ", text)
    beats: list[dict] = []

    for section in sections:
        title = section.split("\n", 1)[0]
        if title.startswith("Крючок") or title.startswith("Финал"):
            times = TIME_IN_HEADER.search(title)
            block = FENCED.search(section)
            if not times or not block:
                raise ValueError(f"{path.name}: в разделе «{title}» нет тайминга или текста")
            beats.append({
                "start": int(times.group(1)),
                "end": int(times.group(2)),
                "text": block.group(1).strip(),
                "kind": "hook" if title.startswith("Крючок") else "final",
            })
        elif title.startswith("Тело"):
            for beat in re.finditer(
                r"\*\*(\d+)\s*[–—-]\s*(\d+)\s*с\*\*\s*\n+```\n(.*?)\n```", section, re.S
            ):
                beats.append({
                    "start": int(beat.group(1)),
                    "end": int(beat.group(2)),
                    "text": beat.group(3).strip(),
                    "kind": "beat",
                })

    if not beats:
        raise ValueError(f"{path.name}: не нашёл ни одного кадра с таймингом")

    beats.sort(key=lambda b: b["start"])
    for beat in beats:
        if beat["end"] <= beat["start"]:
            raise ValueError(
                f"{path.name}: кадр {beat['start']}–{beat['end']} с длится ноль или меньше"
            )
    for left, right in zip(beats, beats[1:]):
        if right["start"] < left["end"]:
            raise ValueError(
                f"{path.name}: кадры {left['start']}–{left['end']} и "
                f"{right['start']}–{right['end']} перекрываются"
            )
    return beats


def wrapped(draw: ImageDraw.ImageDraw, text: str,
            font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Переносит по словам, сохраняя переводы строк из сценария."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
    return lines


def fit(draw: ImageDraw.ImageDraw, text: str, sizes: list[int],
        max_width: int, max_height: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in sizes:
        font = ImageFont.truetype(str(SANS_BOLD), size)
        lines = wrapped(draw, text, font, max_width)
        if len(lines) * int(size * 1.3) <= max_height:
            return font, lines
    font = ImageFont.truetype(str(SANS_BOLD), sizes[-1])
    return font, wrapped(draw, text, font, max_width)


def render_beat(beat: dict, transparent: bool) -> Image.Image:
    """Кадр с текстом: прозрачный для наложения, с фоном — для видео без съёмки."""
    if transparent:
        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    else:
        img = Image.new("RGBA", (WIDTH, HEIGHT), INK + (255,))
        gradient = ImageDraw.Draw(img)
        for y in range(HEIGHT):
            shade = int(INK[0] + (INK_DARK[0] - INK[0]) * (y / HEIGHT))
            gradient.line([(0, y), (WIDTH, y)], fill=(shade, shade, shade + 2, 255))
        gradient.rectangle([0, 0, 14, HEIGHT], fill=ACCENT + (255,))

    draw = ImageDraw.Draw(img)
    margin = 80
    sizes = HOOK_SIZES if beat["kind"] in {"hook", "final"} else BEAT_SIZES
    font, lines = fit(draw, beat["text"], sizes,
                      WIDTH - margin * 2, HEIGHT - SAFE_TOP - SAFE_BOTTOM)

    line_height = int(font.size * 1.3)
    block = len(lines) * line_height
    y = SAFE_TOP + (HEIGHT - SAFE_TOP - SAFE_BOTTOM - block) // 2

    for line in lines:
        if transparent:
            # Подложка под строкой: на светлом кадре белый текст иначе пропадает
            width = draw.textlength(line, font=font)
            draw.rectangle(
                [margin - 24, y - 10, margin + width + 24, y + line_height - 6],
                fill=INK + (215,),
            )
        draw.text((margin, y), line, font=font, fill=PAPER)
        y += line_height

    return img


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-6:])
        raise RuntimeError(f"ffmpeg вернул ошибку:\n{tail}")


def build_with_footage(beats: list[dict], footage: Path, out: Path, work: Path) -> None:
    overlays = []
    for index, beat in enumerate(beats):
        path = work / f"beat{index}.png"
        render_beat(beat, transparent=True).save(path)
        overlays.append(path)

    inputs: list[str] = ["-i", str(footage)]
    for path in overlays:
        inputs += ["-i", str(path)]

    # Кадр приводится к 9:16 обрезкой по центру, чтобы не появились поля
    chain = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1[base]"
    ]
    current = "base"
    for index, beat in enumerate(beats):
        nxt = f"v{index}"
        chain.append(
            f"[{current}][{index + 1}:v]overlay=0:0:"
            f"enable='between(t,{beat['start']},{beat['end']})'[{nxt}]"
        )
        current = nxt

    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(chain),
        "-map", f"[{current}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        str(out),
    ])


def build_text_only(beats: list[dict], out: Path, work: Path) -> None:
    listing = work / "concat.txt"
    lines = []
    for index, beat in enumerate(beats):
        path = work / f"frame{index}.png"
        render_beat(beat, transparent=False).convert("RGB").save(path)
        lines.append(f"file '{path}'")
        lines.append(f"duration {beat['end'] - beat['start']}")
    # Последний кадр повторяется: concat отбрасывает длительность финального файла
    lines.append(f"file '{work}/frame{len(beats) - 1}.png'")
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")

    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
        "-vf", "fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        str(out),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка вертикального ролика")
    parser.add_argument("script", type=Path, help="файл сценария из content/reels")
    parser.add_argument("--footage", type=Path, default=None,
                        help="отснятый материал; без него собирается текстовый ролик")
    parser.add_argument("--out", type=Path, required=True, help="куда сохранить mp4")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        print("ОШИБКА: не найден ffmpeg", file=sys.stderr)
        return 1
    if not args.script.is_file():
        print(f"ОШИБКА: нет файла {args.script}", file=sys.stderr)
        return 1
    if args.footage and not args.footage.is_file():
        print(f"ОШИБКА: нет файла {args.footage}", file=sys.stderr)
        return 1

    try:
        beats = parse_script(args.script)
    except ValueError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 1

    duration = beats[-1]["end"]
    print(f"Кадров: {len(beats)}, хронометраж по сценарию: {duration} с")
    for beat in beats:
        first = beat["text"].split("\n")[0]
        print(f"  {beat['start']:>3}–{beat['end']:<3} с  {first[:52]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        try:
            if args.footage:
                build_with_footage(beats, args.footage, args.out, work)
            else:
                build_text_only(beats, args.out, work)
        except RuntimeError as exc:
            print(f"ОШИБКА: {exc}", file=sys.stderr)
            return 1

    print(f"Готово: {args.out}")
    if args.footage:
        print("Проверьте, что текст не перекрывает лицо: подложки ставятся по левому краю.")
    else:
        print("Ролик без звука — для публикации добавьте дорожку в приложении.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
