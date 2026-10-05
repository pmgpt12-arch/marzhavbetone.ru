# S1 — 08 print: rate display and row 13 overflow (F-1/F-2), AUTHOR CANDIDATE

**Status: AUTHOR CANDIDATE. This is not independent acceptance and not SALE_READY.** Excel, legal conclusions — **NOT VERIFIED**.

- Base: `01100bdf85d5575b68dab2847152edf4e0cc00bd` (PR #373 with the #376 report merged).
- Executor: anthropic/claude-opus-5.5 via OpenRouter, one attempt.
- Sources read: `tools/candidates/MB001_P1_RESIDUAL_INDEPENDENT_ACCEPTANCE.md` (F-1, F-2) and `tools/build_s1_candidate.py` `f08`.
- Input integrity: `sha256sum p1-display-inputs/*` matches `index.json` for all entries.
- Run dir: `…/p1-display-20261005/377/`. It holds the scripts, the ru-RU profile, PDFs and logs.
- Committed evidence: `tools/candidates/evidence/S1_PRINT_RATE/`.

## Root cause

Class: **inherited format / display**. Stored values and formulas were correct.

- **F-2.** «Ввод» B12:B71, «Расчёт» G and «По дням» B had the General format.
  - In Calc, typing `21%` stores 0,21 and gives the cell a percent format.
  - Re-typing `21` stores 21, but the percent format stays: «2100,00%».
  - Formula cells with the General format inherit that format through the INDEX chain («По дням» B → «Расчёт» G). So the READY print showed «2100,00%» on «Ввод», «Расчёт» and «По дням».
  - Reproduced on the old 08 (`calc-old-8f05aee9.json`, `print-reentry-reopened-old.txt`).
- **F-1.** The «Проверки» rows had no height set. Calc does not grow the row when a formula result wraps.
  - Row 13 was 10,00 mm; Calc's optimal height for the message is 19,47 mm.
  - In the PDF, the third line of the message prints over «ок» of row 14 (`print-mismatch-old.txt`).

## Correction (08 only; values and formulas unchanged)

All changes are in `build_s1_candidate.py`:

1. `RATE = "0.00##"` is set explicitly on «Расчёт» G7:G518 and «По дням» B2:B4000. With a non-General format these cells cannot inherit the input cell's format.
2. «Ввод» B12:B71 get the direct format `0.00##` plus a **conditional format** `ISNUMBER(B12)` with dxf numFmt `0.00##`.
   - Typing can change a cell's own format, but it does not remove the conditional format.
   - So the printed number has no «%» even when the cell itself is percent-formatted.
   - I do not rely on the initial format alone. I also do not guess intent from magnitude, and I do not use `CELL("format")`.
3. Each «Проверки» row gets `fit_height` sized to its longest possible message. The new helper `самое_длинное` joins the string literals that are linked by `&…&` and substitutes `999 999 999,99` for each sum. Row 13 is now 63 pt (22,23 mm). The message text was not shortened.

The existing checks are unchanged: rate 0–100, the `<1` «похоже на долю» block, B5/B6 reconciliation, payments, days and rounding.

Cell-level diff of old vs new 08 (openpyxl, all sheets):
- **0 differences in values or formulas.**
- Formats: Ввод B ×60, Расчёт G ×512, По дням B ×3999 (General → `0.00##`).
- Height set on Проверки rows 2–18, plus one CF rule on Ввод B12:B71.

The zip has no external, VBA or `.bin` parts and no `TargetMode="External"`. A rebuild changes only 08:
- old sha256 `8f05aee9…08be`
- new sha256 `2b8fb665b0c6dd14a753b6f2db6ba130496d66db46849a20e523f816dead2e5b`

`MANIFEST.md`, `S1-ROUTE-MAP.json` and the other kit files are unchanged.

## Own Calc check

Setup: LibreOffice 24.2.7.2 with an isolated ru-RU profile. Input is real typing (`.uno:EnterString`) into the delivered 08, then save as xlsx, reopen, and export to PDF.

Fixture: A 950 000 from 01.07, F 650 000; B 320 000 from 01.08, F 220 000; payments 20.07 300 000 (A) and 15.08 100 000 (B); rate 21 from 01.06 and 19 from 15.09; end 30.09.2026; B5 870 000.

| Case | Old 08 | New 08 |
|---|---|---|
| `21%` into B12 | 0,21, «21,00%», БЛОК «похоже на долю», ЗАБЛОКИРОВАН | 0,21, shown «0,21», same БЛОК, ЗАБЛОКИРОВАН |
| then `21` | 21, ГОТОВ 45 678,91 / 870 000,00, but **«2100,00%»** in Ввод B12, Расчёт G and По дням B | 21, ГОТОВ 45 678,91 / 870 000,00, «21,00» everywhere |
| saved, reopened, PDF | PDF contains «2100,00%» | no «2100»; prints «21,00» / «19,00» |
| B12 forced to a percent cell format (inherited or pasted format), typing `21` | — | the cell format really is percent (UNO `.String` «2100,00%»). **The PDF after reopen prints «21,00»**, Расчёт G «21,00», ГОТОВ 45 678,91 |
| normal `21`, then B13 `19,5` → `19` | 45 869,59 → 45 678,91 | 45 869,59 → 45 678,91 (identical) |
| mismatch H/L + 870 000 | ЗАБЛОКИРОВАН; row 13 10,00 mm < 19,47 mm optimal, overprints row 14 | ЗАБЛОКИРОВАН; full message with both sums (1 000 000,00 / 870 000,00) and the instruction; 22,23 mm ≥ 19,47 mm; «13 Периоды без начисления ок» prints below the message |
| missing reference (B5 empty) | ЗАБЛОКИРОВАН «не внесена» | ЗАБЛОКИРОВАН «не внесена» |
| every «Проверки» row with its longest message (`rows_check.py`) | — | all 17 rows: fixed ≥ Calc optimal (`rows-check-2b8fb665.txt`) |

- In the new 08, typing `21%` did not change the cell's format: it stayed `0.00##`, an observation in Calc only. The forced-percent row shows that the conditional format guards the display even when the cell's own format is percent.
- The financial result is unchanged: formulas are identical, Calc gives the same totals for old and new, and the author reference `r1_эталон` = 45 678,91.
- **Numeric paste: NOT VERIFIED.** Headless `.uno:Copy`/`.uno:Paste` had no effect, the same result as #376.
- **Excel: NOT VERIFIED.** That covers dxf numFmt rendering and Excel's automatic percent entry.

## Reusable gate (`tools/test_s1_candidate.py`, 2 tests)

- `test_печать_08_ставка_и_строки_проверок` (static):
  - a conditional format without «%» exists on Ввод B12:B71;
  - Расчёт G and По дням B are neither General nor «%»;
  - each «Проверки» row height is ≥ 13,3 pt × ⌈longest message / 100 chars⌉ + 2 pt. This is calibrated on the Calc measurements: 96 chars = 1 line, 131 = 2, 367 = 4.
- `test_libreoffice_печать_ставки_после_повторного_ввода` (Calc): the R-1 fixture with B12 in a `0.00%` cell format and value 21 is printed to PDF. The test requires ГОТОВ, 45 678,91, «21,00»/«19,00» and **no «2100»**.
- On the old 08, both tests **FAIL**: «нет условного формата…» and «печать ГОТОВОГО расчёта показывает ставку 2100%».

## Author test suite

- The final run is `author-tests-final2.log`: **60 «ок», 0 other lines**, exit 0. That is the 58 existing tests plus the 2 new ones, with the Calc layer running.
- Earlier runs (`author-tests.log`, `author-tests-final.log`) failed only on defects in my own new static test: the openpyxl `dxfId` lookup, then a too-strict 95-char calibration. No existing test failed in any run.
- The 58 existing tests therefore ran more than once, not exactly once.

## Disclosed, not changed

- «Ввод» column D («служ.», 2958465) and «Расчёт» K/L print «###» because the columns are narrow. This was already the case before the change (`print-reentry-reopened-old.txt`) and is outside F-1/F-2 scope.
- `21.00` typed in ru-RU is stored as text and gets the misleading «ставка вне 0–100» message (fail-safe, #376). Not changed.

## Handoff

Changed files: `tools/build_s1_candidate.py`, `tools/test_s1_candidate.py`, `tools/candidates/s1-oplata-za-raboty/08-raschet-procentov-395.xlsx`, this report, `tools/candidates/evidence/S1_PRINT_RATE/`.

Not done, for the coordinator: commit, Draft PR, independent acceptance. No merge, deploy, price or contact changes.
