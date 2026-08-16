#!/usr/bin/env python3
"""Разрез снимка по нашим UTM-меткам: разбор ответа Метрики и своды.

Зачем проверка. Разрез отвечает на единственный вопрос, ради которого
размечаются ссылки каналов: сколько визитов дал телеграм, сколько Дзен,
сколько Инстаграм. Ошибиться тут можно тихо и тремя способами, и каждый
читается как ответ:

  · визиты без метки попадают в «прочие каналы» — и весь прямой и
    поисковый трафик превращается в чужой канал;
  · Метрика не вернула ряд без метки вовсе — и «без метки» становится
    нулём, хотя визиты были;
  · цели нет в счётчике — и «не измерено» превращается в ноль
    достижений, то есть в «канал не продаёт».

Живые данные проверкой не заменяются: сюда кладутся записанные ответы,
чтобы поймать исчезновение разреза и порчу разбора. Сам прогон идёт из
Actions — из облачной сессии адрес Метрики закрыт.

    python3 tools/test_metrika_utm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrika_report as mr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Ответ Метрики на разрез по источнику метки: визиты и три ступени.
# Последний ряд — визиты без метки, Метрика отдаёт их пустым именем.
BY_SOURCE = {"data": [
    {"dimensions": [{"name": ""}], "metrics": [21.0, 2.0, 0.0, 0.0]},
    {"dimensions": [{"name": "telegram"}], "metrics": [9.0, 4.0, 2.0, 1.0]},
    {"dimensions": [{"name": "dzen"}], "metrics": [3.0, 1.0, 0.0, 0.0]},
    {"dimensions": [{"name": "vc"}], "metrics": [1.0, 0.0, 0.0, 0.0]},
]}

BY_CAMPAIGN = {"data": [
    {"dimensions": [{"name": "telegram"}, {"name": "post"},
                    {"name": "srok-uderzhaniya"}], "metrics": [5.0]},
    {"dimensions": [{"name": "telegram"}, {"name": "post"},
                    {"name": "avans-kryuchok"}], "metrics": [4.0]},
    {"dimensions": [{"name": ""}, {"name": ""}, {"name": ""}], "metrics": [21.0]},
]}

GOALS = {"product_opened": 11, "checkout_open": 12, "purchase": 13}

failures: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    print(f"{'OK  ' if ok else 'ДЕФЕКТ'} {name}\n       {detail}")
    if not ok:
        failures.append(name)


def fake_stat(answers: list):
    """Подменяет запрос к Метрике записанными ответами по порядку вызова."""
    queue = list(answers)
    seen: list[str] = []

    def call(token, counter, metrics, d1, d2, dimensions="", limit=20):
        seen.append(dimensions)
        answer = queue.pop(0)
        # BaseException, а не Exception: отказ Метрики приходит SystemExit,
        # и по Exception он не поймался бы — заглушка вернула бы сам объект.
        if isinstance(answer, BaseException):
            raise answer
        return answer

    call.seen = seen  # type: ignore[attr-defined]
    return call


def run(answers: list, goals: dict, total_visits: float) -> dict:
    original = mr.stat
    mr.stat = fake_stat(answers)
    try:
        return mr.utm_report("t", "1", goals, "2026-08-07", "2026-08-13",
                             total_visits)
    finally:
        mr.stat = original


# 1. Обычный случай: своды по каналам и ступени по источнику
report = run([BY_SOURCE, BY_CAMPAIGN], GOALS, 34.0)
check("визиты с меткой и без разведены",
      report["attributed_visits"] == 13.0 and report["by_channel"]["none"] == 21.0,
      f"с меткой {report['attributed_visits']}, без метки "
      f"{report['by_channel']['none']}")

check("канал называется строкой свода",
      report["by_channel"].get("telegram") == 9.0
      and report["by_channel"].get("dzen") == 3.0
      and report["by_channel"].get("instagram") == 0.0,
      str(report["by_channel"]))

check("незнакомый источник идёт в прочие, а не в канал",
      report["by_channel"].get("other_utm") == 1.0,
      "vc не объявлен в data/content/rules.yaml — 1 визит в other_utm")

check("ступени воронки едут вместе с источником",
      report["sources"][0]["source"] == "telegram"
      and report["sources"][0]["purchase"] == 1.0
      and report["sources"][0]["checkout_open"] == 2.0,
      str(report["sources"][0]))

check("кампании разобраны с медиумом и слагом",
      any(c["campaign"] == "srok-uderzhaniya" and c["medium"] == "post"
          and c["source"] == "telegram" for c in report["campaigns"])
      and all(c["source"] for c in report["campaigns"]),
      f"кампаний {len(report['campaigns'])}, без метки отброшены")

# 2. Цели нет в счётчике: «не измерено» не должно стать нулём
report = run([BY_SOURCE, BY_CAMPAIGN], {"product_opened": 11}, 34.0)
telegram = next(r for r in report["sources"] if r["source"] == "telegram")
check("цель вне счётчика даёт null, а не ноль",
      telegram["purchase"] is None and telegram["product_opened"] == 4.0,
      f"purchase={telegram['purchase']!r}, product_opened={telegram['product_opened']}")

# 3. Метрика не вернула ряд без метки — ноль был бы ложью
only_marked = {"data": [r for r in BY_SOURCE["data"] if r["dimensions"][0]["name"]]}
report = run([only_marked, BY_CAMPAIGN], GOALS, 34.0)
check("без метки считается и когда ряда нет",
      report["by_channel"]["none"] == 21.0,
      "34 визита всего, 13 с меткой — 21 без метки берётся вычитанием")

# 4. Отказ API не должен ронять весь снимок
report = run([SystemExit("Метрика ответила 400 на /stat/v1/data: bad dimension"),
              BY_CAMPAIGN], GOALS, 34.0)
check("отказ разреза записан строкой, а не обрушил прогон",
      report["error"] and "400" in report["error"] and report["sources"] == [],
      str(report["error"])[:80])

# 5. Разрез не должен исчезнуть из снимка при следующей правке
source = (ROOT / "tools" / "metrika_report.py").read_text(encoding="utf-8")
check("снимок несёт ключ utm",
      '"utm": utm' in source, "ключ utm в сборке снимка main()")
check("прежний разрез источников остался на месте",
      "ym:s:lastTrafficSource" in source and '"sources": [{"source"' in source,
      "lastTrafficSource отвечает на другой вопрос и не заменяется")
check("измерения меток названы явно",
      "ym:s:UTMSource" in source and "ym:s:UTMCampaign" in source
      and "ym:s:UTMMedium" in source,
      "источник, канал и кампания")

print()
if failures:
    print(f"ДЕФЕКТОВ — {len(failures)}: {', '.join(failures)}")
    sys.exit(1)
print("Разрез снимка по меткам: расхождений нет.")
