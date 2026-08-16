#!/usr/bin/env python3
"""Добыть offline-доказательства норм с машины, у которой есть сеть.

В CI не запускается и запускаться не должен: гейт объявлен набором без
сети, а этот инструмент без сети бесполезен. CI только читает уже
сохранённое.

Главное правило, ради которого инструмент написан именно так: **при
недоступности официального источника он не подставляет вторичный**. Норма
получает `not_verified`, гейт остаётся красным, и это верный исход.
Вторичный источник можно записать только явным `--allow-secondary`, и
класс у такой записи будет `secondary` — полного PASS она всё равно не
даёт. Таймаут вторичным источником тоже не заменяется: не ответивший
официальный публикатор это «неизвестно», а не «можно взять другой».

    python tools/fetch_legal_evidence.py --all
    python tools/fetch_legal_evidence.py --all --capture data/legal/fixtures
    python tools/fetch_legal_evidence.py --norm gk-395 --debug
    python tools/fetch_legal_evidence.py --all --allow-secondary

Что изменилось после прогона владельца 16.08.2026. Прогон дал `official 0,
secondary 0, not_verified 17`, и по большинству норм — «источник ответил,
но статья в нём не найдена». То есть сеть работает, а разбор нет, и по
выводу нельзя было понять, чем именно ответил публикатор. Отсюда две
вещи: разбор вынесен в `legal_extract.py` и накрыт тестами без сети, а
здесь появился `--debug` и `--capture`, которые показывают и сохраняют
фактический ответ. Инструмент, который не умеет объяснить свой отказ,
чинится вслепую.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_evidence import (  # noqa: E402
    NOT_VERIFIED, OFFICIAL, SECONDARY, write)
from legal_extract import (  # noqa: E402
    extract, page_title, parse_units, strip_html)

ROOT = Path(__file__).resolve().parent.parent
NORMS = ROOT / "data" / "legal" / "norms.yaml"
UA = "marzhavbetone-legal-evidence/1.1 (+normative gate bootstrap)"

# Таймаут и повторы. Замер владельца 16.08.2026: `nk-333-40` и `nk-333-21`
# упали в TimeoutError при тридцати секундах — обе на одном хосте. Тридцать
# секунд не «мало вообще», а мало для этого хоста; повтор с паузой дешевле
# ручного перезапуска. Исчерпание повторов даёт NOT_VERIFIED с числом
# попыток в причине, а не молчаливый пропуск.
TIMEOUT = 45
RETRIES = 3
BACKOFF = (2, 5)


class Unreachable(RuntimeError):
    """Источник не ответил. Причина называется кодом, а не словом «не смог»."""


def fetch(url: str) -> dict:
    """Ответ вместе с обстоятельствами: они нужны и для разбора, и для отказа."""
    last = ""
    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "text/html,*/*",
                          "Accept-Language": "ru,en;q=0.5"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                return {
                    "status": resp.status,
                    "final_url": resp.geturl(),
                    "content_type": resp.headers.get("Content-Type", ""),
                    "length": len(raw),
                    "body": raw.decode(
                        resp.headers.get_content_charset() or "utf-8", "replace"),
                    "attempts": attempt,
                }
        except urllib.error.HTTPError as e:
            raise Unreachable(f"код {e.code}") from e
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < RETRIES:
                time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
    raise Unreachable(f"{last} — попыток {RETRIES}")


def probe(norm: dict, url: str) -> dict:
    """Один адрес: что пришло и что из этого разобралось. Ничего не пишет."""
    kind, units, subs = parse_units(norm.get("article", ""), norm.get("act", ""))
    card = {"url": url, "strategy": kind, "wanted": units, "subdivisions": subs}
    try:
        resp = fetch(url)
    except Unreachable as e:
        return {**card, "ok": False, "reason": f"источник недоступен: {e}"}

    body = strip_html(resp["body"])
    res = extract(body, norm)
    return {**card,
            "status": resp["status"], "final_url": resp["final_url"],
            "content_type": resp["content_type"], "length": resp["length"],
            "attempts": resp["attempts"], "title": page_title(resp["body"]),
            "text_length": len(body), "excerpt": body[:1200],
            "found": res.found, "missing": res.missing,
            "ok": res.ok, "reason": res.reason, "text": res.text}


def show_debug(norm: dict, card: dict) -> None:
    print(f"\n=== {norm['norm_id']} — {norm.get('act','')} {norm.get('article','')}")
    for key in ("url", "status", "final_url", "content_type", "length",
                "attempts", "title", "text_length", "strategy", "wanted",
                "subdivisions", "found", "missing"):
        if key in card:
            print(f"  {key:14} {card[key]}")
    print(f"  {'извлечено':14} {'да' if card.get('ok') else 'нет'}")
    if card.get("reason"):
        print(f"  {'причина':14} {card['reason']}")
    if card.get("excerpt"):
        print(f"  {'начало ответа':14} {card['excerpt'][:400]}")


def capture(card: dict, norm_id: str, out: Path) -> Path:
    """Диагностический слепок для сборки фикстуры. Без cookies и заголовков.

    Сохраняется то, чем чинится разбор: обстоятельства ответа и текст
    вокруг искомых маркеров. Целиком страница не пишется намеренно —
    чужой документ на мегабайты в репозитории не нужен, а для правки
    регулярного выражения хватает окрестности маркера.
    """
    out.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in card.items() if k not in ("text",)}
    payload["excerpt"] = card.get("excerpt", "")[:4000]
    path = out / f"{norm_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


def collect(norm: dict, allow_secondary: bool,
            out: Path | None) -> tuple[str, str, str, str]:
    """(текст, класс, использованный адрес, примечание)."""
    official = norm.get("official_source") or ""
    note = "официальный адрес в реестре не назван"
    if official:
        card = probe(norm, official)
        if out:
            capture(card, norm["norm_id"], out)
        if card["ok"]:
            return card["text"], OFFICIAL, official, _subdivision_note(norm)
        note = f"официальный источник: {card['reason']}"

    if not allow_secondary:
        return "", NOT_VERIFIED, official, note

    for url in norm.get("fallback_sources") or []:
        card = probe(norm, url)
        if card["ok"]:
            return (card["text"], SECONDARY, url,
                    f"{note}; взят вторичный источник")
    return "", NOT_VERIFIED, official, f"{note}; вторичные тоже не дали текста"


def _subdivision_note(norm: dict) -> str:
    _, _, subs = parse_units(norm.get("article", ""), norm.get("act", ""))
    if not subs:
        return ""
    return (f"сохранена статья целиком; документ опирается на подраздел "
            f"{', '.join(subs)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="все нормы реестра")
    ap.add_argument("--norm", help="одна норма по norm_id")
    ap.add_argument("--allow-secondary", action="store_true",
                    help="записать вторичный источник, если официальный молчит "
                         "(класс будет secondary, полного PASS он не даёт)")
    ap.add_argument("--show", action="store_true", help="показать, не записывая")
    ap.add_argument("--debug", action="store_true",
                    help="показать фактический ответ и разбор, ничего не писать")
    ap.add_argument("--capture", metavar="КАТАЛОГ",
                    help="сохранить диагностические слепки для сборки фикстур")
    args = ap.parse_args()

    if not (args.all or args.norm):
        ap.error("нужен --all или --norm")

    norms = yaml.safe_load(NORMS.read_text(encoding="utf-8")).get("norms", [])
    if args.norm:
        norms = [n for n in norms if n["norm_id"] == args.norm]
        if not norms:
            print(f"нормы {args.norm} в реестре нет")
            return 1

    out = Path(args.capture) if args.capture else None

    if args.debug:
        for norm in norms:
            card = probe(norm, norm.get("official_source") or "")
            show_debug(norm, card)
            if out:
                capture(card, norm["norm_id"], out)
        if out:
            print(f"\nСлепки сохранены: {out}")
        return 0

    today = date.today().isoformat()
    tally = {OFFICIAL: 0, SECONDARY: 0, NOT_VERIFIED: 0}
    for norm in norms:
        norm_id = norm["norm_id"]
        text, klass, url, note = collect(norm, args.allow_secondary, out)
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
    if out:
        print(f"Диагностические слепки: {out}")
    if tally[NOT_VERIFIED]:
        print("\nНедоступный источник доказательством не заменяется: норма "
              "остаётся not_verified,\nи гейт по ней красный. Это верный "
              "исход, а не поломка инструмента.\nЧем именно ответил "
              "публикатор — покажет --debug по одной норме.")
    return 0 if tally[OFFICIAL] == len(norms) else 1


if __name__ == "__main__":
    sys.exit(main())
