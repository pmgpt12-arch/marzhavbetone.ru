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

Корневая причина семнадцати отказов названа слепками владельца от
16.08.2026, и она оказалась не в адресах и не в регулярках.
`pravo.gov.ru` отдаёт `Content-Type: text/html` **без charset**, страницы
в windows-1251, а код брал utf-8 с `errors="replace"` — вся кириллица
превращалась в U+FFFD. Соответствие в слепках точное, один байт на один
знак замены. Слова «Статья» в таком тексте нет, и найти его было нельзя
ничем. Шестнадцать слепков из семнадцати — ровно этот случай.

Семнадцатый другой: `vsrf.ru/documents/own/` отвечает целой кириллицей,
но это перечень документов, а не текст постановления. Три слепка АПК —
27 740 байт при 598 знаках текста, то есть навигация. На такие ответы
инструмент теперь идёт по ссылке самой страницы, совпавшей с реквизитами
акта из реестра: адрес берётся из ответа официального источника, а не
угадывается.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_evidence import (  # noqa: E402
    NOT_VERIFIED, OFFICIAL, SECONDARY, write)
from legal_extract import (  # noqa: E402
    decode_body, extract, find_document_links, identifies_act,
    ips_document_url, ips_print_url, looks_damaged, looks_truncated,
    page_title, parse_units, strip_html)

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


# Пауза между обращениями к одному хосту. Причина замером 16.08.2026: в
# прогоне владельца оболочка НК на втором обращении вернула 4 559 байт
# вместо 106 070 — портал отвечает короткой страницей под частым запросом.
# Тот же прогон дёргал один и тот же документ по разу на норму: фрейм ГК
# части первой качался шесть раз по полмегабайта. Ниже и пауза, и память.
POLITE_PAUSE = 1.5

# Ответы за прогон: один адрес — одно обращение. Семнадцать норм стоят на
# шести актах, и без этого каждая тянет чужой мегабайт заново.
_CACHE: dict[str, dict] = {}
_LAST_CALL = [0.0]

# Куда складывать все ответы прогона. Ставится один раз в main.
_SINK: list = [None]


class Unreachable(RuntimeError):
    """Источник не ответил. Причина называется кодом, а не словом «не смог»."""


