#!/usr/bin/env python3
"""База поискового спроса: фактические показы сайта, а не выдуманные частоты.

Почему не частотность Вордстата. Она отвечает на вопрос «сколько людей в
стране это спрашивают», а решение о странице требует другого: «по каким
запросам показывают именно нас и что с этими показами происходит». Второе
знают только Вебмастер и Search Console, и только про уже существующие
страницы.

Где это работает. Из облачной сессии `api.webmaster.yandex.net` закрыт
политикой сети, как `api-metrika.yandex.net` — прогон живёт в Actions
(`.github/workflows/search-demand.yml`). Токен приходит секретом.

    YANDEX_WEBMASTER_TOKEN=... python3 tools/search_demand.py --probe
    YANDEX_WEBMASTER_TOKEN=... python3 tools/search_demand.py --write

Без токена прогон говорит «НЕ ЗАПУСКАЛСЯ», а не показывает ноль строк:
пустая база и недобытая база — разные вещи, и путать их дороже всего.

Классификация намерения (MONEY / PROBLEM / INFORMATION / IRRELEVANT) идёт
правилами из `data/seo/search-demand-rules.yaml`, а не зашита в код: это
не вычисление, а суждение, и оно должно быть видно и правимо без правки
инструмента. Каждая строка помечена `updated_at`; вердикт по строке
остаётся за владельцем.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "seo" / "search-demand.csv"
RULES = ROOT / "data" / "seo" / "search-demand-rules.yaml"
HOST = "marzhavbetone.ru"
API = "https://api.webmaster.yandex.net/v4"

COLUMNS = [
    "query", "landing_url", "cluster", "intent", "money_stage",
    "impressions", "clicks", "ctr", "position", "business_value",
    "existing_solution", "recommended_action", "target_product",
    "source", "updated_at",
]

# Показатели, которые Вебмастер отдаёт по запросу.
INDICATORS = ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION"]


class ApiError(RuntimeError):
    """Отказ API с кодом. Именно с кодом: «не смог» без кода — не факт."""


def get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", "replace")[:400]
        raise ApiError(f"код {e.code} на {url}\n      {body}") from e
    except Exception as e:  # сеть, TLS, таймаут
        raise ApiError(f"{type(e).__name__} на {url}: {e}") from e


def resolve_host(token: str) -> tuple[str, str]:
    """(user_id, host_id). Оба берутся из API, а не из константы."""
    user_id = get(f"{API}/user/", token)["user_id"]
    hosts = get(f"{API}/user/{user_id}/hosts/", token)["hosts"]
    for h in hosts:
        if HOST in h.get("unicode_host_url", "") or HOST in h.get("host_id", ""):
            return str(user_id), h["host_id"]
    known = ", ".join(h.get("unicode_host_url", h.get("host_id", "?"))
                      for h in hosts) or "ни одного"
    raise ApiError(f"{HOST} не найден среди сайтов Вебмастера: {known}")


def popular_queries(token: str, user_id: str, host_id: str,
                    days: int) -> list[dict]:
    """Запросы, по которым сайт показывался, с показами и кликами."""
    params = [
        ("order_by", "TOTAL_SHOWS"),
        ("date_from", (date.today() - timedelta(days=days)).isoformat()),
        ("date_to", date.today().isoformat()),
    ]
    params += [("query_indicator", i) for i in INDICATORS]
    url = (f"{API}/user/{user_id}/hosts/{host_id}/search-queries/popular/"
           f"?{urllib.parse.urlencode(params)}")
    return get(url, token).get("queries", [])


def load_rules() -> dict:
    """Правила классификации. Формат простой намеренно — правит человек."""
    if not RULES.exists():
        return {}
    rules: dict[str, list[str]] = {}
    current = None
    for line in RULES.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith((" ", "\t")) and stripped.endswith(":"):
            current = stripped[:-1]
            rules[current] = []
        elif current and stripped.startswith("- "):
            rules[current].append(stripped[2:].strip().strip('"'))
    return rules


def classify(query: str, rules: dict) -> tuple[str, str]:
    """(intent, business_value). Предварительно — вердикт за владельцем."""
    low = query.lower()
    for intent, value in (("IRRELEVANT", "D"), ("MONEY", "A"),
                          ("PROBLEM", "B"), ("INFORMATION", "C")):
        for marker in rules.get(intent.lower(), []):
            if marker.lower() in low:
                return intent, value
    return "", ""


def existing_pages() -> dict[str, str]:
    """Опубликованные адреса — чтобы `existing_solution` не выдумывался."""
    pages = {}
    for pattern in ("articles/*.html", "materialy/*.html", "products/*.html"):
        for p in sorted(ROOT.glob(pattern)):
            if p.name == "index.html":
                continue
            pages[p.stem] = "/" + p.relative_to(ROOT).as_posix()
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--write", action="store_true",
                    help="записать data/seo/search-demand.csv")
    ap.add_argument("--probe", action="store_true",
                    help="только проверить доступ и права токена")
    args = ap.parse_args()

    token = os.environ.get("YANDEX_WEBMASTER_TOKEN", "").strip()
    if not token:
        print("YANDEX_WEBMASTER_TOKEN не задан — сбор НЕ ЗАПУСКАЛСЯ.")
        print("Это не «ноль запросов»: база не добыта, а не пуста.")
        return 2

    try:
        user_id, host_id = resolve_host(token)
    except ApiError as e:
        print(f"ОТКАЗ ВЕБМАСТЕРА: {e}")
        print("\nЧто это означает по кодам:")
        print("  401 — токен недействителен или не той службы;")
        print("  403 — у токена нет права webmaster:hostinfo;")
        print("  иное — читать тело ответа выше, оно приведено целиком.")
        return 1

    print(f"Доступ есть: user_id={user_id}, host_id={host_id}")
    if args.probe:
        return 0

    try:
        queries = popular_queries(token, user_id, host_id, args.days)
    except ApiError as e:
        print(f"ОТКАЗ НА ЗАПРОСАХ: {e}")
        return 1

    rules = load_rules()
    pages = existing_pages()
    today = date.today().isoformat()
    rows = []
    for q in queries:
        text = q.get("query_text", "")
        ind = {i["field"]: i["value"] for i in q.get("indicators", [])
               if isinstance(i, dict)} or q.get("indicators", {})
        shows = ind.get("TOTAL_SHOWS") or 0
        clicks = ind.get("TOTAL_CLICKS") or 0
        intent, value = classify(text, rules)
        rows.append({
            "query": text,
            # Вебмастер по популярным запросам посадочную не отдаёт.
            # Пусто — значит не измерено, а не «страницы нет».
            "landing_url": "",
            "cluster": "",
            "intent": intent,
            "money_stage": "",
            "impressions": shows,
            "clicks": clicks,
            "ctr": round(clicks / shows * 100, 2) if shows else "",
            "position": ind.get("AVG_SHOW_POSITION") or "",
            "business_value": value,
            "existing_solution": "",
            "recommended_action": "",
            "target_product": "",
            "source": "yandex-webmaster",
            "updated_at": today,
        })

    print(f"Запросов с показами за {args.days} дн.: {len(rows)}")
    by_intent: dict[str, int] = {}
    for r in rows:
        by_intent[r["intent"] or "не размечен"] = \
            by_intent.get(r["intent"] or "не размечен", 0) + 1
    for k in sorted(by_intent):
        print(f"  {k}: {by_intent[k]}")
    print(f"Опубликованных страниц для сверки: {len(pages)}")

    if not args.write:
        print("\nпрогон без записи; чтобы записать — --write")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nЗаписано: {OUT.relative_to(ROOT)}, строк {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
