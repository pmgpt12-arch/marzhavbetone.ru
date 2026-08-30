#!/usr/bin/env python3
"""Дымовой прогон боевого сайта: то, чего не видно из репозитория.

Появился 15.08.2026. Причина названа замером, а не соображением: аудит
после выкладки не смог проверить ни одного пользовательского маршрута,
потому что из облачной сессии боевой сайт закрыт егресс-политикой —
`curl https://marzhavbetone.ru/` отвечает `CONNECT tunnel failed, 403`,
`WebFetch` — `EGRESS_BLOCKED`. У раннера GitHub Actions егресс есть,
поэтому проверка живёт там.

Что именно нельзя узнать чтением репозитория и можно — этим прогоном:

  · выложилось ли вообще то, что слито в main;
  · отвечает ли страница кодом 200, а не 404, 403 или 500;
  · совпадает ли canonical на живой странице с её адресом;
  · не закрыта ли страница от индексации `noindex` — ни в мете, ни
    заголовком `X-Robots-Tag`, который в файлах вообще не виден;
  · одинаково ли сайт отвечает браузеру и роботам. Исключение —
    подтверждённые роботы: подставленный User-Agent не подтверждает IP
    раннера, поэтому отказ Cloudflare такой имитации не доказывает, что
    закрыт настоящий робот. Это ограничение прогон обязан назвать.

Проверка намеренно не лезет в корзину и оплату: там нужен настоящий
платёж, и его цена — деньги, а не время.

    python3 tools/smoke_production.py                 # боевой адрес
    python3 tools/smoke_production.py --base URL      # другой адрес
    python3 tools/smoke_production.py --sample 3      # сколько брать из раздела
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = "https://marzhavbetone.ru"
# Хост, который обязан стоять в canonical, независимо от того, по
# какому адресу прогон стучится. Пустая строка снимает проверку.
CANONICAL_HOST = "marzhavbetone.ru"
TIMEOUT = 25

# Агенты. Браузер — эталон; остальные три обязаны получить то же самое.
# OAI-SearchBot добавлен не для полноты: ответы ИИ-поиска уже стали входом,
# и закрыться от него можно, не заметив.
AGENTS = {
    "browser": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Googlebot": ("Mozilla/5.0 (compatible; Googlebot/2.1; "
                  "+http://www.google.com/bot.html)"),
    "YandexBot": ("Mozilla/5.0 (compatible; YandexBot/3.0; "
                  "+http://yandex.com/bots)"),
    "OAI-SearchBot": ("Mozilla/5.0 (compatible; OAI-SearchBot/1.0; "
                      "+https://openai.com/searchbot)"),
}

FIXED = ["/", "/robots.txt", "/sitemap.xml", "/articles/", "/materialy/",
         "/kalkulyator.html", "/diagnostika.html", "/katalog.html"]


def fetch(url: str, agent: str) -> tuple[int, dict, str]:
    request = urllib.request.Request(url, headers={"User-Agent": agent})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(400_000).decode("utf-8", "replace")
            return response.status, dict(response.headers), body
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), ""
    except Exception as exc:  # сеть, TLS, таймаут
        return 0, {"_error": str(exc)}, ""


def unverified_cloudflare_bot_probe(name: str, status: int,
                                    headers: dict) -> bool:
    """Cloudflare отверг имитацию подтверждённого OAI-SearchBot.

    Раннер управляет только User-Agent, но не исходным IP. Поэтому такой
    ответ не подтверждает ни доступ, ни блокировку настоящего робота.
    Исключение намеренно узкое: один агент, 403, Server и непустой CF-Ray.
    """
    нормализованные = {
        str(key).lower(): str(value).strip()
        for key, value in headers.items()
    }
    return (
        name == "OAI-SearchBot"
        and status == 403
        and нормализованные.get("server", "").lower() == "cloudflare"
        and bool(нормализованные.get("cf-ray"))
    )


def sample_urls(count: int) -> list[str]:
    """Адреса берутся из репозитория: проверять надо то, что выложено."""
    out = []
    for folder, prefix in (("articles", "/articles/"), ("products", "/products/"),
                           ("materialy", "/materialy/")):
        files = sorted(p.name for p in (ROOT / folder).glob("*.html")
                       if p.name != "index.html")
        out += [prefix + name for name in files[:count]]
    return out


def check(base: str, path: str, results: list[str],
          observations: set[str] | None = None) -> None:
    url = base.rstrip("/") + path
    status, headers, body = fetch(url, AGENTS["browser"])

    if status != 200:
        detail = headers.get("_error", "")
        results.append(f"{path}: код {status} вместо 200 {detail}".strip())
        return

    xrobots = headers.get("X-Robots-Tag", "")
    if "noindex" in xrobots.lower():
        results.append(f"{path}: заголовок X-Robots-Tag закрывает от индексации — {xrobots}")

    if path.endswith(".xml") or path.endswith(".txt"):
        return

    meta = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', body, re.I)
    if meta and "noindex" in meta.group(1).lower():
        results.append(f"{path}: мета robots закрывает от индексации — {meta.group(1)}")

    canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', body, re.I)
    if not canonical:
        results.append(f"{path}: нет canonical")
    else:
        # Путь и хост сверяются порознь. Иначе прогон против тестового
        # адреса ругался бы на каждый canonical только потому, что в нём
        # стоит боевой домен, — и настоящий дефект утонул бы в этом шуме.
        got = urllib.parse.urlsplit(canonical.group(1))
        want_path = urllib.parse.urlsplit(url).path
        if got.path.rstrip("/") != want_path.rstrip("/"):
            results.append(f"{path}: canonical указывает на путь {got.path}, "
                           f"а страница отдана по {want_path}")
        if CANONICAL_HOST and got.netloc and got.netloc != CANONICAL_HOST:
            results.append(f"{path}: canonical ведёт на чужой хост {got.netloc}, "
                           f"ожидался {CANONICAL_HOST}")

    if not re.search(r"<title[^>]*>\s*\S", body, re.I):
        results.append(f"{path}: пустой или отсутствующий title")
    if not re.search(r"<h1[^>]*>\s*\S", body, re.I):
        results.append(f"{path}: нет H1")

    # Ответ роботам сверяется с ответом браузеру. Сравнивается не байт в
    # байт — на странице есть меняющееся, — а код ответа и длина с допуском.
    for name, agent in AGENTS.items():
        if name == "browser":
            continue
        bot_status, bot_headers, bot_body = fetch(url, agent)
        if bot_status != status:
            if unverified_cloudflare_bot_probe(name, bot_status, bot_headers):
                if observations is not None:
                    observations.add(
                        "Cloudflare отверг имитацию OAI-SearchBot от IP "
                        "раннера (403 + CF-Ray). Доступ настоящего "
                        "подтверждённого робота этим прогоном не измеряется."
                    )
                continue
            results.append(f"{path}: {name} получает код {bot_status}, "
                           f"браузер — {status}")
            continue
        if "noindex" in bot_headers.get("X-Robots-Tag", "").lower():
            results.append(f"{path}: {name} получает X-Robots-Tag noindex, браузер — нет")
        if body and bot_body:
            ratio = len(bot_body) / max(len(body), 1)
            if ratio < 0.8 or ratio > 1.25:
                results.append(f"{path}: {name} получает страницу другого размера "
                               f"({len(bot_body)} против {len(body)}) — похоже на клоакинг")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--sample", type=int, default=3,
                        help="сколько адресов брать из каждого раздела")
    args = parser.parse_args()

    paths = FIXED + sample_urls(args.sample)
    results: list[str] = []
    observations: set[str] = set()
    for path in paths:
        check(args.base, path, results, observations)

    print(f"Дымовой прогон {args.base}: проверено адресов {len(paths)}, "
          f"агентов {len(AGENTS)}")
    for observation in sorted(observations):
        print(f"ОГРАНИЧЕНИЕ: {observation}")
    if results:
        print(f"РАСХОЖДЕНИЙ: {len(results)}")
        for line in results:
            print(f"   ✗ {line}")
        return 1
    print("Расхождений нет: все адреса отвечают 200, canonical на месте, "
          "роботы получают то же, что браузер.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
