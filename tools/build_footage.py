#!/usr/bin/env python3
"""Собирает видеоряд 1080x1920 из неподвижных кадров — движением, а не нарезкой.

Зачем отдельный шаг. `build_reel.py` кладёт текст поверх готового видео, но
видео ему нужно откуда-то взять. Съёмки у проекта нет, генерация видеомодели
закрыта (fal недоступен из облака, у higgsfield бесплатный тариф), а обложки
разборов уже собраны и выдержаны в одном визуальном языке — 16:9,
контровой свет, силуэты, стройка на заднем плане.

ПОЧЕМУ ПАНОРАМА, А НЕ ОБРЕЗКА. Кадр 16:9, приведённый к 9:16 обрезкой по
центру, теряет около двух третей ширины — вместе с композицией: у обложек
смысловой объект часто сбоку, а не по центру. Поэтому кадр масштабируется
по высоте и по нему едет окно 1080 px. Композиция показывается целиком, но
по частям, и кадр при этом заполнен без полей и без размытой подложки.

Панорама заодно решает вторую задачу: неподвижная картинка в ленте читается
как пауза, а медленное движение удерживает взгляд, ничего не обещая
зрителю сверх содержания.

    python3 tools/build_footage.py content/reels/shots/01-uderzhanie.yaml \
        --out footage-01.mp4
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

WIDTH, HEIGHT = 1080, 1920
FPS = 30
# Полная амплитуда панорамы утомляет: окно проходит долю доступного хода,
# остальное остаётся запасом, чтобы движение не упиралось в край кадра.
PAN_SPAN = 0.72
# Наезд едва заметный. Заметный превращает разбор в рекламный ролик.
ZOOM_TO = 1.06


def прогнать(команда: list[str]) -> None:
    готово = subprocess.run(команда, capture_output=True, text=True)
    if готово.returncode != 0:
        хвост = готово.stderr.strip().splitlines()[-12:]
        raise RuntimeError("ffmpeg вернул ошибку:\n" + "\n".join(хвост))


def кадр(источник: Path, длительность: float, направление: str,
         куда: Path) -> None:
    """Один план: окно 1080x1920 едет по кадру, масштабированному по высоте."""
    # Масштаб с запасом под наезд: иначе на конце движения не хватает пикселей.
    высота = int(HEIGHT * ZOOM_TO)
    ход = f"(iw-{WIDTH})*{PAN_SPAN}"
    доля = f"(t/{длительность:.3f})"
    if направление == "left":
        x = f"(iw-{WIDTH})-({ход})*{доля}"
    else:
        x = f"({ход})*{доля}"
    # Вертикаль держим по центру: вертикальный ход на этих кадрах уводит
    # либо в небо, либо в грязь под ногами.
    цепочка = (
        f"scale=-2:{высота}:flags=lanczos,"
        f"crop={WIDTH}:{HEIGHT}:x='{x}':y='(ih-{HEIGHT})/2',"
        f"fps={FPS},format=yuv420p"
    )
    прогнать([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", f"{длительность:.3f}", "-i", str(источник),
        "-vf", цепочка, "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-pix_fmt", "yuv420p", str(куда),
    ])


def склеить(планы: list[Path], куда: Path, работа: Path) -> None:
    список = работа / "список.txt"
    список.write_text(
        "".join(f"file '{п.resolve()}'\n" for п in планы), encoding="utf-8")
    прогнать([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(список),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", str(куда),
    ])


def main() -> int:
    разбор = argparse.ArgumentParser(description=__doc__)
    разбор.add_argument("shots", type=Path, help="YAML с перечнем планов")
    разбор.add_argument("--out", type=Path, required=True)
    аргументы = разбор.parse_args()

    if not shutil.which("ffmpeg"):
        print("ОШИБКА: не найден ffmpeg", file=sys.stderr)
        return 2
    if not аргументы.shots.is_file():
        print(f"ОШИБКА: нет файла {аргументы.shots}", file=sys.stderr)
        return 2

    описание = yaml.safe_load(аргументы.shots.read_text(encoding="utf-8"))
    планы = описание.get("shots") or []
    if not планы:
        print("ОШИБКА: в файле нет ни одного плана", file=sys.stderr)
        return 2

    корень = аргументы.shots.resolve().parent.parent.parent.parent
    итого = 0.0
    with tempfile.TemporaryDirectory() as врем:
        работа = Path(врем)
        готовые: list[Path] = []
        for номер, план in enumerate(планы, 1):
            источник = Path(план["image"])
            if not источник.is_absolute():
                источник = корень / источник
            if not источник.is_file():
                print(f"ОШИБКА: нет кадра {источник}", file=sys.stderr)
                return 2
            длительность = float(план.get("seconds", 4))
            направление = план.get("pan", "right" if номер % 2 else "left")
            цель = работа / f"план-{номер:02d}.mp4"
            кадр(источник, длительность, направление, цель)
            готовые.append(цель)
            итого += длительность
            print(f"  план {номер}: {источник.name} — "
                  f"{длительность:g} с, панорама {направление}")

        аргументы.out.parent.mkdir(parents=True, exist_ok=True)
        склеить(готовые, аргументы.out, работа)

    print(f"Готово: {аргументы.out} — {len(планы)} планов, {итого:g} с")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
