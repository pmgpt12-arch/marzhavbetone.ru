# MB001 P5 residual — independent acceptance (#370 → author PR #369)

**Verdict for the residual scope: ACCEPT** (only for the residual: silent ×100 wrong rate on percent input in the 04 rate column, LibreOffice Calc 24.2.7.2 ru-RU).
This is not `SALE_READY`. Excel: `NOT VERIFIED`. Legal: `NOT VERIFIED`. Real GUI keystrokes and the external OS clipboard: `NOT VERIFIED` (see §6).

- Frozen SHA: `7c202189d27f3ec05a0b8ae55364ccc0a06002f1` (`git rev-parse HEAD` in the assigned worktree, clean tree)
- Parent for the baseline: `12f98eb`
- Executor: one session, anthropic/claude-opus-5.5. No other model calls, no fallback, nothing installed.
- Evidence directory (temporary, outside the repo): `/home/denis/.local/state/claude-dispatcher/recovery-20261004/corrections-20261005/acceptance/370/work/`

## 1. Input integrity

| Input | sha256 (computed) | Matches index.json |
|---|---|---|
| 000-000-previous-independent-acceptance.md | `80c460c05874a28d6f933e2850c28b25940cac56c23664a91667da58e6ea3caa` | yes |
| 001-001-current-owner291.md | `ca894d07f31e523e645a23a1bfc2fec32336bd1d091fb4d0d3851b30893fb06f` | yes |
| 002-current-owner291.md | `ca894d07f31e523e645a23a1bfc2fec32336bd1d091fb4d0d3851b30893fb06f` | yes |
| index.json | `45981de15475ce5b265de7f755ac94fb0931306f4945041a795042e524370c5f` (listed for the record) | — |

Files changed in `7c20218` compared with the parent (`git diff --name-status HEAD~1 HEAD`): `04-raschet-ubytkov.xlsx` (M), `build_paid_07.py` (M), `tools/test_p5_calc_results.py` (M), the author report and `evidence/P5_PERCENT_INPUT/*` (A). Of the products, only 04 changed. 05 and the other kit files were not touched by the commit.

## 2. Source change (read independently)

`products-storage/build_paid_07.py`, `build_raschet_04`:
- The F rate column in both period tables (rows 18–22 and 27–31) is now formatted `@` (text). Before, it was `ФОРМАТ_СТАВКИ`.
- The rate comes from text through `NUMBERVALUE(SUBSTITUTE×4(F; " ", "%", "'", "." → ","); ","; " ")`. The `%` sign is removed, so "1%" and "1" both mean 1 (% per day or % per year, per the column header).
- The new branches in H «Проверка», in order: `ISNUMBER(F)` gives «Ставка вставлена числом — не видно, был ли знак %. Наберите её заново с апострофом впереди…». Not text, an empty normalized value or `ISERROR(NUMBERVALUE)` gives «Ставка не распознана…». After that come the old checks for dates, negatives and thresholds, now against the normalized value. The thresholds are still the declared `0.01` per day and `1` per year; no new thresholds were added.
- A row with an H message gives no amount in G, and the section total is not calculated (existing mechanism).
- A2 was rewritten: type the rate on the keyboard; the cell is text; "0,05 and 0,05%" are equivalent; if the cell holds a number (pasted or a formula), the row is not calculated, so retype the rate with a leading apostrophe; the minimum rates are unchanged; the fine percent in 2.2 is a number without % (instruction text only — the G14 formula is not in the diff).
- The rule is not based on magnitude: a number in F is blocked at any value (0,01 / 0,1 / 0,17 / 7,5 — see §4). There are no `CELL("format")` checks and no portability claims (grep of the generator and the author report).

## 3. Isolated rebuild (own script)

`rebuild_own.py` copies the generator from the frozen SHA into a temporary directory, stubs reportlab, and calls `build_paid_07()`:
- `04-raschet-ubytkov.xlsx` is **BYTE_EQUAL** to the repo copy (`367f2422…`).
- `05-reestr-uderzhaniy.xlsx` is **BYTE_EQUAL** (`ba9bbf6a…`).
- The docx/06 files from the temporary build differ by bytes (the generator is not deterministic for them). That does not matter here: the commit does not change them in the repo (§1).

## 4. Own Calc tests (ru-RU, separate profiles, own data)

Environment: LibreOffice 24.2.7.2. Each run uses a new `-env:UserInstallation` with `ooSetupSystemLocale=ooLocale=ru-RU` (prof-a: typing; prof-c: paste and saving; prof-b/prof-d: reload of the saved xlsx and PDF; prof-e: parent baseline). Locale probe: `0,5` → VALUE 0.5, `01.03.2026` → date 46082.

