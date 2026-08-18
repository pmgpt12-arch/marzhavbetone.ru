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
# Стартовая партия V1-MVP: длительность одна на все три ролика, иначе
# результаты не сравнить — в серии меняется только механика.
EXPECTED_DURATION = 22
# V2 длительность не фиксирует: ролик собирается из сцен, и число сцен
# диктует хронометраж. Окно объявлено стандартом.
V2_DURATION = (20, 30)

REQUIRED_SECTIONS = ["Крючок", "Тело", "Финал", "Оговорка"]
REQUIRED_FIELDS = ["Механика", "Гипотеза", "Ссылка", "Стандарт"]

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
    standard = re.search(r"^\*\*Стандарт:\*\*\s*(\S+)", text, re.M)
    standard = standard.group(1) if standard else ""
    if standard == "V2":
        if not V2_DURATION[0] <= duration <= V2_DURATION[1]:
            problems.append(
                f"длительность {duration} с вне окна "
                f"{V2_DURATION[0]}–{V2_DURATION[1]} с стандарта V2")
    elif duration != EXPECTED_DURATION:
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

    problems += check_cta(path, text, found)
    return problems


# --- Призыв к действию -------------------------------------------------
#
# Дефект назван владельцем 16.08.2026 после просмотра готовых роликов:
# зритель досматривает и не знает, что делать. Финалы всех шести сценариев
# кончались наблюдением, а слова «ссылка в профиле» жили в строке «Голос
# или подпись» — она на экран не попадает вовсе.
#
# Проверяется то, что выражается текстом. Похож ли ролик на слайдшоу и
# объясняет ли кадр сказанное — смотрит человек на готовом mp4: оба
# дефекта первых трёх роликов нашлись именно так.

ROUTE_FIELDS = ["PAIN", "INTENT", "TARGET LANDING", "TARGET PRODUCT",
                "PRIMARY CTA", "CTA TYPE", "UTM CAMPAIGN"]
CTA_TYPES = {"DIAGNOSTIC", "FREE_ENTRY", "PRODUCT"}
# V1-MVP — стартовая партия из трёх роликов, допущенная владельцем
# 16.08.2026 как есть. Всё, что делается после неё, — V2.
STANDARDS = {"V1-MVP", "V2"}
# Обложка разбора допустима вспомогательным кадром, но не основой ролика
MAX_COVER_SHARE = 0.5
# Ролик 20–30 с — это 5–8 визуально разных сцен. Меньше пяти означает,
# что кадр висит на экране, пока говорит голос.
MIN_SCENES = 5
CTA_MIN_SECONDS, CTA_MAX_SECONDS = 2, 4
CTA_ANCHOR = "ссылка в профиле"

# Приглашения вместо действия: зритель не знает, что именно сделает
GENERIC_CTA = [
    "узнайте больше", "узнать больше", "переходите по ссылке",
    "переходи по ссылке", "смотрите на сайте", "подробнее на сайте",
    "подписывайтесь", "подпишитесь", "подпишись",
]
STOPWORDS = {"в", "и", "на", "по", "не", "с", "своё", "свое", "своим",
             "ссылка", "профиле", "до", "за", "к", "о", "а", "у"}


def flat(text: str) -> str:
    """Перенос строки и отступ YAML не должны прятать фразу от поиска."""
    return re.sub(r"\s+", " ", text)


