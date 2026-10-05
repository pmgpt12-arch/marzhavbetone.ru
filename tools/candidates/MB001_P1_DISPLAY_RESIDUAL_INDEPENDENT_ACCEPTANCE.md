# MB001 P1 display residual (F-1/F-2): independent acceptance

**Verdict: ACCEPT** for the F-1/F-2 residual scope only. There is one disclosed, non-blocking residual (R-1: paste with formatting). This is **not SALE_READY**. Excel, legal conclusions, on-screen rendering — **NOT VERIFIED**.

- Frozen SHA: `cd3307f5703ca72964d88d935d1fefac0b50d13e` (`git rev-parse HEAD`, worktree clean). Parent `01100bd` is the PR #376 merge (report only). PR #384 head SHA was not checked: `gh` needed approval.
- Scope: F-1 and F-2 from `tools/candidates/MB001_P1_RESIDUAL_INDEPENDENT_ACCEPTANCE.md:70` and the lines around it. Nothing else.
- Input integrity: all 8 files in `p1-display-inputs/` match the sha256 values in `index.json`. 006 and 007 are the same file (`ca894d07…`), as the index says.
- Run directory: `/home/denis/.local/state/claude-dispatcher/recovery-20261004/p1-display-20261005/acceptance/385/`
  - Scripts: `run_calc.py`, `f1_geom.py`, `ref395.py`
  - Outputs: `out-new/`, `out-old/`, `out-new2/`, `out-old2/` (xlsx, PDF, pdftotext, `results.json`)
  - `old-08.xlsx` = `git show 01100bd:tools/candidates/s1-oplata-za-raboty/08-raschet-procentov-395.xlsx`

## Source read

The change is in `tools/build_s1_candidate.py` (`f08`):

1. **Fixed rate format.** New constant `RATE = "0.00##"` (no «%»). It is set on:
   - «Ввод» B12:B71
   - «По дням» B (the day-by-day rate)
   - «Расчёт» G («Ставка, %»)
2. **Conditional format on «Ввод» B12:B71.** Rule `ISNUMBER(B12)` with a dxf number format `0.00##`. The idea: the rate prints without «%» even if the cell's own format later becomes percent.
3. **F-1 row heights.** `fit_height(pv, i, самое_длинное(f), 3, 3)` for each «Проверки» row. `самое_длинное` takes the longest message a formula can produce: string literals joined with `&…&`, with each number replaced by `999 999 999,99`.

Tests: two new tests in `tools/test_s1_candidate.py`:
- A static test: the conditional format exists, the downstream rate cells do not use General or «%», and row heights fit at 100 characters per line, about 13.3 pt per line.
- A LibreOffice PDF test: openpyxl sets B12 to `0.00%`, then the test checks for no «2100» and that 21,00 and 19,00 are printed.

Only `08-raschet-procentov-395.xlsx` changed among delivered files (`git show --stat HEAD`). No macros or external links were added.

**Root cause class**, confirmed against the old workbook:
- F-2 is inherited format. Typing «21%» gives B12 the cell format `0,00%`. Re-typing «21» keeps that format, and the General-format formula cells «По дням» B and «Расчёт» G inherit it. Result: «2100,00%» appears 79 times in the old PDF.
- F-1 is display only. The row height was not set. Calc sizes rows at load time, when the cached result is short, and does not resize them after recalculation in the same session.

## No financial regression

- **Formulas/values unchanged.** An openpyxl comparison of every cell value and formula on all 8 sheets, old vs new: 72,718 cells, **0 differences**, same sheet list. So the min/threshold checks, B5/B6 reconciliation, payment, day and rounding rules are textually identical. Only formats, conditional formatting and row heights changed.
- **Own reference** (`ref395.py`, independent day loop): 365-day year, payment day still at the old debt, rounding per period. Result **45 678,91**. That matches Calc old and new, in-session and after reopen. The other payment-day convention would give 45 448,77, so the fixture does test that rule.