Input goes through `.uno:GoToCell` + `.uno:EnterString` (the `ScViewFunc::EnterData` path, which respects the cell format and is the same path a recorded macro uses for typed input). Paste uses `.uno:Copy` in a separate source workbook and then `.uno:Paste` / `.uno:InsertContents` (values only) / `.uno:PasteUnformatted` in the target, into an **empty** original `@` cell, with a fresh document for each case.

Own data: penalty 01.03.2026–30.03.2026 (30 days), base 387 500 (base × days = 11 625 000). Art. 395 interest 01.01.2026–10.04.2026 (100 days), base 1 150 000.

### 4.0 Baseline: parent `12f98eb` (the defect reproduced)
| Typed F18 / F27 | G18 | H18 | G27 | H27 |
|---|---|---|---|---|
| `1%` / `17%` | **1 162,50 (silent, wrong)** | empty | empty | threshold message |
| `0,05%` / `7,5%` | empty | threshold message | empty | threshold message |
| `0,1` / `17` | 11 625,00 | empty | 53 561,64 | empty |

### 4.1 Typing on the candidate (typed percent strings normalize correctly)
| Typed into F18 (daily) | Stored | Expected | Actual G18 / total G23 | H18 |
|---|---|---|---|---|
| `0,1` | TEXT | 11 625,00 | 11 625,00 / 11 625,00 | — |
| `0,05` | TEXT | 5 812,50 | 5 812,50 / 5 812,50 | — |
| `0,05%` | TEXT | 5 812,50 | 5 812,50 | — |
| `1%` | TEXT | 116 250,00 | **116 250,00** | — |
| `1` | TEXT | 116 250,00 | 116 250,00 | — |
| `0,1%` / `0.1` / `'0,1` | TEXT | 11 625,00 | 11 625,00 (each) | — |
| `0` / `0%` | TEXT | 0, valid | 0,00 / total 0,00 | — |
| `0,005` / `0,005%` | TEXT | block (threshold) | empty, total empty | «Ставка меньше 0,01 % в день…» |
| `abc` / `1,5%x` / `=1%` / `=0,1+0` | TEXT | block | empty | «Ставка не распознана…» |
| `-0,1` | TEXT | block | empty | «…меньше нуля…» |

| Typed into F27 (annual) | Expected | Actual G27 / G32 | H27 |
|---|---|---|---|
| `17` / `17%` | 53 561,64 | 53 561,64 | — |
| `7,5` / `7,5%` / `7.5%` | 23 630,14 | 23 630,14 | — |
| `0` | 0, valid | 0,00 | — |
| `0,5` / `0,5%` | block | empty | «Ставка меньше 1 % годовых…» |

### 4.2 A number in F (lexical information lost) is blocked at any value
| Case | F stored | G / total | H |
|---|---|---|---|
| API `setValue(0.01)` / `(0.1)` in F18; `(0.17)` in F27 | VALUE | empty / empty | «Ставка вставлена числом…» |
| `.uno:Paste` of a numeric `1,00%` cell → F18 | VALUE 0.01, format `0,00%` | empty / empty | «Ставка вставлена числом…» |
| `.uno:Paste` of a numeric `0,1` cell (General) → F18 | VALUE 0.1 | empty | same |
| `.uno:Paste` of a numeric `17,00%` → F27 | VALUE 0.17 | empty | same |
| Paste special, values only, `1,00%` → F18; `17,00%` → F27 | VALUE 0.01 / 0.17, format `@` kept | empty | same |

### 4.3 Re-entry after the format changes (percent → number)
| Case | F stored | Result |
|---|---|---|
| Text `1%` in F, then format changed to Percent (no retyping) | TEXT `1%` | 116 250,00 (correct) |
| Percent format, retype `1%` | VALUE 0.01 | blocked «вставлена числом» |
| Percent format, retype `0,05%` | VALUE 0.0005 | blocked |
| General format, retype `0,1` | VALUE 0.1 | blocked |
| General, retype `1%` | VALUE 0.01 | blocked |
| Percent format, retype `7,5` (first run) | VALUE 7.5 shown as 750,00% | blocked |
| Retype following the A2 protocol `'1%` / `'0,05` / `'17%` | TEXT | 116 250,00 / 5 812,50 / 53 561,64 |
| Annual: General, retype `17%` | VALUE 0.17 | blocked |

### 4.4 Pasted text (unformatted / text cell)
| Case | F stored | Result |
|---|---|---|
| Paste of a text cell `1%` → F18 | TEXT `1%` | 116 250,00 |
| Paste of a text cell `0,05%` → F18 | TEXT | 5 812,50 |
| `PasteUnformatted` of a numeric `1,00%` cell | TEXT `1,00%` | 116 250,00 (the visible `%` is kept, so correct) |
| `PasteUnformatted` of a numeric `17,00%` | TEXT `17,00%` | 53 561,64 |
| `PasteUnformatted` of a numeric `0,1` (General) | TEXT `0,1` | 11 625,00 (the visible text is read as 0,1 % per day, matching the header) |

