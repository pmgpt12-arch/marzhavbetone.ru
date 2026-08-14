#!/usr/bin/env python3
"""Нужен ли материал, и если да — какой. Решение, а не текст.

Маршрутизатор ничего не пишет. Он отвечает на один вопрос: под этот
сигнал заводить новый адрес, усиливать существующий или не делать ничего.
По умолчанию — усиливать существующий: новый URL заводится только под
самостоятельный интент, иначе сайт разрастается каннибализацией.

    python3 tools/content_router.py "гарантийное удержание не возвращают"
    python3 tools/content_router.py --check    # проверки баз и запретов

Проверки (код 1):
  • колонки баз не совпадают со схемой;
  • крючок с числом без ссылки на доказательство (`hooks.csv`);
  • строка очереди с неизвестным статусом или без цели;
  • внешняя ссылка в материалах канала без `utm_source`.

Решение по сигналу кодом возврата не отражается: это подсказка человеку,
а не вердикт. Вердикт о составе сайта остаётся владельцу.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "data" / "content"
RULES = CONTENT / "rules.yaml"
EVIDENCE = ROOT / "data" / "evidence" / "evidence.csv"

STATUSES = {"IDEA", "VALIDATED", "DRAFT", "REVIEW", "APPROVED", "SCHEDULED",
            "PUBLISHED", "MEASURING", "LEARNED", "ARCHIVED"}

SCHEMAS = {
 "opportunities.csv": ["opportunity_id", "source", "topic", "money_cluster",
  "primary_intent", "target_audience", "user_problem", "evidence",
  "search_demand", "novelty", "product_connection", "existing_pages",
  "recommended_action", "priority", "confidence", "channels",
  "reason_to_publish"],
 "publication-queue.csv": ["content_id", "source_insight", "content_type",
  "channel", "priority", "status", "scheduled_date", "published_url",
  "campaign", "target_page", "target_product", "owner", "created_at"],
 "performance.csv": ["content_id", "channel", "published_at", "views",
  "reach", "watch_time", "completion_rate", "likes", "comments", "saves",
  "shares", "profile_visits", "site_clicks", "free_downloads",
  "product_clicks", "purchases", "revenue", "updated_at"],
 "learnings.csv": ["learning_id", "content_id", "channel", "hypothesis",
  "observation", "result", "confidence", "applies_to", "recommended_change",
  "created_at"],
 "hooks.csv": ["hook_id", "hook_type", "text", "money_cluster",
  "evidence_ids", "used", "views", "completion_rate", "saves", "shares",
  "profile_visits", "site_clicks", "performance_status"],
 "creative-memory.csv": ["memory_id", "content_id", "published_at",
  "channel", "hook_type", "plot", "case_ref", "cta", "visual",
  "money_cluster", "notes"],
 "calendar.csv": ["date", "channel", "content_id", "cluster",
  "content_class", "campaign", "product", "objective"],
}


def markers() -> list[str]:
    """Обороты, делающие крючок утверждением о факте."""
    out, section = [], None
    for raw in RULES.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        if not raw.startswith((" ", "\t")) and text.endswith(":"):
            section = text[:-1]
        elif section == "factual_markers" and text.startswith("- "):
            out.append(text[2:].strip().strip('"'))
    return out


def read(name: str) -> list[dict]:
    path = CONTENT / name
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def site_pages() -> dict[str, str]:
    """Опубликованные страницы: адрес → заголовок первого уровня."""
    pages = {}
    for pattern in ("articles/*.html", "materialy/*.html", "products/*.html"):
        for path in sorted(ROOT.glob(pattern)):
            if path.name == "index.html":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
            pages["/" + path.relative_to(ROOT).as_posix()] = title
    return pages


def route(signal: str) -> int:
    """Подсказка по сигналу: что уже есть на сайте под эту тему."""
    words = [w for w in re.findall(r"[а-яёa-z0-9-]{4,}", signal.lower())]
    scored = []
    for url, title in site_pages().items():
        hay = (url + " " + title).lower()
        hits = sum(1 for w in words if w in hay)
        if hits:
            scored.append((-hits, url, title))
    scored.sort()

    print(f"Сигнал: «{signal}»")
    if not scored:
        print("\nСовпадений на сайте нет.")
        print("Решение по умолчанию неприменимо — усиливать нечего.")
        print("Кандидат на CREATE, но только при самостоятельном интенте и")
        print("подтверждённом спросе. Вердикт — владельца.")
        return 0

    print(f"\nСтраницы под эту тему уже есть — {len(scored)}:")
    for neg, url, title in scored[:6]:
        print(f"   {-neg} совпад.  {url}\n              {title}")

    best = scored[0]
    print(f"\nРешение по умолчанию: UPDATE_EXISTING → {best[1]}")
    print("Новый адрес заводится, только если у сигнала самостоятельный")
    print("интент, которого эта страница не закрывает. Это решение")
    print("владельца, а не вывод инструмента.")
    return 0


def check() -> int:
    defects: list[str] = []
    facts = markers()

    for name, cols in SCHEMAS.items():
        path = CONTENT / name
        if not path.exists():
            defects.append(f"{name}: базы нет")
            continue
        with path.open(encoding="utf-8", newline="") as f:
            got = csv.DictReader(f).fieldnames
        if got != cols:
            defects.append(f"{name}: колонки разошлись со схемой")

    known_evidence: set[str] = set()
    if EVIDENCE.exists():
        with EVIDENCE.open(encoding="utf-8", newline="") as f:
            known_evidence = {r["evidence_id"] for r in csv.DictReader(f)}

    for row in read("hooks.csv") if (CONTENT / "hooks.csv").exists() else []:
        text = row.get("text", "").lower()
        # По границам слова, а не по подстроке. Замер: маркер «дел»
        # срабатывал внутри «делать», и крючок-вопрос «что делать, если
        # генподрядчик перестал платить» объявлялся утверждением о факте.
        # Знаки «%» и «₽» границ слова не имеют — они ищутся как есть.
        hit = []
        for m in facts:
            pattern = (re.escape(m) if not m[0].isalnum()
                       else r"\b" + re.escape(m) + r"\b")
            if re.search(pattern, text):
                hit.append(m)
        ids = [s.strip() for s in row.get("evidence_ids", "").split(";")
               if s.strip()]
        if hit and not ids:
            defects.append(
                f"{row.get('hook_id')}: крючок содержит утверждение о факте "
                f"({', '.join(hit)}) без ссылки на доказательство")
        for eid in ids:
            if known_evidence and eid not in known_evidence:
                defects.append(f"{row.get('hook_id')}: {eid} нет в реестре")

    for row in (read("publication-queue.csv")
                if (CONTENT / "publication-queue.csv").exists() else []):
        status = row.get("status", "").strip().upper()
        if status and status not in STATUSES:
            defects.append(f"{row.get('content_id')}: неизвестный статус "
                           f"«{status}»")
        if status == "PUBLISHED" and not row.get("published_url", "").strip():
            defects.append(f"{row.get('content_id')}: статус PUBLISHED без "
                           f"адреса публикации")
        if status in {"APPROVED", "SCHEDULED", "PUBLISHED"} \
                and not row.get("target_page", "").strip() \
                and not row.get("target_product", "").strip():
            defects.append(f"{row.get('content_id')}: материал без цели — "
                           f"ни страницы, ни комплекта")

    # Внешние каналы: ссылка без разметки не измеряется вовсе. Но метку
    # каждый канал приделывает по-своему, и требовать её в тексте от всех
    # — ошибка. Первая версия этой проверки объявила дефектом пятнадцать
    # исправных постов Телеграма: `post_telegram.py` собирает
    # `utm_source=telegram&utm_medium=post&utm_campaign=…` при отправке из
    # шапки файла, и в тексте её нет по устройству.
    #
    # Отсюда проверка идёт по механизму канала, а не по одному шаблону.
    # Ролики не проверяются здесь вовсе: их метку держит `check_reel.py`,
    # и вторая проверка того же места разошлась бы с первой.
    for path in sorted((ROOT / "content" / "telegram").glob("*.md")) \
            if (ROOT / "content" / "telegram").exists() else []:
        if path.name.upper().startswith("README"):
            continue
        head = path.read_text(encoding="utf-8", errors="replace")[:600]
        if "marzhavbetone.ru" not in head:
            continue
        if "utm_campaign:" not in head:
            defects.append(f"content/telegram/{path.name}: в шапке нет "
                           f"utm_campaign — отправка не разметит ссылку")

    for folder in ("content/dzen", "content/social"):
        for path in sorted((ROOT / folder).glob("*.md")) \
                if (ROOT / folder).exists() else []:
            if path.name.upper().startswith("README"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            links = re.findall(r"https://marzhavbetone\.ru/[^\s\)\"]+", text)
            # Черновик Дзена собирается build_dzen_draft.py и метку несёт
            # в теле; заготовка без ссылок на сайт проверке не подлежит.
            bad = [l for l in links if "utm_source=" not in l
                   and not l.endswith(("rss.xml", "rss.xml`."))]
            if bad and "utm_campaign:" not in text[:600]:
                defects.append(f"{folder}/{path.name}: ссылка без разметки — "
                               f"{bad[0][:70]}")

    counts = {n: len(read(n)) for n in SCHEMAS if (CONTENT / n).exists()}
    print("Базы контентного контура: "
          + ", ".join(f"{n.replace('.csv','')} {c}" for n, c in counts.items()))

    if defects:
        print(f"\n## ДЕФЕКТЫ — {len(defects)}")
        for d in defects:
            print(f"   ✗ {d}")
        return 1

    print("\nДефектов нет: схемы совпадают, крючков с неподтверждённым "
          "числом нет, ссылки внешних каналов размечены.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("signal", nargs="?", help="тема или запрос")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check or not args.signal:
        return check()
    return route(args.signal)


if __name__ == "__main__":
    sys.exit(main())
