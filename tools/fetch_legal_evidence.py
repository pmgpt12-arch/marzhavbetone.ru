#!/usr/bin/env python3
"""Добыть offline-доказательства норм с машины, у которой есть сеть.

В CI не запускается и запускаться не должен: гейт объявлен набором без
сети, а этот инструмент без сети бесполезен. CI только читает уже
сохранённое.

Зачем инструмент вообще нужен. Из рабочей среды официальные публикаторы
закрыты политикой сети — замер 15.08.2026: `pravo.gov.ru` и
`publication.pravo.gov.ru` отвечают 403 на CONNECT, `consultant.ru` и
`base.garant.ru` не резолвятся вовсе. Значит доказательства должен
получить тот, у кого доступ есть, одной командой и на все нормы разом, а
не открывая семнадцать статей руками.

Главное правило, ради которого инструмент написан именно так: **при
недоступности официального источника он не подставляет вторичный**. Норма
получает `not_verified`, гейт остаётся красным, и это верный исход.
Вторичный источник можно записать только явным `--allow-secondary`, и
класс у такой записи будет `secondary` — полного PASS она всё равно не
даёт.

    python3 tools/fetch_legal_evidence.py --all
    python3 tools/fetch_legal_evidence.py --norm gk-395 --show
    python3 tools/fetch_legal_evidence.py --all --allow-secondary

Ограничение названо прямо: сетевой путь из этой среды проверить нечем —
он закрыт. Отказной путь проверен (`--all` здесь даёт семнадцать
`not_verified`), сетевой ждёт первого прогона на машине с доступом.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_evidence import (  # noqa: E402
    NOT_VERIFIED, OFFICIAL, SECONDARY, normalize, write)

ROOT = Path(__file__).resolve().parent.parent
NORMS = ROOT / "data" / "legal" / "norms.yaml"
UA = "marzhavbetone-legal-evidence/1.0 (+normative gate bootstrap)"
TIMEOUT = 30


class Unreachable(RuntimeError):
    """Источник не ответил. Причина называется кодом, а не словом «не смог»."""


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as e:
        raise Unreachable(f"код {e.code}") from e
    except Exception as e:
        raise Unreachable(f"{type(e).__name__}: {e}") from e
    return raw.decode(charset, "replace")


def strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    for entity, char in (("&nbsp;", " "), ("&laquo;", "«"), ("&raquo;", "»"),
                         ("&mdash;", "—"), ("&ndash;", "–"), ("&amp;", "&")):
        html = html.replace(entity, char)
    return normalize(html)


def extract_article(text: str, article: str) -> str:
    """Вырезать названную статью из полного текста акта.

    Границей служит заголовок следующей статьи. Если границу найти не
    удалось, возвращается пусто: отдать вместо статьи весь кодекс значило
    бы захешировать не то, что проверяли.
    """
    number = article.strip().split()[-1].rstrip(".")
    start = re.search(rf"Стать[яи]\s+{re.escape(number)}\s*[.．]", text)
    if not start:
        return ""
    tail = text[start.start():]
    nxt = re.search(r"Стать[яи]\s+[\d.]+\s*[.．]", tail[10:])
    return tail[: nxt.start() + 10] if nxt else tail[:20000]


def collect(norm: dict, allow_secondary: bool) -> tuple[str, str, str, str]:
    """(текст, класс, использованный адрес, примечание)."""
    official = norm.get("official_source") or ""
    if official:
        try:
            body = extract_article(strip_html(fetch(official)),
                                   str(norm.get("article", "")))
            if body:
                return body, OFFICIAL, official, ""
            note = "официальный источник ответил, но статья в нём не найдена"
        except Unreachable as e:
            note = f"официальный источник недоступен: {e}"
    else:
        note = "официальный адрес в реестре не назван"

    if not allow_secondary:
        return "", NOT_VERIFIED, official, note

    for url in norm.get("fallback_sources", []) or []:
        try:
            body = extract_article(strip_html(fetch(url)),
                                   str(norm.get("article", "")))
            if body:
                return body, SECONDARY, url, note + "; взят вторичный источник"
        except Unreachable:
            continue
    return "", NOT_VERIFIED, official, note + "; вторичные тоже не ответили"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="все нормы реестра")
    ap.add_argument("--norm", help="одна норма по norm_id")
    ap.add_argument("--allow-secondary", action="store_true",
                    help="записать вторичный источник, если официальный молчит "
                         "(класс будет secondary, полного PASS он не даёт)")
    ap.add_argument("--show", action="store_true", help="показать, не записывая")
    args = ap.parse_args()

    if not (args.all or args.norm):
        ap.error("нужен --all или --norm")

    norms = yaml.safe_load(NORMS.read_text(encoding="utf-8")).get("norms", [])
    if args.norm:
        norms = [n for n in norms if n["norm_id"] == args.norm]
        if not norms:
            print(f"нормы {args.norm} в реестре нет")
            return 1

    today = date.today().isoformat()
    tally = {OFFICIAL: 0, SECONDARY: 0, NOT_VERIFIED: 0}
    for norm in norms:
        norm_id = norm["norm_id"]
        text, klass, url, note = collect(norm, args.allow_secondary)
        tally[klass] += 1
        mark = {OFFICIAL: "✓", SECONDARY: "~", NOT_VERIFIED: "✗"}[klass]
        print(f"  {mark} {norm_id:14} {klass:12} {note or url}")
        if args.show or not text:
            continue
        write(norm_id, official_url=url,
              edition_marker=norm.get("edition_marker", ""), text=text,
              source_class=klass, retrieved_at=today,
              retrieved_by="tools/fetch_legal_evidence.py", note=note)

    print(f"\nofficial {tally[OFFICIAL]}, secondary {tally[SECONDARY]}, "
          f"not_verified {tally[NOT_VERIFIED]} — всего {len(norms)}.")
    if tally[NOT_VERIFIED]:
        print("\nНедоступный источник доказательством не заменяется: норма "
              "остаётся not_verified,\nи гейт по ней красный. Это верный "
              "исход, а не поломка инструмента.")
    return 0 if tally[OFFICIAL] == len(norms) else 1


if __name__ == "__main__":
    sys.exit(main())
