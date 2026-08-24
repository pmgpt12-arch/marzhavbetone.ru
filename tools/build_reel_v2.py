#!/usr/bin/env python3
"""Собирает ролик по стандарту V2 из списка сцен.

Чем отличается от build_reel.py. Тот кладёт надписи поверх одного готового
видеоряда, и видеоряд у него — панорама по неподвижным обложкам сайта.
Решением владельца 16.08.2026 этот формат закрыт как основной: он выглядит
автоматической нарезкой материалов, потому что ею и является.

Здесь ролик — последовательность сцен, у каждой свой способ сборки.
Движение даёт не панорама, а анимация: вход текста, появление строк списка,
счёт цифр. Кадр под сцену снимается отдельно, обложки разборов в пул кадров
не входят.

    python3 tools/build_reel_v2.py content/reels/scenes/07-dopraboty.yaml \
        --voice out/voice/07-dopraboty.wav --out media/07-dopraboty.mp4

Без --voice собирается немой вариант: он нужен, чтобы посмотреть картинку
до того, как оплачен синтез.

Порядок один и тот же на каждой пересборке, потому что параметры звука
заданы явно. Фильтр loudnorm сам поднимает частоту дискретизации, а
Instagram ждёт 48 кГц и чинит несовпадение перекодированием — то есть
теряет качество там, где терять нечего.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "tools" / "remotion"
FPS = 30


def прогнать(команда: list[str], где: Path | None = None) -> None:
    готово = subprocess.run(команда, cwd=где, capture_output=True, text=True)
    if готово.returncode != 0:
        хвост = (готово.stderr or готово.stdout).strip().splitlines()[-25:]
        print("\n".join(хвост), file=sys.stderr)
        raise SystemExit(f"не отработало: {' '.join(команда[:4])}…")


def проверить_среду() -> None:
    if not (REMOTION / "node_modules").is_dir():
        raise SystemExit(
            "нет зависимостей Remotion. Поставьте:\n"
            "    cd tools/remotion && npm install\n"
            "    npx remotion browser ensure")
    if not shutil.which("ffmpeg"):
        raise SystemExit("нет ffmpeg: apt-get install -y ffmpeg")


def отрисовать(сцена: dict, куда: Path) -> Path:
    """Одна сцена — один mp4. Длительность задаётся планом, а не сценой."""
    имя = сцена["id"]
    состав = сцена["composition"]
    секунды = float(сцена["seconds"])
    props = dict(сцена.get("props") or {})
    # Сцены с собственной длительностью читают её из props: иначе план и
    # сцена разойдутся молча, и ролик окажется длиннее заявленного
    if состав == "PhotoStatementScene":
        props["durationSec"] = секунды

    файл = куда / f"{имя}.mp4"
    прогнать([
        "npx", "remotion", "render", "src/index.ts", состав, str(файл),
        f"--props={json.dumps(props, ensure_ascii=False)}",
    ], где=REMOTION)

    # Сцены зарегистрированы с фиксированной длительностью, и план имеет
    # право попросить короче. Подрезаем по плану, а не подстраиваем план.
    ровно = куда / f"{имя}-ровно.mp4"
    прогнать([
        "ffmpeg", "-y", "-v", "error", "-i", str(файл), "-t", str(секунды),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", str(ровно),
    ])
    длина = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(ровно)],
        capture_output=True, text=True).stdout.strip())
    if abs(длина - секунды) > 0.2:
        print(f"  ВНИМАНИЕ: сцена {имя} вышла {длина:.1f} с вместо {секунды} с "
              f"— зарегистрированная длительность короче плана", file=sys.stderr)
    print(f"  сцена {имя}: {состав}, {длина:.1f} с")
    return ровно


def длительность_потока(файл: Path, поток: str) -> float:
    """ffprobe отдаёт csv с хвостовой запятой — разбор должен это пережить."""
    вывод = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", поток,
         "-show_entries", "stream=duration", "-of", "csv=p=0", str(файл)],
        capture_output=True, text=True).stdout
    число = вывод.strip().splitlines()[0].strip().rstrip(",") if вывод.strip() else ""
    try:
        return float(число)
    except ValueError:
        return 0.0


def main() -> int:
    разбор = argparse.ArgumentParser(description=__doc__)
    разбор.add_argument("план", type=Path, help="список сцен")
    разбор.add_argument("--voice", type=Path, help="готовая озвучка wav")
    разбор.add_argument("--out", type=Path, required=True, help="куда положить")
    аргументы = разбор.parse_args()

    проверить_среду()
    план = yaml.safe_load(аргументы.план.read_text(encoding="utf-8"))
    сцены = план.get("scenes") or []
    if not сцены:
        raise SystemExit(f"в {аргументы.план} нет ни одной сцены")

    работа = Path(tempfile.mkdtemp(prefix="reel-v2-"))
    try:
        print(f"1/3 сцены: {len(сцены)}")
        куски = [отрисовать(сцена, работа) for сцена in сцены]

        print("2/3 склейка")
        список = работа / "куски.txt"
        список.write_text(
            "".join(f"file '{кусок}'\n" for кусок in куски), encoding="utf-8")
        немой = работа / "немой.mp4"
        прогнать(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                  "-i", str(список), "-c", "copy", str(немой)])

        аргументы.out.parent.mkdir(parents=True, exist_ok=True)
        if not аргументы.voice:
            print("3/3 без звука — озвучка не задана")
            shutil.copy(немой, аргументы.out)
        else:
            print("3/3 сведение")
            прогнать([
                "ffmpeg", "-y", "-v", "error", "-i", str(немой),
                "-i", str(аргументы.voice),
                "-filter:a", "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", str(аргументы.out),
            ])
            # Без -shortest намеренно. С ним видео обрезается по концу
            # озвучки, и первым это съедает финальную карточку призыва:
            # замер 17.08.2026 — план 20 с, голос 18,4 с, на выходе 18,5 с
            # и призыв вместо четырёх секунд стоял два с половиной.
            # План здесь главнее звука; хвост карточки без голоса нужен,
            # чтобы её успели прочитать.
            видео = длительность_потока(аргументы.out, "v:0")
            звук = длительность_потока(аргументы.out, "a:0")
            if звук > видео + 0.3:
                print(f"  ВНИМАНИЕ: голос {звук:.1f} с длиннее картинки "
                      f"{видео:.1f} с — конец фразы обрежется площадкой",
                      file=sys.stderr)
    finally:
        shutil.rmtree(работа, ignore_errors=True)

    print(f"Готово: {аргументы.out}")
    прогнать(["ffprobe", "-v", "error", "-show_entries",
              "stream=codec_name,width,height,duration",
              "-of", "default=noprint_wrappers=1", str(аргументы.out)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