def significant(text: str) -> set[str]:
    words = re.findall(r"[а-яёa-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def check_not_slideshow(shots: Path) -> list[str]:
    """V2 не собирается из готовых обложек сайта: это видно как автонарезка."""
    import yaml

    plan = yaml.safe_load(shots.read_text(encoding="utf-8")) or {}
    if "scenes" in plan:
        сцены = plan["scenes"]
        if len(сцены) < MIN_SCENES:
            return [f"сцен {len(сцены)}, а V2 требует не меньше {MIN_SCENES}: "
                    f"меньше — это подложка под голос, а не ролик"]
        total = sum(float(s.get("seconds", 0)) for s in сцены)
        covers = sum(float(s.get("seconds", 0)) for s in сцены
                     if str((s.get("props") or {}).get("image", ""))
                     .startswith("assets/"))
    else:
        total = covers = 0
        for shot in plan.get("shots", []):
            seconds = float(shot.get("seconds", 0))
            total += seconds
            if str(shot.get("image", "")).startswith("assets/"):
                covers += seconds
    if total and covers / total > MAX_COVER_SHARE:
        return [f"{covers:.0f} с из {total:.0f} — готовые обложки assets/ "
                f"({covers / total:.0%}); в V2 они вспомогательный кадр, "
                f"а не основа (предел {MAX_COVER_SHARE:.0%})"]
    return []


def check_cta(path: Path, text: str, found: list[dict]) -> list[str]:
    stem = re.sub(r"^(\d{2})-.*", r"\1", path.stem)
    shots = (sorted(REELS_DIR.glob(f"shots/{stem}-*.yaml"))
             or sorted(REELS_DIR.glob(f"scenes/{stem}-*.yaml")))
    if not shots:
        # Черновик: сцен нет, собирать нечего. Готовым он станет вместе с
        # планами — тогда включатся и требования ниже.
        return []
    name = shots[0].stem

    problems: list[str] = []
    standard = re.search(r"^\*\*Стандарт:\*\*\s*(\S+)", text, re.M)
    standard = standard.group(1) if standard else ""
    if standard not in STANDARDS:
        problems.append(
            f"Стандарт «{standard}» не из набора {', '.join(sorted(STANDARDS))}")
    elif standard == "V2":
        problems += check_not_slideshow(shots[0])

    for field in ROUTE_FIELDS:
        if not re.search(rf"^\*\*{re.escape(field)}:\*\*\s*\S", text, re.M):
            problems.append(f"в блоке маршрута нет поля «{field}»")

    cta_type = re.search(r"^\*\*CTA TYPE:\*\*\s*(\S+)", text, re.M)
    if cta_type and cta_type.group(1) not in CTA_TYPES:
        problems.append(
            f"CTA TYPE «{cta_type.group(1)}» не из набора "
            f"{', '.join(sorted(CTA_TYPES))}")

    landing = re.search(r"^\*\*TARGET LANDING:\*\*\s*`?([^`\s]+)", text, re.M)
    if landing and not (ROOT / landing.group(1)).exists():
        problems.append(f"целевой страницы {landing.group(1)} нет в репозитории")

    final = found[-1]
    seconds = final["end"] - final["start"]
    if not CTA_MIN_SECONDS <= seconds <= CTA_MAX_SECONDS:
        problems.append(
            f"финальный кадр {seconds} с — призыву отводится "
            f"{CTA_MIN_SECONDS}–{CTA_MAX_SECONDS} с")

    screen = final["text"].lower()
    if CTA_ANCHOR not in flat(screen):
        problems.append(f"на экране в финале нет слов «{CTA_ANCHOR}»")
    for phrase in GENERIC_CTA:
        if phrase in screen:
            problems.append(
                f"призыв «{phrase}» не называет действия — зритель не знает, "
                f"что именно сделает")

    # Три слоя не спорят: экран, голос, подпись зовут в одно место
    action = significant(screen)
    for kind, layer in (("озвучке", REELS_DIR / "voice" / f"{name}.yaml"),
                        ("подписи", REELS_DIR / "captions" / f"{name}.txt")):
        if not layer.exists():
            problems.append(f"нет файла {kind}: {layer.relative_to(ROOT)}")
            continue
        body = layer.read_text(encoding="utf-8").lower()
        if CTA_ANCHOR not in flat(body):
            problems.append(f"в {kind} нет призыва «{CTA_ANCHOR}»")
        if action and len(action & significant(body)) < 2:
            problems.append(
                f"призыв в {kind} расходится с экраном: общих слов меньше двух")

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
