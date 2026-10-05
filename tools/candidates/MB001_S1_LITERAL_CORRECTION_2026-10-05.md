# S1: узкое исправление A-1 длины литерала

{
  "status": "AUTHOR_CANDIDATE",
  "old_literal_chars": 293,
  "old_affected_cells": 500,
  "changed_formula_cells": 500,
  "new_oversized_literals": 0,
  "max_literal_utf16_units_02_04_08": 226,
  "other10buyer_and_manifest_unchanged": true,
  "displayed_warning_identical": true,
  "financial_decisions_unchanged": true,
  "B2": "BLOCK",
  "L1c": 550000,
  "native_Excel": "NOT VERIFIED",
  "owner_style_snapshot": "Preserved separately, not overwritten",
  "checks": "Scope, styles, formula collapse, negative/positive literal gate, actual Calc/reopen/oracle"
}

Источник риска: Microsoft Q&A https://learn.microsoft.com/en-ca/answers/questions/5041885/text-values-in-formulas-limited-to-255 — предел отдельной quotedstring, не общей длины формулы. Десктопное повреждение книги не наблюдалось, это был риск совместимости. Строка разбита через & без изменения видимого предупреждения и финансового решения. Gate проверяет книги02/04/08 и границы255/256, экранированныекавычки, допустимуюконкатенацию. R1/R2 прежней финансовойприёмки остаются раскрыты; не исправлялись.

Кандидат требует независимой проверки A-1 по новомуSHA. Это не приёмка владельческихстилей или продукта целиком.
