#!/usr/bin/env python3
"""Прогон проверок репозитория по реестру `tools/ci_checks.yaml`.

ЗАЧЕМ ОН ЕСТЬ. Гейт был списком шагов Actions на `bash -e`. Такой список
останавливается на первом упавшем шаге, и всё, что стоит ниже, в CI не
исполняется вообще. Замер 27.08.2026 (аудит RC1): гейт умирал на седьмом
шаге `test_search_demand`, и `check_packages`, `check_free_materials`,
`check_rss` не отработали ни на одном PR. Два дефекта захода P0 и регресс
UTM в ленте Дзена нашлись локальным прогоном, а не гейтом, — то есть гейт
существовал, но не проверял.

ЧТО ЗДЕСЬ ИНАЧЕ. Каждая проверка идёт своим процессом; падение одной не
мешает следующей. Код возврата считается в конце и только по блокирующим:
результат job — FAIL, если упала хоть одна обязательная, и PASS, если все
обязательные прошли, сколько бы ни было предупреждений.

ПРО ПРОПУСКИ. Проверка с объявленным `требует` и отсутствующим входным
файлом не запускается и не красит прогон — но и не молчит: она печатается
строкой «НЕТ ДАННЫХ» с именем недостающего пути. Это не «silent skip»:
пропуск назван, причина названа, и как только файл вернётся, проверка
пойдёт сама, без правки реестра.

    python3 tools/run_checks.py --class public     # гейт релиза
    python3 tools/run_checks.py --class internal   # внутренний контур
    python3 tools/run_checks.py --list             # что объявлено
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

КОРЕНЬ = Path(__file__).resolve().parent.parent
РЕЕСТР = КОРЕНЬ / "tools" / "ci_checks.yaml"

# Потолок на одну проверку. Самая долгая в наборе — test_covers, 6 секунд;
# пять минут оставляют запас на медленный раннер и ловят зависание, а не
# останавливают работающую проверку.
ТАЙМАУТ = 300


class Проверка:
    def __init__(self, запись: dict):
        self.id = запись["id"]
        self.команда = запись["команда"]
        self.класс = запись["класс"]
        self.блокирует = bool(запись.get("блокирует", False))
        self.зачем = запись.get("зачем", "")
        self.требует = list(запись.get("требует", []) or [])
        self.решение = запись.get("решение", "")

    @property
    def недостающее(self) -> list[str]:
        return [п for п in self.требует if not (КОРЕНЬ / п).exists()]


def читать_реестр(файл: Path = РЕЕСТР) -> list[Проверка]:
    записи = yaml.safe_load(файл.read_text(encoding="utf-8"))["проверки"]
    известные = {"public", "internal"}
    видел: set[str] = set()
    проверки = []
    for з in записи:
        п = Проверка(з)
        if п.класс not in известные:
            raise SystemExit(f"{п.id}: неизвестный класс {п.класс!r}")
        if п.id in видел:
            raise SystemExit(f"дубликат id в реестре: {п.id}")
        if п.блокирует and п.класс != "public":
            raise SystemExit(f"{п.id}: блокирует прогон, но не в классе public")
        видел.add(п.id)
        проверки.append(п)
    return проверки


def группа(заголовок: str) -> None:
    """Свёртка в логе Actions; локально — обычная строка."""
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::group::{заголовок}", flush=True)
    else:
        print(f"── {заголовок}", flush=True)


def конец_группы() -> None:
    if os.environ.get("GITHUB_ACTIONS"):
        print("::endgroup::", flush=True)


def прогнать(п: Проверка) -> dict:
    начало = time.time()
    try:
        готово = subprocess.run(["bash", "-c", п.команда], cwd=КОРЕНЬ,
                                capture_output=True, text=True, timeout=ТАЙМАУТ)
        код, вывод = готово.returncode, готово.stdout + готово.stderr
    except subprocess.TimeoutExpired:
        код, вывод = 124, f"проверка не уложилась в {ТАЙМАУТ} с и снята"
    return {
        "id": п.id,
        "статус": "PASS" if код == 0 else "FAIL",
        "код": код,
        "секунд": round(time.time() - начало, 1),
        "вывод": вывод,
        "блокирует": п.блокирует,
        "зачем": п.зачем,
    }


def главная() -> int:
    р = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    р.add_argument("--class", dest="класс", choices=["public", "internal", "all"],
                   default="public", help="какой контур прогонять")
    р.add_argument("--list", action="store_true", help="показать реестр и выйти")
    р.add_argument("--only", help="прогнать одну проверку по id")
    # Только ради сторожа `test_run_checks.py`: он подсовывает игрушечные
    # реестры, чтобы доказать поведение раннера, не трогая настоящий.
    р.add_argument("--registry", type=Path, default=РЕЕСТР,
                   help="другой файл реестра (для проверок самого раннера)")
    аргументы = р.parse_args()

    проверки = читать_реестр(аргументы.registry)
    if аргументы.класс != "all":
        проверки = [п for п in проверки if п.класс == аргументы.класс]
    if аргументы.only:
        проверки = [п for п in проверки if п.id == аргументы.only]
        if not проверки:
            raise SystemExit(f"в реестре нет проверки {аргументы.only!r}")

    if аргументы.list:
        print(f"{'id':<26}{'класс':<10}{'блокирует':<11}зачем")
        for п in проверки:
            print(f"{п.id:<26}{п.класс:<10}{'да' if п.блокирует else 'нет':<11}{п.зачем}")
        print(f"\nвсего {len(проверки)}, из них блокирующих "
              f"{sum(1 for п in проверки if п.блокирует)}")
        return 0

    итоги, пропущены = [], []
    for п in проверки:
        нет = п.недостающее
        if нет:
            пропущены.append((п, нет))
            print(f"НЕТ ДАННЫХ  {п.id:<26} нет {', '.join(нет)}", flush=True)
            continue
        группа(f"{п.id} — {п.зачем}")
        итог = прогнать(п)
        print(итог["вывод"].rstrip())
        конец_группы()
        метка = "ok  " if итог["статус"] == "PASS" else "ПРОВАЛ"
        print(f"{метка:<11} {п.id:<26} код {итог['код']}, {итог['секунд']} с",
              flush=True)
        итоги.append(итог)

    упали = [и for и in итоги if и["статус"] == "FAIL"]
    блокирующие = [и for и in упали if и["блокирует"]]
    предупреждения = [и for и in упали if not и["блокирует"]]

    print("\n" + "=" * 72)
    print(f"контур: {аргументы.класс}")
    print(f"прогнано {len(итоги)}, прошли {len(итоги) - len(упали)}, "
          f"упали {len(упали)} (блокирующих {len(блокирующие)}, "
          f"предупреждений {len(предупреждения)}), "
          f"пропущено без данных {len(пропущены)}")

    # Упавшие называются поимённо и после сводки: в длинном логе Actions
    # верх экрана не виден, а вниз смотрят всегда.
    for и in блокирующие:
        print(f"  ПРОВАЛ (блокирует)  {и['id']} — {и['зачем']}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title={и['id']}::{и['зачем']} — код {и['код']}")
    for и in предупреждения:
        print(f"  провал (не блокирует)  {и['id']} — {и['зачем']}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning title={и['id']}::{и['зачем']} — код {и['код']}")
    for п, нет in пропущены:
        print(f"  пропущена  {п.id} — нет {', '.join(нет)}"
              + (f"; {п.решение}" if п.решение else ""))

    if блокирующие:
        print("\nИТОГ: FAIL — упала обязательная проверка.")
        return 1
    print("\nИТОГ: PASS — все обязательные проверки прошли.")
    return 0


if __name__ == "__main__":
    sys.exit(главная())
