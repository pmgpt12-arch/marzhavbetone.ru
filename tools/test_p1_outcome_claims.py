#!/usr/bin/env python3
"""Регрессия P1: внешний результат спора не может быть итогом шаблона."""
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).with_name("check_storefront_claims.py")
spec = importlib.util.spec_from_file_location("check_storefront_claims", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

bad = (
    "Пошаговый порядок до денег на счёте.",
    "Результат шага: деньги на счете.",
    "Задача выполнена, когда оплата получена — либо иск принят.",
    "Формальных причин вернуть комплект не остаётся.",
    "Гарантированное взыскание задолженности.",
)
for phrase in bad:
    assert module.обещания_п1(phrase), f"пропущено обещание: {phrase}"

allowed = (
    "Ближайший результат: проверены сумма, дата и документы.",
    "Получение оплаты зависит от договора и позиции сторон.",
    "Шаблон не даёт гарантий взыскания.",
)
for phrase in allowed:
    assert not module.обещания_п1(phrase), f"ложный запрет: {phrase}"

issues = []
module.проверить_результат_п1(issues)
assert not issues, "ошибки в текущей выдаче:\n" + "\n".join(issues)
print("P1 outcome claims: fixtures and buyer sources PASS")
