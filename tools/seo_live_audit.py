#!/usr/bin/env python3
"""Живой аудит индексируемости: что боевой сайт отдаёт роботам на самом деле.

Слой, которого не закрывает ни одна проверка по файлам: check_seo.py сверяет
репозиторий с самим собой, а робот ходит по https://marzhavbetone.ru/ — и
между этими двумя состояниями лежат сервер, кеш, WAF и редиректы. Из
облачной сессии сайт закрыт политикой сети (CONNECT 403, факт net.site),
поэтому прогон живёт в .github/workflows/seo-audit.yml и ходит с раннера.

Что меряется:

  1. robots.txt — код, строка Sitemap, не закрыт ли корень.
  2. sitemap.xml — код, разбор, каждый URL из карты: код ответа, редиректы,
     финальный адрес.
  3. Каждый 200-адрес: canonical в отданном HTML (self или чужой),
     meta robots, заголовок X-Robots-Tag, наличие <title> и <h1>.
  4. Дубли схемы: http://, www., хвост «/» на выборке — куда ведут.
  5. Роботы: ключевые страницы под User-Agent браузера, YandexBot,
     Googlebot и OAI-SearchBot — не отдаёт ли сервер им разное
     (403, challenge, другой код).

Выход — markdown-отчёт с таблицей URL → код → индексируемость → причина и
итоговыми уровнями. Код возврата 1 при находках уровня КРИТИЧНО.

    python3 tools/seo_live_audit.py --out content/metrics/seo-live-audit.md

Замер, а не суждение: «страница в индексе Яндекса или нет» этот прогон не
показывает — это данные Вебмастера. Он показывает предыдущий этаж: может ли
робот вообще получить то, что мы опубликовали.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

SITE = "https://marzhavbetone.ru"

UA = {
    "browser": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "YandexBot": "Mozilla/5.0 (compatible; YandexBot/3.0; "
                 "+http://yandex.com/bots)",
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                 "+http://www.google.com/bot.html)",
    "OAI-SearchBot": "OAI-SearchBot/1.0; +https://openai.com/searchbot",
}

CANONICAL = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
META_ROBOTS = re.compile(
    r'<meta\s+name="robots"\s+content="([^"]+)"', re.I)
TITLE = re.compile(r"<title>", re.I)
H1 = re.compile(r"<h1[\s>]", re.I)


def fetch(url: str, ua: str = UA["browser"], follow: bool = True):
    """(код, финальный URL, заголовки, тело|None, ошибка|None)."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = (urllib.request.build_opener() if follow
              else urllib.request.build_opener(NoRedirect))
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with opener.open(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, resp.url, dict(resp.headers), body, None
    except urllib.error.HTTPError as e:
        return e.code, url, dict(e.headers or {}), None, None
    except Exception as e:  # сеть, TLS, таймаут
        return None, url, {}, None, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0,
                        help="ограничить число URL из карты (0 — все)")
    args = parser.parse_args()

    critical: list[str] = []
    high: list[str] = []
    medium: list[str] = []
    lines: list[str] = [
        "# Живой аудит индексируемости marzhavbetone.ru",
        f"\nДата: {date.today().isoformat()}. Прогон: seo-audit.yml, "
        "раннер GitHub Actions.",
        "\nКаждая строка — наблюдение команды, а не вывод. Что этот прогон "
        "не показывает: состав индекса — это Вебмастер/Search Console.",
    ]

    # --- 1. robots.txt ----------------------------------------------------
    code, _, _, body, err = fetch(f"{SITE}/robots.txt")
    robots_txt = (body or b"").decode("utf-8", "replace")
    lines.append("\n## robots.txt\n")
    if err or code != 200:
        critical.append(f"robots.txt: код {code}, ошибка {err}")
        lines.append(f"- КРИТИЧНО: код {code}, ошибка {err}")
    else:
        lines.append(f"- код 200, {len(robots_txt)} байт")
        if "Sitemap:" not in robots_txt:
            high.append("robots.txt без строки Sitemap")
        if re.search(r"^Disallow:\s*/\s*$", robots_txt, re.M):
            critical.append("robots.txt закрывает корень: Disallow: /")
        for line in robots_txt.splitlines():
            lines.append(f"      {line}")

    # --- 2. sitemap.xml и все его URL -------------------------------------
    code, _, _, body, err = fetch(f"{SITE}/sitemap.xml")
    lines.append("\n## sitemap.xml\n")
    urls: list[str] = []
    if err or code != 200:
        critical.append(f"sitemap.xml: код {code}, ошибка {err}")
        lines.append(f"- КРИТИЧНО: код {code}, ошибка {err}")
    else:
        urls = re.findall(r"<loc>(.*?)</loc>",
                          body.decode("utf-8", "replace"))
        lines.append(f"- код 200, адресов: {len(urls)}")
        if args.limit:
            urls = urls[: args.limit]

    lines.append("\n## Адреса карты сайта\n")
    lines.append("| URL | код | canonical | meta robots | X-Robots | "
                 "title | h1 | итог |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for url in urls:
        code, final, headers, body, err = fetch(url)
        path = url.replace(SITE, "") or "/"
        if err or code is None:
            critical.append(f"{path}: не отвечает ({err})")
            lines.append(f"| {path} | — | | | | | | КРИТИЧНО: {err} |")
            continue
        if code != 200:
            critical.append(f"{path}: код {code} в карте сайта")
            lines.append(f"| {path} | {code} | | | | | | КРИТИЧНО |")
            continue
        if final.rstrip("/") != url.rstrip("/"):
            high.append(f"{path}: редирект из карты на {final}")
        html = body.decode("utf-8", "replace")
        can = CANONICAL.search(html)
        can_val = (can.group(1).replace(SITE, "") or "/") if can else "нет"
        can_ok = can_val == path or (path == "/" and can_val == "/")
        meta = META_ROBOTS.search(html)
        meta_val = meta.group(1) if meta else "—"
        xrobots = headers.get("X-Robots-Tag", "—")
        has_title = bool(TITLE.search(html))
        has_h1 = bool(H1.search(html))
        verdict = "ок"
        if meta and "noindex" in meta_val.lower():
            critical.append(f"{path}: meta robots noindex при наличии в карте")
            verdict = "КРИТИЧНО: noindex"
        elif "noindex" in str(xrobots).lower():
            critical.append(f"{path}: X-Robots-Tag noindex")
            verdict = "КРИТИЧНО: X-Robots noindex"
        elif not can_ok:
            high.append(f"{path}: canonical ведёт на {can_val}")
            verdict = f"ВЫСОКО: canonical {can_val}"
        elif not has_title or not has_h1:
            medium.append(f"{path}: title={has_title}, h1={has_h1}")
            verdict = "СРЕДНЕ: нет title/h1"
        lines.append(
            f"| {path} | {code} | {can_val} | {meta_val} | {xrobots} | "
            f"{'да' if has_title else 'НЕТ'} | {'да' if has_h1 else 'НЕТ'} | "
            f"{verdict} |")

    # --- 3. Дубли схемы ---------------------------------------------------
    lines.append("\n## Дубли схемы и хвосты\n")
    for probe, want in [
        ("http://marzhavbetone.ru/", f"{SITE}/"),
        ("https://www.marzhavbetone.ru/", f"{SITE}/"),
    ]:
        code, _, headers, _, err = fetch(probe, follow=False)
        loc = headers.get("Location", "")
        ok = code in (301, 308) and loc.rstrip("/") == want.rstrip("/")
        lines.append(f"- {probe} → {code} {loc}"
                     + ("" if ok else "  ← ВЫСОКО: ожидался 301 на " + want))
        if not ok:
            high.append(f"{probe}: {code} {loc}, ожидался 301 → {want}")
    # хвост «/» на выборке файловых адресов
    sample = [u for u in urls if u.endswith(".html")][:3]
    for u in sample:
        code, _, headers, _, _ = fetch(u + "/", follow=False)
        lines.append(f"- {u.replace(SITE,'')}/ → {code} "
                     f"{headers.get('Location','')}")
        if code == 200:
            medium.append(f"{u.replace(SITE,'')}/: хвост «/» отдаёт 200 — "
                          "дубль без склейки")

    # --- 4. Роботы --------------------------------------------------------
    lines.append("\n## Ответ по User-Agent (ключевые страницы)\n")
    lines.append("| страница | " + " | ".join(UA) + " |")
    lines.append("|---|" + "---|" * len(UA))
    key_pages = ["/", "/robots.txt", "/sitemap.xml"] + \
        [u.replace(SITE, "") for u in urls[:4] if u != f"{SITE}/"]
    for page in key_pages[:7]:
        row = [page]
        for name, ua in UA.items():
            code, _, _, _, err = fetch(f"{SITE}{page}", ua=ua)
            row.append(str(code) if code else f"ошибка")
            if code not in (200,):
                critical.append(f"{page}: {name} получает {code or err}")
        lines.append("| " + " | ".join(row) + " |")

    # --- Итог -------------------------------------------------------------
    lines.append("\n## Итог\n")
    for level, items in (("КРИТИЧНО", critical), ("ВЫСОКО", high),
                         ("СРЕДНЕ", medium)):
        lines.append(f"\n### {level} — {len(items)}\n")
        lines.extend(f"- {i}" for i in items) if items else \
            lines.append("- не найдено")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Отчёт: {args.out}")
    print(f"КРИТИЧНО {len(critical)}, ВЫСОКО {len(high)}, "
          f"СРЕДНЕ {len(medium)}")
    return 1 if critical else 0


if __name__ == "__main__":
    sys.exit(main())