## Calc cases (own)

Setup:
- LibreOffice 24.2.7.2, headless, an isolated profile per run with `ooSetupSystemLocale`/`ooLocale = ru-RU`. Proof that ru-RU parsing was active: «19,5» became the number 19.5, and «19.5» stayed text.
- Base fixture filled through UNO:
  - acts A 950 000 from 01.07.2026 and B 320 000 from 01.08.2026; «Акты» F 650 000 / 220 000
  - payments 20.07 300 000 (A) and 15.08 100 000 (B)
  - last day 30.09.2026; A12 = 01.06.2026, A13 = 15.09.2026; B5 = 870 000
- Rates were **typed through the real Calc input path**: `.uno:GoToCell` + `.uno:EnterString`, the same as typing and pressing Enter.
- Each case was saved as xlsx, closed, reopened, recalculated and exported to PDF, then run through `pdftotext`. In-session PDFs (before saving) were also exported for the key cases.

| Case (typed sequence) | Expected | New (cd3307f) actual | Old (01100bd) actual |
|---|---|---|---|
| normal: B12 «21», B13 «19» | ГОТОВ 45 678,91, prints 21,00/19,00 | ГОТОВ 45 678,91; PDF «21,00 ок», «19,00 ок»; no «2100» | ГОТОВ, prints «21» |
| B12 «21%» (intermediate) | blocked | 0,21, «БЛОК: похоже на долю — введите проценты», ЗАБЛОКИРОВАН | 21,00%, blocked |
| «21%» → «19» → B12 «21», reopened | ГОТОВ 45 678,91, no 2100 | ГОТОВ 45 678,91; B12 «21,00»; Расчёт G7 «21,00»; PDF 0 × «2100», in-session and reopened | **ГОТОВ with «2100,00%»** on Ввод and Расчёт (F-2 reproduced) |
| «21%» only | blocked | ЗАБЛОКИРОВАН, prints «0,21 БЛОК…» | blocked |
| B13 «19,5» → «19» | ГОТОВ 45 678,91 | intermediate value 19,5; final ГОТОВ 45 678,91, «19,00» | ГОТОВ |
| B13 «19.5» (text in ru-RU) → «19» | blocked, then ГОТОВ | intermediate «БЛОК: ставка вне 0–100»; final ГОТОВ 45 678,91 | ГОТОВ |
| B12 cell format forced to `0,00%` (API), then «21» | no 2100 in print | cell's own format stays `0,00%`, but **PDF prints «21,00»** (the conditional format wins); ГОТОВ 45 678,91 | prints 2100,00% |
| forced `0,00%`, «21%» → «21» | no 2100 | PDF «21,00», 0 × «2100» | 2100,00% |
| paste special, values only (`InsertContents` SVD), from a `0,00%` cell with value 21 | no 2100 | «21,00», ГОТОВ 45 678,91 | «21» |
| full paste (`.uno:Paste`) from a General cell with value 21 | no 2100 | «21» (General came with the paste), Расчёт «21,00», ГОТОВ | «21» |
| full paste from a `0,00%` cell with value 21 (it shows 2100,00%) | — | **Ввод prints «2100,00%»**, ГОТОВ 45 678,91; Расчёт G and По дням print «21,00». See R-1 | 2100,00% everywhere |
| mismatch: B5 = 860 000 | blocked, full message | ЗАБЛОКИРОВАН; message has both sums (870 000,00 / 860 000,00) and the instruction (…«колонки J и M») | blocked |
| mismatch after «21%» → «21» | blocked | ЗАБЛОКИРОВАН, same full message, no 2100 | blocked, prints 2100,00% |
| missing reference: B5 empty | blocked | ЗАБЛОКИРОВАН, «БЛОК: на листе «Ввод» не внесена бесспорная часть…» | blocked |

