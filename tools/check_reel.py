#!/usr/bin/env python3
"""Проверяет сценарии роликов до того, как по ним что-то снимут.

Ошибка в сценарии стоит дороже ошибки в коде: по нему снимают, генерируют
кадры и платят за генерацию. Дешевле поймать её текстом.

    python3 tools/check_reel.py                       # все сценарии
    python3 tools/check_reel.py content/reels/01-*.md  # конкретные

Код возврата 1, если хотя бы один сценарий не прошёл.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REELS_DIR = ROOT / "content" / "reels"
HOOKS = REELS_DIR / "hooks.md"

# Скорость чтения текста на экране. Выше этого зритель не успевает, и
# кадр работает вхолостую: он его пролистает, не дочитав.
MAX_CHARS_PER_SECOND = 20
# Крючок обязан уложиться в первые секунды — дальше зритель уже решил
MAX_HOOK_END = 4
# Наша серия. Меняем длительность осознанно, а не потому что так вышло
EXPECTED_DURATION = 22

REQUIRED_SECTIONS = ["Крючок", "Тело", "Финал", "Оговорка"]
REQUIRED_FIELDS = ["Механика", "Гипотеза", "Ссылка"]

# Обещания результата, которых мы не даём: юридическая тема, исход зависит
# от документов, а не от нашего шаблона
BANNED = [
    "вернём ваши деньги",
    "вернем ваши деньги",
    "гарантируем",
    "100% результат",
    "обязательно выиграете",
    "точно взыщете",
]

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]"
)
TIME_IN_HEADER = re.compile(r"\((\d+)\s*[–—-]\s*(\d+)\s*с\)")
TIME_IN_BEAT = re.compile(r"\*\*(\d+)\s*[–—-]\s*(\d+)\s*с\*\*")
FENCED = re.compile(r"```\n(.*?)\n```", re.S)


def known_mechanics() -> set[str]:
    if not HOOKS.is_file():
        return set()
    return set(re.findall(r"^## (М\d+)\.", HOOKS.read_text(encoding="utf-8"), re.M))


def beats(text: str) -> list[dict]:
    found: list[dict] = []
    for section in re.split(r"\n## ", text):
        title = section.split("\n", 1)[0]
        if title.startswith(("Крючок", "Финал")):
            times = TIME_IN_HEADER.search(title)
            block = FENCED.search(section)
            if times and block:
                found.append({
                    "start": int(times.group(1)),
                    "end": int(times.group(2)),
                    "text": block.group(1).strip(),
                    "kind": "hook" if title.startswith("Крючок") else "final",
                })
        elif title.startswith("Тело"):
            for beat in re.finditer(
                r"\*\*(\d+)\s*[–—-]\s*(\d+)\s*с\*\*\s*\n+```\n(.*?)\n```", section, re.S
            ):
                found.append({
                    "start": int(beat.group(1)),
                    "end": int(beat.group(2)),
                    "text": beat.group(3).strip(),
                    "kind": "beat",
                })
    return sorted(found, key=lambda b: b["start"])


def check(path: Path, mechanics: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {section}", text, re.M):
            problems.append(f"нет раздела «{section}»")
    for field in REQUIRED_FIELDS:
        if f"**{field}:**" not in text:
            problems.append(f"нет поля «{field}»")

    found = beats(text)
    if not found:
        problems.append("не найдено ни одного кадра с таймингом")
        return problems

    for left, right in zip(found, found[1:]):
        if right["start"] < left["end"]:
            problems.append(
                f"кадры {left['start']}–{left['end']} и "
                f"{right['start']}–{right['end']} перекрываются"
            )
    for beat in found:
        if beat["end"] <= beat["start"]:
            problems.append(f"кадр {beat['start']}–{beat['end']} нулевой длины")
            continue
        seconds = beat["end"] - beat["start"]
        # Переводы строк не читаются, поэтому в подсчёт не идут
        length = len(beat["text"].replace("\n", " "))
        rate = length / seconds
        if rate > MAX_CHARS_PER_SECOND:
            problems.append(
                f"кадр {beat['start']}–{beat['end']} с: {length} символов за "
                f"{seconds} с — {rate:.0f} зн/с, зритель не успевает "
                f"(предел {MAX_CHARS_PER_SECOND})"
            )

    hook = next((b for b in found if b["kind"] == "hook"), None)
    if hook and hook["end"] > MAX_HOOK_END:
        problems.append(
            f"крючок заканчивается на {hook['end']} с — позже {MAX_HOOK_END} с "
            f"решение зрителя уже принято"
        )

    duration = found[-1]["end"]
    declared = re.search(r"\*\*Длительность:\*\*\s*(\d+)", text)
    if declared and int(declared.group(1)) != duration:
        problems.append(
            f"в шапке заявлено {declared.group(1)} с, по кадрам выходит {duration} с"
        )
    if duration != EXPECTED_DURATION:
        problems.append(
            f"длительность {duration} с вместо {EXPECTED_DURATION} с — "
            f"в серии меняется только механика, иначе результаты не сравнить"
        )

    mechanic = re.search(r"\*\*Механика:\*\*\s*(М\d+)", text)
    if mechanic and mechanics and mechanic.group(1) not in mechanics:
        problems.append(f"механика {mechanic.group(1)} не описана в hooks.md")

    if not re.search(r"utm_source=instagram&utm_medium=reels", text):
        problems.append("в ссылке нет меток utm_source=instagram&utm_medium=reels")

    lowered = text.lower()
    for phrase in BANNED:
        if phrase in lowered:
            problems.append(f"обещание результата: «{phrase}»")

    if EMOJI.search(text):
        problems.append("эмодзи — их нет ни на сайте, ни в других материалах")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка сценариев роликов")
    parser.add_argument("files", nargs="*", type=Path,
                        help="файлы сценариев; по умолчанию все в content/reels")
    args = parser.parse_args()

    paths = args.files or sorted(
        p for p in REELS_DIR.glob("*.md")
        if re.match(r"\d{2}-", p.name)
    )
    if not paths:
        print("Сценариев не найдено", file=sys.stderr)
        return 1

    mechanics = known_mechanics()
    failed = 0
    for path in paths:
        problems = check(path, mechanics)
        if problems:
            failed += 1
            print(f"НЕ ПРОШЁЛ {path.name}")
            for problem in problems:
                print(f"    {problem}")
        else:
            print(f"ок        {path.name}")

    print(f"\nПроверено: {len(paths)}, с ошибками: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
