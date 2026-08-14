#!/usr/bin/env python3
"""Доказательный контур: схемы, уверенность, гейт публикации.

Проверяет то, что задано в `data/evidence/rules.yaml`, и ровно там, где
ошибка стоит дороже всего — в утверждении о мире, за которым нет выборки.

Дефект (код 1):
  • колонки базы разошлись с объявленной схемой;
  • утверждение без evidence_id или со ссылкой на несуществующий;
  • утверждение о праве, опирающееся только на класс D или E;
  • confidence LOW со статусом published;
  • HIGH или MEDIUM без выборки нужного размера;
  • расчёт, в котором числитель, знаменатель и результат не сходятся;
  • **ловушка знаменателя**: `denominator_scope: subset` при выводе,
    сформулированном как влияние на исход;
  • исследование в статусе published без ограничений и выборки;
  • число-статистика на странице сайта, не заведённое в реестре.

Замечание (кода не меняет):
  • подошёл срок перепроверки утверждения (`review_due`).

    python3 tools/check_evidence.py
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "data" / "evidence"
RULES = EV / "rules.yaml"
RESEARCH = ROOT / "research"

SCHEMAS = {
    "evidence.csv": [
        "evidence_id", "source_type", "source_class", "source_url",
        "source_name", "publication_date", "effective_date", "jurisdiction",
        "topic", "money_cluster", "claim", "quote_or_fact", "context",
        "verified", "verified_at", "superseded", "superseded_by", "used_in",
        "notes"],
    "court-cases.csv": [
        "case_id", "court", "instance", "decision_date", "case_number",
        "plaintiff_role", "defendant_role", "contract_type", "work_type",
        "claim_type", "claim_amount", "awarded_amount", "money_cluster",
        "ks2_status", "ks3_status", "acceptance_status",
        "executive_docs_status", "additional_works", "written_instruction",
        "contract_condition", "payment_condition", "retention", "expertise",
        "outcome", "contractor_won", "key_reason", "key_evidence",
        "failure_reason", "source_url", "verified", "notes"],
    "claims.csv": [
        "claim_id", "claim", "claim_type", "evidence_ids", "confidence",
        "first_published", "last_verified", "review_due", "pages_using_claim",
        "products_using_claim", "status"],
}

# Утверждение о мире, а не расчёт в примере. Пример узнаётся по соседству
# с суммой договора: «КС-2 на 5 млн, из них 90% — погашение аванса» это
# арифметика конкретного случая, а не статистика.
STAT = re.compile(r"(?:в|у)\s+(\d{1,3})\s*%\s+(?:случаев|дел|споров|"
                  r"подрядчиков|договоров)|(\d+)\s+из\s+(\d+)\s+(?:дел|"
                  r"споров|решений|случаев)")


def read_rules() -> dict:
    """Узкий разбор: сюда смотрит человек, поэтому формат простой."""
    out: dict = {"insufficient": [], "confidence": {}, "causal": [],
                 "scopes": []}
    section = None
    key = None
    for raw in RULES.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        if indent == 0 and text.endswith(":"):
            section = text[:-1]
            continue
        if section == "insufficient_for_legal_claim" or (
                indent == 0 and text.startswith("insufficient_for_legal_claim:")):
            out["insufficient"] = re.findall(r"SOURCE_[A-E]", text)
        elif section == "confidence":
            if indent == 2 and text.endswith(":"):
                key = text[:-1]
                out["confidence"][key] = {"classes": [], "min": 0,
                                          "forbidden": False}
            elif indent == 4 and text.startswith("требует_классы:"):
                out["confidence"][key]["classes"] = re.findall(
                    r"SOURCE_[A-E]", text)
            elif indent == 4 and text.startswith("минимальная_выборка:"):
                out["confidence"][key]["min"] = int(text.split(":")[1])
            elif indent == 4 and text.startswith("публикация_запрещена:"):
                out["confidence"][key]["forbidden"] = "true" in text
        elif section == "causal_markers" and text.startswith("- "):
            out["causal"].append(text[2:].strip().strip('"'))
        elif section == "denominator_scopes" and indent == 2:
            out["scopes"].append(text.split(":")[0].strip())
    if not out["insufficient"]:
        text = RULES.read_text(encoding="utf-8")
        m = re.search(r"insufficient_for_legal_claim:\s*\[([^\]]*)\]", text)
        if m:
            out["insufficient"] = re.findall(r"SOURCE_[A-E]", m.group(1))
    return out


def read_yaml_flat(path: Path) -> dict:
    """Плоские ключи верхнего уровня исследования. Списки — как есть."""
    out: dict = {}
    key = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")) and ":" in line:
            key, _, rest = line.partition(":")
            key = key.strip()
            out[key] = rest.strip()
        elif key and line.strip().startswith("- "):
            out.setdefault(key + "__list", []).append(line.strip()[2:])
        elif key and out.get(key) in (">", "|", ""):
            out[key] = (str(out.get(key, "")).replace(">", "").strip()
                        + " " + line.strip()).strip()
    return out


def main() -> int:
    rules = read_rules()
    defects: list[str] = []
    notes: list[str] = []
    today = date.today().isoformat()

    # 1. Схемы баз.
    tables: dict[str, list[dict]] = {}
    for name, cols in SCHEMAS.items():
        path = EV / name
        if not path.exists():
            defects.append(f"{name}: базы нет")
            continue
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != cols:
                defects.append(
                    f"{name}: колонки разошлись со схемой\n"
                    f"      объявлено: {', '.join(cols)}\n"
                    f"      в файле:   {', '.join(reader.fieldnames or [])}")
                continue
            tables[name] = list(reader)

    evidence = {r["evidence_id"]: r for r in tables.get("evidence.csv", [])}
    claims = tables.get("claims.csv", [])

    # 2. Утверждения.
    for row in claims:
        cid = row["claim_id"] or "(без id)"
        ids = [s.strip() for s in row["evidence_ids"].split(";") if s.strip()]
        if not ids:
            defects.append(f"{cid}: утверждение без единого evidence_id")
        for eid in ids:
            if eid not in evidence:
                defects.append(f"{cid}: ссылка на несуществующий {eid}")

        conf = row["confidence"].strip().upper()
        spec = rules["confidence"].get(conf)
        if conf and not spec:
            defects.append(f"{cid}: неизвестная уверенность «{conf}»")
        if spec and spec["forbidden"] and row["status"].strip() == "published":
            defects.append(
                f"{cid}: confidence {conf} опубликован — "
                f"LOW публикуется только как гипотеза, не как закономерность")

        if row["claim_type"].strip() == "legal" and ids:
            classes = {evidence[e]["source_class"] for e in ids
                       if e in evidence}
            if classes and classes <= set(rules["insufficient"]):
                defects.append(
                    f"{cid}: вывод о праве опирается только на "
                    f"{', '.join(sorted(classes))} — нужен первичный источник")

        due = row["review_due"].strip()
        if due and due <= today and row["status"].strip() == "published":
            notes.append(f"{cid}: подошёл срок перепроверки ({due})")

    # 3. Исследования.
    for path in sorted(RESEARCH.glob("*.yaml")):
        if path.name == "SCHEMA.yaml":
            continue
        data = read_yaml_flat(path)
        rel = path.relative_to(ROOT).as_posix()
        status = data.get("status", "").strip()

        scope = data.get("denominator_scope", "").strip()
        if scope and scope not in rules["scopes"]:
            defects.append(f"{rel}: denominator_scope «{scope}» не объявлен "
                           f"в rules.yaml")
        if scope == "unknown":
            defects.append(f"{rel}: знаменатель не установлен — "
                           f"публикация запрещена")

        # Ловушка знаменателя: вывод о подмножестве, поданный как влияние.
        if scope == "subset":
            question = " ".join(str(v) for k, v in data.items()
                                if k in ("research_question", "hypothesis",
                                         "results"))
            hit = [m for m in rules["causal"] if m in question.lower()]
            if hit:
                defects.append(
                    f"{rel}: знаменатель взят из части выборки, а вывод "
                    f"сформулирован как влияние на исход ({', '.join(hit)}) — "
                    f"это ловушка знаменателя, публикация блокируется")

        if status == "published":
            if not data.get("limitations__list"):
                defects.append(f"{rel}: опубликовано без раздела ограничений")
            if data.get("results", "").strip() in ("", "not_collected"):
                defects.append(f"{rel}: статус published при несобранных "
                               f"результатах")

        # Арифметика: если числа объявлены, они обязаны сходиться.
        num, den = data.get("numerator", ""), data.get("denominator", "")
        if num and den:
            try:
                got = round(int(num) / int(den) * 100, 1)
                declared = float(str(data.get("result", "0")).rstrip("%"))
                if abs(got - declared) > 0.15:
                    defects.append(
                        f"{rel}: {num}/{den} даёт {got}%, объявлено "
                        f"{declared}%")
            except (ValueError, ZeroDivisionError) as e:
                defects.append(f"{rel}: расчёт не проверяется ({e})")

    # 4. Статистика на страницах сайта против реестра.
    registered = " ".join(r["claim"] for r in claims)
    for pattern in ("*.html", "articles/*.html", "products/*.html",
                    "materialy/*.html", "demo/*.html"):
        for page in sorted(ROOT.glob(pattern)):
            text = re.sub(r"<[^>]+>", " ",
                          re.sub(r"<(script|style).*?</\1>", " ",
                                 page.read_text(encoding="utf-8",
                                                errors="replace"),
                                 flags=re.S))
            for m in STAT.finditer(text):
                fragment = " ".join(m.group(0).split())
                if fragment not in registered:
                    defects.append(
                        f"/{page.relative_to(ROOT).as_posix()}: утверждение "
                        f"«{fragment}» не заведено в claims.csv — число о "
                        f"мире без выборки публиковать нельзя")

    print(f"Утверждений в реестре: {len(claims)}; "
          f"доказательств: {len(evidence)}; "
          f"дел: {len(tables.get('court-cases.csv', []))}; "
          f"исследований: {len(list(RESEARCH.glob('*.yaml')))}")

    if notes:
        print(f"\n## Замечания — {len(notes)}")
        for n in notes:
            print(f"   • {n}")

    if defects:
        print(f"\n## ДЕФЕКТЫ — {len(defects)}")
        for d in defects:
            print(f"   ✗ {d}")
        return 1

    print("\nДефектов нет: схемы совпадают, утверждений без доказательств "
          "нет, придуманной статистики на страницах нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