In this LO version, the base format `0.00##` alone already stops the percent auto-format on «21%»: the cell format stays `0,00##`. The task said not to rely on that, so the forced-percent cases were run separately. They show that the conditional format still makes the print show 21,00 when the cell's own format is percent. After save and reopen as xlsx, the conditional format still applied (forced cases above).

## F-1 geometry (own gate, `f1_geom.py`)

This uses `pdftotext -bbox` on the «Проверки» page (p. 35):
- It finds the bottom of the last line of the row-13 message and the top of the row-14 label «Периоды без начисления».
- It rebuilds the row-13 text and checks for both sums and the instruction.

| PDF | row-13 lines | bottom of row 13 vs top of row 14 | content |
|---|---|---|---|
| old, in-session | 3 | 238,0 vs 228,9 → **OVERLAP** (−9,0 pt) | full text, but the 3rd line is on the row-14 line |
| old, saved/reopened | 3 | gap 11,1 (Calc sized the row on reload, which hid the defect) | full |
| new, in-session | 3 | gap **16,9 pt** | both sums + instruction |
| new, saved/reopened | 3 | gap **16,9 pt** | both sums + instruction |

So F-1 shows only in the realistic path: open the delivered file, enter data, print. That path reproduces it on the old file and passes on the new one. Row 13 now has height 63, that is 4 lines.

## Gates

- **Author gates** (statically reviewed, not run here): they catch a downstream rate cell with General or «%», a missing conditional format, and a «Проверки» row lower than its longest message. Against the old file, the row-height and format checks would fail (heights None; General on Расчёт G). That is meaningful and needs no framework. The 58 author tests were **not run** in this session: they are not independent evidence, and there was a time budget.
- **Own reusable gate candidates:** «no "2100" in the PDF of a READY fixture after typing «21%» → «21»» (`run_calc.py`) and the bbox overlap check (`f1_geom.py`). Both separate old (fail) from new (pass).

## Findings / residuals

- **R-1 (non-blocking, disclosed):** a full paste (Ctrl+V with formatting) of a source cell with value 21 in percent format replaces both B12's format and its conditional format. «Ввод» then prints «2100,00%» while the status is ГОТОВ. The calculation stays right: 45 678,91, and Расчёт/По дням print 21,00. The source cell itself showed «2100,00%», so this is user-supplied formatting, not the workbook's own input sequence. The typed entry/re-entry path that F-2 is about is closed. The coordinator decides whether paste-with-format needs a separate scope.
- The API `getString()` of a forced-percent B12 returns «2100,00%» because UNO ignores conditional formatting. Only PDF output is verified; **on-screen display is NOT VERIFIED**.
- «###» in the PDF rate rows of «Ввод» (to the right of «ок») is in old and new. It is pre-existing and outside this scope; not investigated.
- **NOT VERIFIED:** Excel (no Excel available; Excel may apply the percent format on «21%» whatever the base format, so there only the conditional format would protect), legal conclusions, PR #384 head SHA, regeneration of the 08 file from the generator (not rebuilt here).

## Commands (run directory)

```
sha256sum p1-display-inputs/*
git show HEAD -- tools/build_s1_candidate.py tools/test_s1_candidate.py
git show 01100bd:tools/candidates/s1-oplata-za-raboty/08-raschet-procentov-395.xlsx > old-08.xlsx
python3 run_calc.py <new 08.xlsx> new ; python3 run_calc.py old-08.xlsx old
python3 run_calc.py <new 08.xlsx> new2 mismatch,pct_then_21,normal,missing_ref   # + in-session PDFs
python3 run_calc.py old-08.xlsx old2 mismatch,pct_then_21,normal,missing_ref
python3 f1_geom.py out-{old2,new2}/mismatch-session.pdf ; python3 f1_geom.py out-{old,new}/mismatch.pdf
python3 ref395.py
```

Next: the coordinator reads this report and the exact-head CI before any authorized merge. No merge, deploy, sale or publication was done.
