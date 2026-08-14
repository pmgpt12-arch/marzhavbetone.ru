#!/usr/bin/env python3
"""Размеченные случаи для доказательного контура.

Проверка на пустых базах зеленеет всегда — это ничего не значит. Здесь
каждый запрет из `data/evidence/rules.yaml` проверяется случаем, который
обязан быть пойман, и парным случаем, который ловиться не должен.

Главный случай — ловушка знаменателя из постановки владельца: 18 из 27
проигравших подрядчиков не имели письменного поручения. Вывод «без
письменного поручения подрядчик проигрывает в 67% случаев» неверен,
потому что знаменатель взят только из проигравших дел.

Запуск без pytest: python3 tools/test_evidence.py
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "data" / "evidence"
RESEARCH = ROOT / "research"
CHECK = ROOT / "tools" / "check_evidence.py"

PROBE_RESEARCH = RESEARCH / "_probe.yaml"


def run() -> tuple[int, str]:
    done = subprocess.run([sys.executable, str(CHECK)],
                          capture_output=True, text=True, cwd=ROOT)
    return done.returncode, done.stdout + done.stderr


def with_rows(name: str, rows: list[dict]):
    """Временно дописывает строки в базу и возвращает её обратно."""
    path = EV / name
    original = path.read_bytes()

    class Ctx:
        def __enter__(self):
            with path.open("a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=path.read_text(encoding="utf-8")
                    .splitlines()[0].split(","))
                for row in rows:
                    writer.writerow(row)

        def __exit__(self, *exc):
            path.write_bytes(original)
    return Ctx()


def evidence_row(eid: str, cls: str) -> dict:
    return {"evidence_id": eid, "source_type": "COURT", "source_class": cls,
            "source_url": "https://example.test/act", "source_name": "проба",
            "publication_date": "2026-01-01", "effective_date": "",
            "jurisdiction": "RU", "topic": "проба", "money_cluster": "MI-3",
            "claim": "проба", "quote_or_fact": "проба", "context": "",
            "verified": "yes", "verified_at": "2026-01-01", "superseded": "",
            "superseded_by": "", "used_in": "", "notes": ""}


def claim_row(**over) -> dict:
    row = {"claim_id": "PROBE-1", "claim": "проба", "claim_type": "legal",
           "evidence_ids": "PROBE-E1", "confidence": "HIGH",
           "first_published": "2026-01-01", "last_verified": "2026-01-01",
           "review_due": "2027-01-01", "pages_using_claim": "",
           "products_using_claim": "", "status": "draft"}
    row.update(over)
    return row


def test_baseline_is_clean() -> None:
    code, out = run()
    assert code == 0, f"база уже не чиста:\n{out}"


def test_claim_without_evidence_is_blocked() -> None:
    with with_rows("claims.csv", [claim_row(evidence_ids="")]):
        code, out = run()
    assert code == 1 and "без единого evidence_id" in out, out


def test_claim_with_unknown_evidence_is_blocked() -> None:
    with with_rows("claims.csv", [claim_row(evidence_ids="NET-TAKOGO")]):
        code, out = run()
    assert code == 1 and "несуществующий" in out, out


def test_legal_claim_on_media_only_is_blocked() -> None:
    """Вывод о праве на классе D — недостаточно, даже если источник есть."""
    with with_rows("evidence.csv", [evidence_row("PROBE-E1", "SOURCE_D")]):
        with with_rows("claims.csv", [claim_row()]):
            code, out = run()
    assert code == 1 and "первичный источник" in out, out


def test_legal_claim_on_court_act_passes() -> None:
    """Парный случай: тот же вывод на судебном акте ловиться не должен."""
    with with_rows("evidence.csv", [evidence_row("PROBE-E1", "SOURCE_B")]):
        with with_rows("claims.csv", [claim_row()]):
            code, out = run()
    assert code == 0, f"ложное срабатывание:\n{out}"


def test_low_confidence_cannot_be_published() -> None:
    with with_rows("evidence.csv", [evidence_row("PROBE-E1", "SOURCE_B")]):
        with with_rows("claims.csv", [claim_row(confidence="LOW",
                                                status="published")]):
            code, out = run()
    assert code == 1 and "LOW публикуется только как гипотеза" in out, out


def test_denominator_trap_is_blocked() -> None:
    """Случай владельца: 18 из 27 проигравших → «проигрывает в 67%»."""
    PROBE_RESEARCH.write_text(
        "research_id: _probe\n"
        "status: planned\n"
        "research_question: >\n"
        "  Насколько отсутствие письменного поручения приводит к\n"
        "  проигрышу подрядчика\n"
        "denominator_scope: subset\n"
        "numerator: 18\n"
        "denominator: 27\n"
        "result: 66.7\n",
        encoding="utf-8")
    try:
        code, out = run()
    finally:
        PROBE_RESEARCH.unlink(missing_ok=True)
    assert code == 1 and "ловушка знаменателя" in out, out


def test_same_numbers_about_the_subset_pass() -> None:
    """Те же числа без вывода о влиянии — допустимы: это факт о подвыборке."""
    PROBE_RESEARCH.write_text(
        "research_id: _probe\n"
        "status: planned\n"
        "research_question: >\n"
        "  Как часто среди проигранных дел отсутствовало письменное\n"
        "  поручение\n"
        "denominator_scope: subset\n"
        "numerator: 18\n"
        "denominator: 27\n"
        "result: 66.7\n",
        encoding="utf-8")
    try:
        code, out = run()
    finally:
        PROBE_RESEARCH.unlink(missing_ok=True)
    assert code == 0, f"ложное срабатывание на факте о подвыборке:\n{out}"


def test_arithmetic_must_add_up() -> None:
    PROBE_RESEARCH.write_text(
        "research_id: _probe\n"
        "status: planned\n"
        "research_question: сколько\n"
        "denominator_scope: full_sample\n"
        "numerator: 18\n"
        "denominator: 27\n"
        "result: 80.0\n",
        encoding="utf-8")
    try:
        code, out = run()
    finally:
        PROBE_RESEARCH.unlink(missing_ok=True)
    assert code == 1 and "объявлено" in out, out


def test_published_without_limitations_is_blocked() -> None:
    PROBE_RESEARCH.write_text(
        "research_id: _probe\n"
        "status: published\n"
        "research_question: сколько\n"
        "denominator_scope: full_sample\n"
        "results: not_collected\n",
        encoding="utf-8")
    try:
        code, out = run()
    finally:
        PROBE_RESEARCH.unlink(missing_ok=True)
    assert code == 1 and "ограничен" in out, out


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {str(e)[:200]}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