def _store(url: str, resp: dict) -> None:
    """Сохранить фактический ответ. Имя — по содержимому, а не по адресу.

    Первый захват именовал файл хешем адреса и не перезаписывал уже
    существующий. Замер 16.08.2026 показал, чем это плохо: у `nk-333-40` в
    слепке записано 4 559 байт, а на диске лежал файл на 106 070 от
    прошлого обращения к тому же адресу. Слепок и байты разошлись, и
    разобрать по ним отказ было нельзя.

    Второй дефект того же ряда: сохранялся только последний ответ нормы.
    Ответы фрейма — то единственное, что объясняет двенадцать отказов, — не
    сохранялись вовсе. Теперь пишется каждый.
    """
    sink = _SINK[0]
    if sink is None:
        return
    pages = sink / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(resp["raw"]).hexdigest()[:16]
    path = pages / f"{digest}.html"
    if not path.exists():
        path.write_bytes(resp["raw"])
    index = sink / "responses.json"
    log = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    log.append({"url": url, "final_url": resp["final_url"],
                "status": resp["status"], "length": resp["length"],
                "charset": resp["charset"], "damaged": resp["damaged"],
                "page_file": f"pages/{path.name}"})
    index.write_text(json.dumps(log, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def fetch(url: str) -> dict:
    """Ответ вместе с обстоятельствами: они нужны и для разбора, и для отказа."""
    if url in _CACHE:
        return _CACHE[url]
    pause = POLITE_PAUSE - (time.monotonic() - _LAST_CALL[0])
    if _LAST_CALL[0] and pause > 0:
        time.sleep(pause)
    _LAST_CALL[0] = time.monotonic()
    last = ""
    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "text/html,*/*",
                          "Accept-Language": "ru,en;q=0.5"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                body, codec = decode_body(
                    raw, resp.headers.get_content_charset() or "")
                if looks_truncated(body) and attempt < RETRIES:
                    # Код 200, но ответ оборван на полуслове. Замер
                    # 16.08.2026: оболочка ГК части первой пришла на 4 561
                    # байт вместо 56 248, без `</html>`, и фрейма с текстом
                    # в обрезке уже не было. Это повод повторить запрос, а
                    # не докладывать «пути к тексту нет».
                    last = "ответ оборван (нет закрывающего тега)"
                    time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
                    continue
                out = {
                    "status": resp.status,
                    "final_url": resp.geturl(),
                    "content_type": resp.headers.get("Content-Type", ""),
                    "length": len(raw),
                    "charset": codec,
                    "damaged": looks_damaged(body),
                    "raw": raw,
                    "body": body,
                    "attempts": attempt,
                }
                _CACHE[url] = out
                _store(url, out)
                return out
        except urllib.error.HTTPError as e:
            raise Unreachable(f"код {e.code}") from e
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < RETRIES:
                time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
    raise Unreachable(f"{last} — попыток {RETRIES}")


def probe(norm: dict, url: str, follow: bool = True) -> dict:
    """Один адрес: что пришло и что из этого разобралось. Ничего не пишет.

    Не нашлось на объявленном адресе — ссылки фактического ответа
    просматриваются на совпадение с реквизитами акта, и найденное
    проходится один уровень вглубь. Владелец при этом статей руками не
    открывает, а адрес не угадывается: он взят из ответа официального
    источника.
    """
    kind, units, subs = parse_units(norm.get("article", ""), norm.get("act", ""))
    card = {"url": url, "strategy": kind, "wanted": units, "subdivisions": subs}
    try:
        resp = fetch(url)
    except Unreachable as e:
        return {**card, "ok": False, "reason": f"источник недоступен: {e}"}

    body = strip_html(resp["body"])
    if not identifies_act(resp["body"], body, norm.get("document_match") or []):
        # Адрес в реестре ведёт не на тот акт, и починить его нечем: в
        # оболочке ИПС ссылок всего шесть — стили, помощь, выгрузка в RTF и
        # корень портала. Поиска по документам среди них нет. Корень
        # снимается в захват, чтобы у следующего разбора был материал:
        # угадывать идентификатор документа нельзя, а искать его надо где-то.
        if "pravo.gov.ru" in url and _SINK[0] is not None:
            try:
                fetch(urljoin(resp["final_url"], "/"))
            except Unreachable:
                pass
        return {**card, "ok": False, "status": resp["status"],
                "final_url": resp["final_url"], "length": resp["length"],
                "title": page_title(resp["body"]), "excerpt": body[:1200],
                "raw": resp["raw"], "followed": [],
                "reason": ("по адресу лежит другой документ — «"
                           + (page_title(resp["body"]) or body[:70]).strip()
                           + "»; адрес в реестре указывает не на тот акт")}
    res = extract(body, norm)
    card = {**card,
            "status": resp["status"], "final_url": resp["final_url"],
            "content_type": resp["content_type"], "length": resp["length"],
            "charset": resp["charset"], "damaged": resp["damaged"],
            "attempts": resp["attempts"], "title": page_title(resp["body"]),
            "text_length": len(body), "excerpt": body[:1200],
            "found": res.found, "missing": res.missing,
            "ok": res.ok, "reason": res.reason, "text": res.text,
            "raw": resp["raw"], "followed": []}
    if card["damaged"]:
        card["reason"] = (f"{card['reason']}; страница декодирована как "
                          f"{resp['charset']} и содержит знаки замены — "
                          "кодировка определена неверно")
    if res.ok or not follow:
        return card

    # Оболочка ИПС: текст акта лежит во фрейме, а не в этом ответе.
    frame = ips_document_url(resp["body"], resp["final_url"], page="all")
    if frame:
        deeper = probe(norm, frame, follow=False)
        card["followed"].append({"url": frame, "ok": deeper.get("ok"),
                                 "reason": deeper.get("reason", "")})
        if deeper.get("ok"):
            deeper["followed"], deeper["reached_from"] = card["followed"], url
            return deeper
        paged = _walk_ips_pages(norm, resp["body"], resp["final_url"], card)
        if paged:
            return paged

    # Печатный вид — второй адрес текста, объявленный той же оболочкой.
    # Замер 16.08.2026: фрейм отдал документ по двум актам из пяти, по трём
    # вернул ответ без статей. Пробовать объявленный порталом второй путь
    # дешевле, чем гадать про параметры первого.
    printed = ips_print_url(resp["body"], resp["final_url"])
    if printed:
        deeper = probe(norm, printed, follow=False)
        card["followed"].append({"url": printed, "ok": deeper.get("ok"),
                                 "reason": deeper.get("reason", "")})
        if deeper.get("ok"):
            deeper["followed"], deeper["reached_from"] = card["followed"], url
            return deeper

    return _walk_search_path(norm, resp["body"], resp["final_url"], card) or card


MAX_HOP_LINKS = 5
MAX_HOP_PAGES = 3


def _walk_search_path(norm: dict, html: str, base: str, card: dict) -> dict:
    """Дойти до документа по ссылкам самих страниц, шаг за шагом.

    Нужно там, где официальный адрес ведёт на перечень. Замер 16.08.2026 по
    сохранённой странице `vsrf.ru/documents/own/`: восемьдесят пять ссылок,
    ни одна не называет 24.03.2016 — постановления там нет, а есть переход
    в раздел «Постановления Пленума». Значит одного шага мало, и путь
    описывается шагами: сначала раздел, потом документ.

    Реквизиты шагов лежат в реестре (`search_path`), адреса — нет: каждый
    следующий адрес берётся из фактического ответа официального источника.
    """
    pages = [(html, base)]
    for hop, terms in enumerate(norm.get("search_path") or [], 1):
        nxt = []
        for page_html, page_base in pages:
            for link in find_document_links(page_html, page_base,
                                            terms)[:MAX_HOP_LINKS]:
                try:
                    resp = fetch(link)
                except Unreachable as e:
                    card["followed"].append({"url": link, "ok": False,
                                             "reason": f"шаг {hop}: {e}"})
                    continue
                res = extract(strip_html(resp["body"]), norm)
                card["followed"].append({"url": link, "ok": res.ok,
                                         "reason": res.reason or f"шаг {hop}"})
                if res.ok:
                    return {**card, "ok": True, "reason": "", "text": res.text,
                            "found": res.found, "missing": [],
                            "reached_from": base}
                nxt.append((resp["body"], resp["final_url"]))
        pages = nxt[:MAX_HOP_PAGES]
        if not pages:
            break
    return {}


MAX_IPS_PAGES = 120


def _walk_ips_pages(norm: dict, shell: str, base: str, card: dict) -> dict:
    """Собрать текст акта по страницам фрейма, когда `page=all` не сработал.

    Страницы складываются и разбираются один раз в конце: статья может
    начаться на одной странице и кончиться на следующей, и разбор по
    отдельности резал бы норму пополам. Обход прекращается на повторе —
    портал на несуществующей странице отдаёт последнюю, и без этого выхода
    цикл был бы вечным.
    """
    chunks, seen = [], set()
    for page in range(1, MAX_IPS_PAGES + 1):
        url = ips_document_url(shell, base, page=str(page))
        if not url:
            break
        try:
            resp = fetch(url)
        except Unreachable as e:
            card["followed"].append({"url": url, "ok": False,
                                     "reason": f"страница {page}: {e}"})
            break
        body = strip_html(resp["body"])
        digest = hashlib.sha1(body.encode("utf-8")).hexdigest()
        if digest in seen or not body:
            break
        seen.add(digest)
        chunks.append(body)

    if not chunks:
        return {}
    res = extract(" ".join(chunks), norm)
    card["followed"].append({"url": f"фрейм по страницам ({len(chunks)})",
                             "ok": res.ok, "reason": res.reason})
    if not res.ok:
        return {}
    return {**card, "ok": True, "reason": "", "text": res.text,
            "found": res.found, "missing": [],
            "reached_from": base, "text_length": sum(len(c) for c in chunks)}


def show_debug(norm: dict, card: dict) -> None:
    print(f"\n=== {norm['norm_id']} — {norm.get('act','')} {norm.get('article','')}")
    for key in ("url", "status", "final_url", "content_type", "charset",
                "damaged", "length", "attempts", "title", "text_length",
                "strategy", "wanted", "subdivisions", "found", "missing",
                "reached_from"):
        if key in card:
            print(f"  {key:14} {card[key]}")
    print(f"  {'извлечено':14} {'да' if card.get('ok') else 'нет'}")
    if card.get("reason"):
        print(f"  {'причина':14} {card['reason']}")
    for step in card.get("followed") or []:
        print(f"  {'перешли':14} {step['url']} → "
              f"{'да' if step['ok'] else step['reason'][:70]}")
    if card.get("excerpt"):
        print(f"  {'начало ответа':14} {card['excerpt'][:400]}")


def capture(card: dict, norm_id: str, out: Path) -> Path:
    """Диагностический слепок. Без cookies и заголовков запроса.

    Пишутся **исходные байты**, а не декодированный текст. Причина замером
    16.08.2026: первый слепок сохранил уже испорченную строку, и по нему
    нельзя было ни проверить починку кодировки, ни восстановить исходное —
    `errors="replace"` необратим. Слепок, теряющий то, ради чего он снят,
    диагностикой не является.

    Страницы кладутся по хешу адреса: шесть актов на семнадцать норм, и
    хранить один и тот же кодекс шесть раз незачем.
    """
    out.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in card.items() if k not in ("text", "raw")}
    payload["excerpt"] = card.get("excerpt", "")[:4000]

    raw = card.get("raw")
    if raw:
        payload["page_file"] = "pages/" + hashlib.sha1(raw).hexdigest()[:16] + ".html"

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
    _SINK[0] = out

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