### 4.5 Saving, reloading in another profile, PDF
- S1c-positive.xlsx (typed `1%` and `17%`), saved in prof-c and reloaded in prof-d with a full recalculation: F18 TEXT `1%`, G18 = G23 = G41 = **116 250,00**; F27 TEXT `17%`, G27 = G32 = G42 = **53 561,64**. No H messages.
- S2c-negative.xlsx (real `.uno:Paste` of a numeric 1% into F18, typed `7,5` into F27), reloaded: F18 VALUE 0.01, G18/G23/G41 empty, H18 «Ставка вставлена числом…», H23 «Итог не считается…», H41 «Ошибка ввода — см. раздел 2». The 395 table computes independently: 23 630,14.
- The PDFs (calc_pdf_Export from prof-d) are each 1 page. pdftotext: A2 prints in full in all three (blank, S1c, S2c), including «набирайте с клавиатуры… наберите ставку заново с апострофом впереди: '0,05». In S2c the full H18 message prints («…Наберите её заново с апострофом впереди: '0,1 или '0,1%») and «Итог не считается…». In S1c 116 250,00 and 53 561,64 print.

### 4.6 Author tests (one run after the final change, not independent evidence)
`python3 -B -m pytest -q -p no:cacheprovider tools/test_p5_calc_results.py` → **19 passed in 17.04s**. The brief says 18; pytest collected 19 on this SHA.

## 5. Evidence files (sha256)
| File | sha256 |
|---|---|
| work/rebuild_own.py | `66346578…553a` |
| work/calc_own_lib.py | `c7ef4ec8…8208` |
| work/calc_own.py → results.json | `2e67a453…aa3` → `140bfb45…7ba5` |
| work/calc_paste.py → results_paste.json | `2b7d773c…eb` → `d1cb6239…1616` |
| work/calc_parent.py → results_parent.json | `752a8859…7347` → `53f0f8e0…49d6` |
| work/pdf_check.py → pdf_check.json | `ae32c8c7…19da` → `1432206c…8106` |
| S1c-positive.xlsx / .pdf | `79680639…7b12` / `3fe56da6…7e20f` |
| S2c-negative.xlsx / .pdf | `775135fd…9e37` / `a76a1293…cb0` |
| S0-blank.pdf | `8aade2c7…1649f` |

Notes on the harness (they do not change the conclusions): in the first run (calc_own.py) the reset to a text format used the wrong key (100 instead of `NumberFormat.TEXT`=256), and `.uno:Paste` over a non-empty cell did nothing in headless mode (the overwrite confirmation is cancelled). Those paste results are not used. They were rerun in calc_paste.py with a fresh document and an empty original `@` cell. S1/S2 from the first run are also not used (the cells were reformatted by earlier cases); S1c/S2c replace them.

## 6. Limits and remaining gates
1. **Real keystrokes / AutoInput / AutoCorrect: NOT VERIFIED.** EnterString does not go through Calc's interactive AutoInput. Since F is a text column shared by both tables, AutoInput could suggest a value already present in the column (for example `17%` while `1` is being typed). Whether that is possible was not checked.
2. **External OS clipboard (another application, browser, Excel): NOT VERIFIED.** The in-process LibreOffice clipboard between two documents was used. `PasteUnformatted` is the closest model of a text paste.
3. **Ambiguity outside the residual.** A pasted text fraction with no `%` (for example the visible `0,01` from a General cell that meant 1%) is read as 0,01 % per day and computes 1 162,50 with no message. The workbook cannot recover lexical information that was never visible. A2 tells the buyer to type the rate and that the value is "% per day" per the header, but it does not mention text paste specifically. This is not the #357 case (typed `1%` now gives 116 250,00). Flagged for the coordinator; not a reason for CORRECTION within this scope.
4. Not tested: scientific notation (`1e-1`), several separators (`1.000,5` → blocked by design, not run), other locales, other Calc versions.
5. Excel (NUMBERVALUE, text cells, the `_xlfn.` prefix): **NOT VERIFIED**. Legal correctness of the thresholds and formulas: **NOT VERIFIED**.
6. The P1 passport fixture (870000/45678.91) is outside this P5 scope: N/A.
7. Next: the coordinator reads this report and the exact-head CI before an authorized merge. No merge, deploy, price, SKU, payment or contact actions were taken. Product and candidate files were not changed; the only repo artifact is this report.
