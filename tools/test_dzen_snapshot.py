#!/usr/bin/env python3
"""Размеченные случаи: что снимок канала считает привезённым из ленты.

Случай А — тот, на котором первая версия ошиблась. Сверка шла по словам
(`similarity`), и ручная публикация «Аванс — это не деньги. Это крючок»
совпала с ожидаемым «Аванс по договору подряда: почему работа начинается
на ваши деньги» на 67%: две общие значимые слова, делённые на длину более
короткого заголовка. Снимок объявил бы трансляцию включённой на канале,
куда лента ничего не привозила.

    python3 tools/test_dzen_snapshot.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dzen_channel


# Ручные публикации канала: они исключены из ленты (PUBLISHED_BY_HAND),
# поэтому ни одна из них привезённой считаться не может.
MANUAL = [
    "Аванс — это не деньги. Это крючок",
    "Пять доказательств, которые заставят заплатить",
    "Подписанная КС-2 не значит, что вам заплатят",
]


def read(field: str, text: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""


def main() -> int:
    problems: list[str] = []
    expected = dzen_channel.expected_from_feed()

    if not expected:
        print("ДЕФЕКТ: ленте нечего привозить — expected_from_feed() пуст")
        return 1

    def snap(titles: list[str]) -> str:
        return dzen_channel.snapshot([{"title": t} for t in titles], 0.6)

    # А. Трансляции нет: в канале только ручные публикации.
    text = snap(MANUAL)
    if read("feed_delivered", text) != "0":
        problems.append(
            "А: ручные публикации зачтены как привезённые лентой — "
            f"feed_delivered={read('feed_delivered', text)}, ожидался 0. "
            "Сверка снова стала нестрогой"
        )
    if read("translation_live", text) != "unknown":
        problems.append(
            "А: при нуле привезённых состояние трансляции объявлено "
            f"«{read('translation_live', text)}», а оно неизвестно: лента "
            "может быть не включена, а может не успеть отработать"
        )

    # Б. Лента привезла пять: заголовки в канале дословно те же.
    live = list(expected.values())[:5]
    text = snap(MANUAL + live)
    if read("feed_delivered", text) != "5":
        problems.append(
            f"Б: привезено пять, засчитано {read('feed_delivered', text)}"
        )
    if read("translation_live", text) != "yes":
        problems.append("Б: пять привезённых, а трансляция не признана живой")

    # В. Тот же заголовок другим регистром и кавычками — это он же.
    loud = list(expected.values())[0].upper().replace('"', "«")
    text = snap(MANUAL + [loud])
    if read("feed_delivered", text) != "1":
        problems.append(
            "В: заголовок в другом регистре не опознан — "
            f"feed_delivered={read('feed_delivered', text)}, ожидался 1"
        )

    if problems:
        for line in problems:
            print(f"ДЕФЕКТ: {line}")
        return 1

    print(f"Случаев сошлось: 3, статей ленты в расчёте: {len(expected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
