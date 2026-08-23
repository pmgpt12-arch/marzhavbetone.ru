#!/usr/bin/env python3
"""Кадры чужого ролика: единственный способ разобрать его механику честно.

ЗАЧЕМ. У карточки референса есть числа, но поля суждения — крючок, ритм
резов, доля живого видео, стиль надписей — ставит тот, кто ролик видел.
Из облачной сессии видео не открыть: адреса Инстаграма закрыты выходным
прокси. У своей машины сеть есть, и есть ffmpeg.

ЧТО ДЕЛАЕТ. По каждой карточке с `video_url` скачивает ролик во временный
файл, вынимает кадры и складывает в `content/reels/references/frames/<id>/`.
Само видео не сохраняется: нам нужен разбор, а не чужая копия. Каталог
`content/` не выкладывается.

ГДЕ ГУЩЕ КАДРЫ. Первые три секунды решают всё: зритель уходит на первой.
Поэтому там кадр каждые полсекунды, дальше — раз в две.

ССЫЛКИ ЖИВУТ НЕДОЛГО. Адреса подписаны и протухают за часы. Отказ по
такому адресу — не дефект инструмента, а повод пересобрать карточки; это
говорится словами, а не кодом 1 без объяснения.

    python3 tools/reference_frames.py                 # всем, у кого кадров нет
    python3 tools/reference_frames.py --card <файл>   # одной карточке
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
КАРТОЧКИ = ROOT / "content" / "reels" / "references" / "cards"
КАДРЫ = ROOT / "content" / "reels" / "references" / "frames"

# Отметки времени в секундах. Плотно в начале — там решается, останется ли
# зритель; дальше реже, потому что дальше смотрят уже по инерции сюжета.
НАЧАЛО = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
ШАГ_ДАЛЬШЕ = 2.0
ПРЕДЕЛ_КАДРОВ = 24

ВЫСОТА = 480          # кадра хватает, чтобы прочитать надписи, вес втрое меньше
ТАЙМАУТ_СКАЧИВАНИЯ = 120


class FramesError(Exception):
    """Отказ, о котором можно сказать словами."""


def отметки(длительность: float) -> list[float]:
    точки = [t for t in НАЧАЛО if t < длительность]
    t = НАЧАЛО[-1] + ШАГ_ДАЛЬШЕ
    while t < длительность and len(точки) < ПРЕДЕЛ_КАДРОВ:
        точки.append(round(t, 1))
        t += ШАГ_ДАЛЬШЕ
    return точки or [0.0]


def скачать(адрес: str, куда: Path, opener=None) -> None:
    открыть = opener or urllib.request.urlopen
    запрос = urllib.request.Request(адрес, headers={
        # Без узнаваемого клиента раздача отвечает отказом.
        "User-Agent": "Mozilla/5.0 (compatible; marzha-reference-frames/1.0)",
    })
    try:
        with открыть(запрос, timeout=ТАЙМАУТ_СКАЧИВАНИЯ) as ответ, куда.open("wb") as файл:
            shutil.copyfileobj(ответ, файл)
    except urllib.error.HTTPError as exc:
        raise FramesError(
            f"HTTP {exc.code} {exc.reason}. Подписанные адреса Инстаграма живут "
            "часы: если ролик собран давно, карточки надо пересобрать, а не "
            "чинить инструмент."
        ) from exc
    except OSError as exc:
        raise FramesError(f"{type(exc).__name__}: {exc}") from exc


def вырезать(видео: Path, точки: list[float], каталог: Path, runner=None) -> list[Path]:
    запустить = runner or (lambda cmd: subprocess.run(cmd, capture_output=True))
    каталог.mkdir(parents=True, exist_ok=True)
    готовые = []
    for номер, отметка in enumerate(точки, start=1):
        путь = каталог / f"{номер:02d}-{отметка:g}s.jpg"
        итог = запустить([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{отметка}", "-i", str(видео),
            "-frames:v", "1", "-vf", f"scale=-2:{ВЫСОТА}", "-q:v", "4",
            str(путь),
        ])
        if getattr(итог, "returncode", 1) == 0 and путь.exists():
            готовые.append(путь)
    if not готовые:
        raise FramesError("ffmpeg не отдал ни одного кадра — проверить, что он есть "
                          "в PATH и что файл ролика скачался целиком")
    return готовые


def подпись(карточка: dict) -> str:
    """Текст подписи из сырого ответа. Он уже добыт, добывать заново нечего."""
    сырое = карточка.get("raw") or {}
    медиа = сырое.get("media") if isinstance(сырое.get("media"), dict) else сырое
    заголовок = медиа.get("caption")
    if isinstance(заголовок, dict):
        return str(заголовок.get("text") or "")
    return ""


def обработать(путь: Path, *, перезаписать: bool = False,
               opener=None, runner=None) -> tuple[str, int]:
    карточка = yaml.safe_load(путь.read_text(encoding="utf-8")) or {}
    ид = str(карточка.get("id") or путь.stem)
    адрес = str(карточка.get("video_url") or "")
    каталог = КАДРЫ / ид

    if not адрес:
        return f"{ид}: в карточке нет video_url — кадры взять неоткуда", 0
    if каталог.exists() and any(каталог.glob("*.jpg")) and not перезаписать:
        return f"{ид}: кадры уже есть", 0

    точки = отметки(float(карточка.get("duration_sec") or 0) or 30.0)
    with tempfile.TemporaryDirectory() as временный:
        видео = Path(временный) / "reel.mp4"
        скачать(адрес, видео, opener)
        кадры = вырезать(видео, точки, каталог, runner)

    текст = подпись(карточка)
    if текст:
        (каталог / "caption.txt").write_text(текст, encoding="utf-8")
    return f"{ид}: кадров {len(кадры)}" + (", подпись сохранена" if текст else ""), len(кадры)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--card", default=None, help="одна карточка вместо всех")
    parser.add_argument("--force", action="store_true", help="переснять уже готовые")
    args = parser.parse_args(argv)

    файлы = ([Path(args.card)] if args.card
             else sorted(КАРТОЧКИ.glob("*.yaml")) if КАРТОЧКИ.exists() else [])
    if not файлы:
        print("Карточек нет — нечего разбирать", file=sys.stderr)
        return 0

    всего, отказов = 0, 0
    for файл in файлы:
        try:
            строка, число = обработать(файл, перезаписать=args.force)
            всего += число
            print(строка)
        except FramesError as exc:
            отказов += 1
            print(f"{файл.stem}: {exc}", file=sys.stderr)

    print(f"\nКадров вырезано: {всего}, карточек с отказом: {отказов}")
    # Отказ по части карточек не роняет прогон: часть кадров лучше, чем ничего,
    # а причина названа построчно.
    return 0


if __name__ == "__main__":
    sys.exit(main())
