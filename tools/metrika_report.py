#!/usr/bin/env python3
"""Забирает числа сайта из Яндекс.Метрики и кладёт их рядом в ряд снимков.

Зачем. План развития (`content/strategy/site-plan-2026-08-11.md`) построен на
частотности Wordstat и наличии товара — то есть на спросе рынка, а не на
поведении наших читателей. Ни одного числа о сайте в репозитории не было:
счётчик стоял, данные оставались в интерфейсе Метрики. Один снимок не
отвечает ни на один вопрос, два отвечают, поэтому снимки складываются в ряд
`content/metrics/site-<дата>.yaml` и читаются сравнением между собой.

Что забирается:
  · посещаемость за период — визиты, посетители, просмотры, отказы, время;
  · достижения целей поимённо, включая `article_to_product` и
    `article_to_magnet` — ради них цели и переехали в attribution.js;
  · двадцать самых читаемых адресов;
  · источники визитов.

Откуда что берётся. Номер счётчика — из `attribution.js`, чтобы он не жил в
двух местах и не разошёлся. Идентификаторы целей — из самой Метрики по их
именам: держать их числами в коде значит однажды считать чужую цель.

Где это работает. Из облачной сессии `api-metrika.yandex.net` закрыт
(CONNECT 403, замер 11.08.2026) — так же, как `api.telegram.org` и `dzen.ru`.
Прогон идёт из GitHub Actions (`.github/workflows/metrika.yml`) или с машины
владельца.

    METRIKA_TOKEN=... python3 tools/metrika_report.py --days 7
    METRIKA_TOKEN=... python3 tools/metrika_report.py --days 30 --write
    METRIKA_TOKEN=... python3 tools/metrika_report.py --create-goals

Отдельно про цели. Метрика считает только те, что объявлены в счётчике:
вызов `reachGoal('article_to_product')` по необъявленной цели не ошибается, а
молча ничего не делает. Четыре цели появились в коде 11.08.2026 и в счётчике
их заведомо нет — `--create-goals` заводит недостающие через API, чтобы это
не было ручным шагом в чужом интерфейсе.

Без токена это не «ноль визитов», а «не запускалась»: код возврата 2.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "content" / "metrics"
API = "https://api-metrika.yandex.net"
TIMEOUT = 40

# Цели, ради которых всё и делалось. Порядок — путь читателя, а не алфавит.
GOAL_ORDER = [
    "article_to_product", "article_to_magnet", "magnet_opened", "product_opened",
    "checklist_download", "lead_sent", "calculator_use", "calculator_to_product",
    "product_selected", "add_to_cart", "checkout_open", "purchase", "dzen_click",
    # Заведены 15.08.2026. Первые две страница диагностики слала с самого
    # своего появления, и Метрика их молча теряла: вся воронка диагностики
    # не считалась. Найдено сверкой tools/check_goals.py, которая с тех пор
    # держит список и код в согласии.
    "diagnostic_start", "diagnostic_complete", "calculator_diagnostic_click",
    # Заведены 15.08.2026 вместе с допродажей. Обе точки денежные:
    # первая считает переход по блоку «если ваша ситуация также
    # включает», вторая — переход по предложению после покупки.
    "cross_sell_click", "upsell_click",
]


def counter_id() -> str:
    """Номер счётчика — из attribution.js, единственного места, где он задан."""
    text = (ROOT / "attribution.js").read_text(encoding="utf-8")
    found = re.search(r"window\.METRIKA_ID\s*=\s*(\d+)", text)
    if not found:
        raise SystemExit("в attribution.js нет window.METRIKA_ID — счётчик брать неоткуда")
    return found.group(1)


def call(path: str, token: str, **params) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "Authorization": f"OAuth {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"Метрика ответила {error.code} на {path}: {body}")
    except urllib.error.URLError as error:
        raise SystemExit(f"до Метрики не достучались ({error.reason}). "
                         "Из облачной сессии её адрес закрыт — нужен прогон из Actions")


def goals(token: str, counter: str) -> dict[str, int]:
    """Цели счётчика по имени. Имя здесь — то же, что идентификатор события в
    `reachGoal`: цель заводится как JavaScript-событие, и её условие — ровно
    та строка, которую шлёт код."""
    data = call(f"/management/v1/counter/{counter}/goals", token)
    found: dict[str, int] = {}
    for goal in data.get("goals", []):
        found[goal["name"]] = goal["id"]
        # Считать «цель есть» надо по условию, а не по названию: название в
        # интерфейсе человек пишет как хочет, а совпасть должно условие.
        for condition in goal.get("conditions", []):
            if condition.get("url"):
                found.setdefault(condition["url"], goal["id"])
    return found


def create_goal(token: str, counter: str, name: str) -> int:
    """Заводит цель-JavaScript-событие. Без неё вызов reachGoal уходит в
    никуда: Метрика считает только объявленные цели, и молча."""
    payload = json.dumps({"goal": {
        "name": name,
        "type": "action",
        "is_retargeting": 0,
        "conditions": [{"type": "exact", "url": name}],
    }}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{API}/management/v1/counter/{counter}/goals",
        data=payload, method="POST",
        headers={"Authorization": f"OAuth {token}",
                 "Content-Type": "application/x-yametrika+json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))["goal"]["id"]
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")[:300]
        raise SystemExit(f"цель «{name}» не создалась ({error.code}): {body}")


def stat(token: str, counter: str, metrics: list[str], date1: str, date2: str,
         dimensions: str = "", limit: int = 20) -> dict:
    params = {
        "ids": counter,
        "metrics": ",".join(metrics),
        "date1": date1,
        "date2": date2,
        "limit": limit,
        "accuracy": "full",
    }
    if dimensions:
        params["dimensions"] = dimensions
        params["sort"] = "-" + metrics[0]
    return call("/stat/v1/data", token, **params)


def totals(data: dict) -> list[float]:
    return [round(x, 2) for x in data.get("totals", [])]


def rows(data: dict) -> list[tuple[str, float]]:
    out = []
    for row in data.get("data", []):
        label = row["dimensions"][0].get("name") or row["dimensions"][0].get("id") or "—"
        out.append((str(label), round(row["metrics"][0], 2)))
    return out


# Ступени воронки, которые считаются в разрезе страницы входа. Порядок —
# порядок движения к деньгам, и он же порядок колонок в отчёте.
FUNNEL_BY_LANDING = [
    "product_opened", "article_to_product",
    "add_to_cart", "checkout_open", "purchase",
]

# Разрез по нашим меткам. Он отвечает на другой вопрос, чем lastTrafficSource,
# и не заменяет его: тот называет тип источника — прямой заход, переход,
# поиск, — а этот называет наш канал. Замер 16.08.2026: в снимке за неделю
# стояло «Direct traffic 30, Recommendation 3, Link 1», и ни одно из трёх не
# отвечало на вопрос, сколько визитов дал телеграм-канал, хотя все ссылки
# в постах размечены с первого дня.
UTM_FUNNEL = ["product_opened", "checkout_open", "purchase"]

# Визит без метки Метрика отдаёт пустым именем измерения. Это не «прочий
# канал», а «метки не было»: смешать их значит превратить весь прямой и
# поисковый трафик в чужой канал.
NO_UTM_LABELS = {"", "—", "-", "none", "null", "не указано", "не определено",
                 "not set", "(none)", "undefined"}


def entry_group(path: str) -> str:
    """Куда человек вошёл: главная, каталог, разбор, прочее.

    Три группы разделены потому, что ведут себя по-разному и лечатся
    разным: на главной витрина, в каталоге перечень, в разборе текст под
    запрос. Сложенные в одно число они дают среднее, из которого не
    следует ни одного действия.
    """
    if path in ("/", "/index.html", "/#catalog", "/#top"):
        return "home"
    if path.startswith("/katalog"):
        return "catalog"
    if path.startswith("/articles/"):
        return "article"
    return "other"


def rows_multi(data: dict, names: list[str]) -> dict[str, dict[str, float]]:
    """Строки с несколькими метриками: путь → {имя метрики: значение}."""
    out: dict[str, dict[str, float]] = {}
    for row in data.get("data", []):
        dimension = row["dimensions"][0]
        label = str(dimension.get("name") or dimension.get("id") or "—")
        out[label] = {n: round(v, 2) for n, v in zip(names, row["metrics"])}
    return out


def landings(token: str, counter: str, found: dict[str, int],
             d1: str, d2: str) -> list[dict]:
    """Воронка в разрезе страницы входа.

    Двумя запросами, а не одним: Метрика ограничивает число метрик в
    запросе, и визиты берутся в обоих, чтобы строки сходились по одному
    и тому же знаменателю. Цель, которой нет в счётчике, не запрашивается
    вовсе — иначе запрос падает целиком и молчит вся таблица.
    """
    present = [name for name in FUNNEL_BY_LANDING if name in found]
    merged: dict[str, dict[str, float]] = {}
    for part in (present[:2], present[2:]):
        if not part:
            continue
        names = ["visits"] + part
        metrics = ["ym:s:visits"] + [f"ym:s:goal{found[n]}reaches" for n in part]
        data = stat(token, counter, metrics, d1, d2,
                    dimensions="ym:s:startURLPath", limit=30)
        for path, values in rows_multi(data, names).items():
            merged.setdefault(path, {}).update(values)

    out = []
    for path, values in sorted(merged.items(),
                               key=lambda kv: -kv[1].get("visits", 0)):
        row = {"path": path, "group": entry_group(path),
               "visits": values.get("visits", 0)}
        for name in FUNNEL_BY_LANDING:
            # None, а не 0: цели нет в счётчике — это «не измерено»
            row[name] = values.get(name) if name in present else None
        out.append(row)
    return out


def by_group(rows_of_landings: list[dict]) -> dict[str, dict]:
    """Свод по группам входа. Доля не считается — её порог живёт в отчёте."""
    groups: dict[str, dict] = {}
    for row in rows_of_landings:
        bucket = groups.setdefault(row["group"], {"visits": 0.0})
        bucket["visits"] += row["visits"]
        for name in FUNNEL_BY_LANDING:
            value = row.get(name)
            if value is None:
                bucket.setdefault(name, None)
                continue
            bucket[name] = (bucket.get(name) or 0) + value
    return groups


def declared_channels() -> list[str]:
    """Каналы — из стандарта меток `data/content/rules.yaml`, а не отсюда.

    Второй список каналов разошёлся бы с первым молча: канал завели бы в
    стандарте, а в отчёте он попал бы в «прочие» и остался незамеченным.
    """
    path = ROOT / "data" / "content" / "rules.yaml"
    if not path.is_file():
        return []
    block = re.search(r"^utm:\s*$(.*?)^\S", path.read_text(encoding="utf-8"),
                      re.M | re.S)
    if not block:
        return []
    found = re.search(r"^\s+sources:\s*\[([^\]]*)\]", block.group(1), re.M)
    if not found:
        return []
    return [name.strip() for name in found.group(1).split(",") if name.strip()]


def is_unmarked(label: str) -> bool:
    return label.strip().lower() in NO_UTM_LABELS


def utm_report(token: str, counter: str, found: dict[str, int],
               d1: str, d2: str, total_visits: float) -> dict:
    """Визиты в разрезе наших меток: источник, канал, кампания, ступени.

    Отдельным запросом, а не расширением прежнего: `lastTrafficSource`
    остаётся на месте и отвечает на свой вопрос. Ошибка здесь не должна
    ронять весь снимок — прежние ключи важнее нового, поэтому отказ
    записывается строкой `error`, а не обрывает прогон.
    """
    report: dict = {"attributed_visits": 0.0, "unmarked_visits": None,
                    "by_channel": {}, "sources": [], "campaigns": [],
                    "error": None}
    present = [name for name in UTM_FUNNEL if name in found]
    metrics = ["ym:s:visits"] + [f"ym:s:goal{found[n]}reaches" for n in present]
    names = ["visits"] + present

    try:
        by_source = rows_multi(
            stat(token, counter, metrics, d1, d2,
                 dimensions="ym:s:UTMSource", limit=20), names)
        by_campaign = stat(token, counter, ["ym:s:visits"], d1, d2,
                           dimensions="ym:s:UTMSource,ym:s:UTMMedium,"
                                      "ym:s:UTMCampaign", limit=40)
    except SystemExit as stop:
        # Именно так узнаётся, что идентификатор измерения не тот: Метрика
        # отвечает кодом и текстом, а не пустой таблицей.
        report["error"] = str(stop)
        return report

    attributed = 0.0
    unmarked = 0.0
    for label, values in sorted(by_source.items(),
                                key=lambda kv: -kv[1].get("visits", 0)):
        visits = values.get("visits", 0.0)
        if is_unmarked(label):
            unmarked += visits
            continue
        attributed += visits
        row = {"source": label, "visits": visits}
        for name in UTM_FUNNEL:
            # None, а не 0: цели нет в счётчике — это «не измерено»
            row[name] = values.get(name) if name in present else None
        report["sources"].append(row)

    for row in by_campaign.get("data", []):
        parts = [str(d.get("name") or d.get("id") or "") for d in row["dimensions"]]
        source, medium, campaign = (parts + ["", "", ""])[:3]
        if is_unmarked(source):
            continue
        report["campaigns"].append({
            "source": source,
            "medium": medium if not is_unmarked(medium) else None,
            "campaign": campaign if not is_unmarked(campaign) else None,
            "visits": round(row["metrics"][0], 2),
        })

    # Свод по объявленным каналам: ответ должен читаться строкой, а не
    # складываться глазами из таблицы источников.
    channels = {name: 0.0 for name in declared_channels()}
    other = 0.0
    for row in report["sources"]:
        if row["source"] in channels:
            channels[row["source"]] += row["visits"]
        else:
            other += row["visits"]
    channels["other_utm"] = other
    # Разница со списком источников — тоже «без метки»: Метрика могла не
    # вернуть пустую строку отдельным рядом, и тогда ноль был бы ложью.
    channels["none"] = round(max(unmarked, total_visits - attributed), 2)

    report["attributed_visits"] = round(attributed, 2)
    report["unmarked_visits"] = round(unmarked, 2)
    report["by_channel"] = {k: round(v, 2) for k, v in channels.items()}
    return report


def yaml_dump(value, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.append(yaml_dump(item, indent + 1))
            elif isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}: {{}}" if isinstance(item, dict) else f"{pad}{key}: []")
            elif item is None:
                lines.append(f"{pad}{key}: null")
            elif isinstance(item, str):
                lines.append(f"{pad}{key}: {json.dumps(item, ensure_ascii=False)}")
            else:
                lines.append(f"{pad}{key}: {item}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                body = yaml_dump(item, indent + 1).lstrip()
                lines.append(f"{pad}- {body}")
            else:
                lines.append(f"{pad}- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)
    return f"{pad}{value}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="за сколько последних дней")
    parser.add_argument("--write", action="store_true", help="записать снимок в content/metrics/")
    parser.add_argument("--create-goals", action="store_true",
                        help="завести в счётчике недостающие цели из кода")
    args = parser.parse_args()

    token = os.environ.get("METRIKA_TOKEN", "").strip()
    if not token:
        print("METRIKA_TOKEN не задан — сбор НЕ ЗАПУСКАЛСЯ, а не показал ноль.")
        print("  локально:  METRIKA_TOKEN=... python3 tools/metrika_report.py")
        print("  в Actions: секрет METRIKA_TOKEN, workflow .github/workflows/metrika.yml")
        return 2

    counter = counter_id()
    date2 = date.today() - timedelta(days=1)   # вчера: сегодняшний день неполон
    date1 = date2 - timedelta(days=args.days - 1)
    d1, d2 = date1.isoformat(), date2.isoformat()

    found = goals(token, counter)
    missing = [name for name in GOAL_ORDER if name not in found]
    if missing and args.create_goals:
        for name in missing:
            print(f"  создаю цель {name} … id {create_goal(token, counter, name)}")
        found = goals(token, counter)
        missing = [name for name in GOAL_ORDER if name not in found]
    known = [name for name in GOAL_ORDER if name in found]
    extra = sorted(set(found) - set(GOAL_ORDER))

    base = stat(token, counter, [
        "ym:s:visits", "ym:s:users", "ym:s:pageviews",
        "ym:s:bounceRate", "ym:s:avgVisitDurationSeconds",
    ], d1, d2)
    visits, users, pageviews, bounce, duration = (totals(base) + [0] * 5)[:5]

    reaches: dict[str, float] = {}
    if known:
        goal_metrics = [f"ym:s:goal{found[name]}reaches" for name in known]
        # Метрика ограничивает число метрик в запросе, поэтому по частям
        for start in range(0, len(known), 5):
            part = known[start:start + 5]
            data = stat(token, counter, goal_metrics[start:start + 5], d1, d2)
            for name, value in zip(part, totals(data)):
                reaches[name] = value

    pages = rows(stat(token, counter, ["ym:pv:pageviews"], d1, d2,
                      dimensions="ym:pv:URLPathFull", limit=20))
    sources = rows(stat(token, counter, ["ym:s:visits"], d1, d2,
                        dimensions="ym:s:lastTrafficSource", limit=12))
    entry_rows = landings(token, counter, found, d1, d2)
    entry_totals = by_group(entry_rows)
    utm = utm_report(token, counter, found, d1, d2, visits)

    snapshot = {
        "snapshot_date": date.today().isoformat(),
        "period": {"from": d1, "to": d2, "days": args.days},
        "counter": int(counter),
        "traffic": {
            "visits": visits, "users": users, "pageviews": pageviews,
            "bounce_rate": bounce, "avg_visit_seconds": duration,
        },
        "goals": {name: reaches.get(name, 0) for name in known},
        "goals_not_in_counter": missing,
        "goals_extra_in_counter": extra,
        "top_pages": [{"path": path, "pageviews": views} for path, views in pages],
        "sources": [{"source": name, "visits": value} for name, value in sources],
        "utm": utm,
        "landings": entry_rows,
        "entry_groups": entry_totals,
    }

    print(f"Счётчик {counter}, период {d1} — {d2} ({args.days} дн.)")
    print(f"  визитов {visits:g}, посетителей {users:g}, просмотров {pageviews:g}, "
          f"отказов {bounce:g}%, время {duration:g} с")
    if known:
        print("  цели:")
        for name in known:
            print(f"    {name:22s} {reaches.get(name, 0):g}")
    if missing:
        print("  ЦЕЛЕЙ НЕТ В СЧЁТЧИКЕ, и вызовы reachGoal по ним уходят в никуда:")
        print("    " + ", ".join(missing))
        print("    завести: python3 tools/metrika_report.py --create-goals")
    if pages:
        print("  самые читаемые:")
        for path, views in pages[:8]:
            print(f"    {views:7g}  {path}")
    if utm.get("error"):
        print("  РАЗРЕЗ ПО МЕТКАМ НЕ СОБРАН, и это не ноль визитов из каналов:")
        print(f"    {utm['error']}")
    else:
        print(f"  по нашим меткам: с меткой {utm['attributed_visits']:g}, "
              f"без метки {utm['by_channel'].get('none', 0):g}")
        for name, value in utm["by_channel"].items():
            if name == "none":
                continue
            print(f"    {name:12s} {value:6g}")
        for row in utm["sources"][:8]:
            cells = []
            for goal in UTM_FUNNEL:
                value = row.get(goal)
                cells.append("н/д" if value is None else f"{value:g}")
            print(f"    {row['source']:12s} визитов {row['visits']:6g}  "
                  + "  ".join(f"{g}={c}" for g, c in zip(UTM_FUNNEL, cells)))
    if entry_totals:
        print("  по странице входа (визиты → товар → корзина → оформление → оплата):")
        for group in ("home", "catalog", "article", "other"):
            bucket = entry_totals.get(group)
            if not bucket:
                continue
            cells = []
            for name in FUNNEL_BY_LANDING:
                value = bucket.get(name)
                cells.append("н/д" if value is None else f"{value:g}")
            print(f"    {group:8s} визитов {bucket['visits']:6g}  "
                  + "  ".join(f"{n}={c}" for n, c in zip(FUNNEL_BY_LANDING, cells)))

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUT_DIR / f"site-{date.today().isoformat()}.yaml"
        header = (
            "# Снимок чисел сайта из Яндекс.Метрики. Пишется прогоном\n"
            "# .github/workflows/metrika.yml, инструмент — tools/metrika_report.py.\n"
            "#\n"
            "# Ряд читается сравнением файлов между собой: один снимок не отвечает\n"
            "# ни на один вопрос плана развития, два отвечают.\n"
            "#\n"
            "# Каталог content/ не деплоится: числа остаются внутренними.\n"
        )
        target.write_text(header + yaml_dump(snapshot) + "\n", encoding="utf-8")
        print(f"\nСнимок записан: {target.relative_to(ROOT)}")
    else:
        print("\nЭто показ. Записать снимок: --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
