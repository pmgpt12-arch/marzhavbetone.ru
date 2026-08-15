#!/usr/bin/env python3
"""Юридический линт: находит места, требующие проверки, и не толкует право.

Появился 15.08.2026 после разбора одной статьи. В
`articles/genpodryadchik-zarabatyvaet-na-vas.html` стояло три ошибки
подряд, и ни одна проверка репозитория их не видела, потому что все они
про смысл, а не про разметку:

  · гарантийный срок объяснялся через ст. 715 ГК РФ — статья называется
    «Права заказчика во время выполнения работы подрядчиком» и о
    гарантийном сроке не говорит вовсе;
  · «гарантийный срок на капитальное строительство — 5 лет (ст. 741 ГК РФ
    + Постановление Правительства № 47)» — ст. 741 о распределении риска
    случайной гибели объекта, постановление № 47 о признании помещения
    жилым; пять лет это предельный срок обнаружения недостатков по
    ст. 756 ГК РФ, а не гарантийный срок;
  · «если срок возврата не прописан — по закону он равен гарантийному
    сроку» — такого правила нет.

Отсюда устройство инструмента. Он **не** решает, верно ли утверждение:
машинно это не решается, а решённое машинно неверно опаснее ненайденного.
Он делает две вещи:

  1. находит в тексте страниц конструкции, которые обязаны быть
     проверены человеком — ссылки на нормы, категоричные утверждения о
     правах и обязанностях, сроки, проценты, взыскание;
  2. сверяет найденное с реестром разобранных утверждений
     `data/legal/claims.csv` и называет то, что ещё никем не смотрено.

То есть красным горит не «здесь ошибка», а «здесь никто не проверял».

В гейте выкладки инструмент стоит предупреждением, а не блокировкой
(решение владельца 15.08.2026): новая статья с непроверенным сроком не
должна останавливать выкладку правки вёрстки. Блокировать имеет смысл
только заведомо неверное, а это ровно то, чего инструмент не знает.

    python3 tools/legal_claim_audit.py             # что найдено и что не смотрено
    python3 tools/legal_claim_audit.py --all       # весь список, включая разобранное
    python3 tools/legal_claim_audit.py --table     # таблица для отчёта
    python3 tools/legal_claim_audit.py --strict    # код 1, если есть непроверенное
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "legal" / "claims.csv"

# Каталоги, где живёт публикуемый текст. Всё остальное — служебное.
SCAN_DIRS = ["articles", "products", "materialy", "demo"]
SCAN_ROOT_FILES = True

SKIP = {"test-pokupka.html", "success.html", "fail.html"}

# Признаки, по которым фрагмент попадает на проверку. Разделены на два
# рода не ради красоты: ссылка на норму проверяется сверкой с текстом
# нормы, а категоричное утверждение — вопросом «чем подтверждено».
NORM_PATTERNS = [
    (r"ст\.?\s?\d+(?:\.\d+)?\s*(?:ГК|АПК|ГПК|УК|НК|ГрК|КоАП)", "ссылка на статью кодекса"),
    (r"стать[ияюё]\s+\d+", "ссылка на статью"),
    (r"\bГК РФ\b", "ГК РФ"),
    (r"\bАПК РФ\b", "АПК РФ"),
    (r"\bФЗ[\s№-]|\bФедеральн\w+ закон", "федеральный закон"),
    (r"постановлени\w+ Правительства", "постановление Правительства"),
    (r"Пленум\w?|Президиум\w?", "разъяснение высшей инстанции"),
]

ASSERTION_PATTERNS = [
    (r"по закону", "«по закону»"),
    (r"\bобязан\w*\b", "«обязан»"),
    (r"\bвправе\b|\bимеет право\b", "«вправе / имеет право»"),
    (r"срок\w*\s+(?:составляет|равен|равн\w+)", "«срок составляет»"),
    (r"\bвзыск\w+", "взыскание"),
    (r"\bнеустойк\w+", "неустойка"),
    (r"\bгарантийн\w+", "гарантийный срок"),
    (r"суд\s+(?:взыщет|обяжет|признает|встанет)", "предсказание решения суда"),
    (r"\d+\s?%", "процент"),
    (r"\b\d+\s+(?:год|года|лет|месяц\w*|дн\w+|суток)\b", "срок числом"),
]

CONTEXT = 110


def visible_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Скрипты и стили — не текст страницы. Разметка JSON-LD полна цифр и
    # дат, и без снятия она давала бы ложные срабатывания пачками.
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def pages() -> list[Path]:
    out: list[Path] = []
    if SCAN_ROOT_FILES:
        out += [p for p in sorted(ROOT.glob("*.html")) if p.name not in SKIP]
    for d in SCAN_DIRS:
        out += sorted((ROOT / d).glob("*.html")) if (ROOT / d).is_dir() else []
    return out


def find_claims(path: Path) -> list[dict[str, str]]:
    text = visible_text(path)
    found: list[dict[str, str]] = []
    seen: set[tuple[int, int]] = set()
    for patterns, kind in ((NORM_PATTERNS, "норма"), (ASSERTION_PATTERNS, "утверждение")):
        for pattern, label in patterns:
            for m in re.finditer(pattern, text, re.I):
                span = (m.start() // CONTEXT, m.end() // CONTEXT)
                key = (span[0], hash(label) % 1000)
                if key in seen:
                    continue
                seen.add(key)
                a, b = max(0, m.start() - CONTEXT), min(len(text), m.end() + CONTEXT)
                found.append({
                    "file": path.relative_to(ROOT).as_posix(),
                    "kind": kind,
                    "signal": label,
                    "matched": m.group(0).strip(),
                    "context": text[a:b].strip(),
                })
    return found


def registry() -> dict[tuple[str, str], dict[str, str]]:
    if not REGISTRY.exists():
        return {}
    out = {}
    with REGISTRY.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[(row["file"], row["claim_key"])] = row
    return out


def claim_key(claim: dict[str, str]) -> str:
    """Ключ утверждения — сигнал плюс совпавший текст. Не весь контекст:
    правка соседнего предложения не должна снимать разбор с записи."""
    return f"{claim['signal']}|{claim['matched'].lower()}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="включая разобранное")
    parser.add_argument("--table", action="store_true", help="таблица для отчёта")
    parser.add_argument("--strict", action="store_true",
                        help="код 1, если есть непроверенное")
    args = parser.parse_args()

    known = registry()
    all_claims: list[dict[str, str]] = []
    for path in pages():
        all_claims.extend(find_claims(path))

    for c in all_claims:
        row = known.get((c["file"], claim_key(c)))
        c["status"] = row["status"] if row else "UNREVIEWED"
        c["problem"] = row.get("problem", "") if row else ""
        c["law_reference"] = row.get("law_reference", "") if row else ""

    unreviewed = [c for c in all_claims if c["status"] == "UNREVIEWED"]
    bad = [c for c in all_claims if c["status"] in ("INCORRECT", "OUTDATED")]

    if args.table:
        w = csv.writer(sys.stdout)
        w.writerow(["file", "claim", "law_reference", "verified", "problem"])
        for c in (all_claims if args.all else unreviewed + bad):
            w.writerow([c["file"], c["context"][:200], c["law_reference"],
                        c["status"], c["problem"]])
        return 0

    by_file: dict[str, list[dict[str, str]]] = {}
    for c in (all_claims if args.all else unreviewed):
        by_file.setdefault(c["file"], []).append(c)

    for f in sorted(by_file):
        print(f"\n{f}")
        for c in by_file[f][:12]:
            print(f"   [{c['status']}] {c['signal']}: …{c['context'][:150]}…")
        if len(by_file[f]) > 12:
            print(f"   … ещё {len(by_file[f]) - 12}")

    pages_count = len(pages())
    print(f"\nСтраниц просмотрено: {pages_count}; "
          f"мест на проверку: {len(all_claims)}; "
          f"разобрано: {len(all_claims) - len(unreviewed)}; "
          f"не смотрено: {len(unreviewed)}")
    if bad:
        print(f"ЗАПИСАНО КАК НЕВЕРНОЕ И НЕ ИСПРАВЛЕНО: {len(bad)}")
        for c in bad:
            print(f"   ✗ {c['file']}: {c['problem']}")

    # Инструмент не выносит вердикта о праве. Красное здесь означает
    # «есть непроверенное человеком», и то лишь по явной просьбе.
    if bad:
        return 1
    if args.strict and unreviewed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
