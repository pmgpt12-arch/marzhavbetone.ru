#!/usr/bin/env python3
"""Размеченный набор запросов против правил классификации.

Набор — примеры владельца из постановки этапа, дословно, плюс случаи,
на которых правила уже ломались. Смысл теста не «правила верны вообще», а
«названный случай размечается так, как назвал владелец»: иначе разметка
чинится на глаз и ломается молча.

Первый пойманный случай — «КС-2 подписана, оплаты нет». Правила отдавали
его в INFORMATION по слову «кс-2»: денежного маркера на «оплаты нет» не
существовало. Пример владельца называет его MONEY.

Запуск без pytest: python3 tools/test_search_demand.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from search_demand import classify, load_rules  # noqa: E402

# Примеры из постановки этапа, дословно.
CASES: list[tuple[str, str]] = [
    # MONEY — денежная проблема уже есть.
    ("генподрядчик не платит за выполненные работы", "MONEY"),
    ("КС-2 подписана, оплаты нет", "MONEY"),
    ("как вернуть гарантийное удержание", "MONEY"),
    ("заказчик не оплачивает дополнительные работы", "MONEY"),
    ("претензия за выполненные строительные работы", "MONEY"),
    # PROBLEM — рядом с денежным риском, но деньги ещё не названы.
    ("заказчик не подписывает КС-2", "PROBLEM"),
    ("отказ от приёмки работ", "PROBLEM"),
    ("исполнительная документация не принята", "PROBLEM"),
    ("дополнительные работы без допсоглашения", "PROBLEM"),
    ("как оформить акт скрытых работ", "PROBLEM"),
    # INFORMATION — профессиональный вопрос без риска.
    ("что такое КС-2", "INFORMATION"),
    ("состав исполнительной документации", "INFORMATION"),
    ("кто подписывает акт скрытых работ", "INFORMATION"),
    # IRRELEVANT — не наша бизнес-модель.
    ("работа вахтой бетонщик", "IRRELEVANT"),
    ("купить бетон цена за куб", "IRRELEVANT"),
    ("вакансии прораб москва", "IRRELEVANT"),
]

VALUE_OF = {"MONEY": "A", "PROBLEM": "B", "INFORMATION": "C",
            "IRRELEVANT": "D"}


def test_labelled_cases_match_the_rules() -> None:
    rules = load_rules()
    assert rules, "правила не прочитались — разметка была бы пустой молча"
    wrong = []
    for query, expected in CASES:
        intent, value = classify(query, rules)
        if intent != expected:
            wrong.append(f"«{query}»: ожидалось {expected}, вышло "
                         f"{intent or 'ничего'}")
        elif value != VALUE_OF[expected]:
            wrong.append(f"«{query}»: {expected} даёт {value}, "
                         f"а должен {VALUE_OF[expected]}")
    assert not wrong, "расхождений " + str(len(wrong)) + ":\n  " + \
                      "\n  ".join(wrong)


def test_money_wins_over_information() -> None:
    """Порядок проверки — часть правила, а не деталь реализации.

    «КС-2 подписана, оплаты нет» содержит и денежный маркер, и
    информационный. Денежный обязан выиграть, иначе самый ценный запрос
    уедет в информационный кластер.
    """
    rules = load_rules()
    intent, _ = classify("кс-2 подписана оплаты нет", rules)
    assert intent == "MONEY", intent


def test_irrelevant_wins_over_money() -> None:
    """Чужой запрос отсекается раньше денежного маркера.

    «зарплата прораба не выплачена» — про трудовой спор, а не про
    субподрядчика, хотя «не выплачена» звучит денежно.
    """
    rules = load_rules()
    intent, _ = classify("зарплата прораба не выплачена", rules)
    assert intent == "IRRELEVANT", intent


def test_unknown_query_is_left_unmarked() -> None:
    """Незнакомый запрос остаётся без разметки, а не назначается наугад."""
    rules = load_rules()
    intent, value = classify("асфальтоукладчик аренда сутки", rules)
    assert (intent, value) == ("", ""), (intent, value)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
