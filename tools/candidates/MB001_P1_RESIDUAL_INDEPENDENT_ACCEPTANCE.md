# MB001 P1 (R-1 manual transfer 04 → 08) — independent residual acceptance

**Verdict: ACCEPT** for the R-1 residual scope only. There are two non-blocking findings (F-1 print overlap, F-2 percent re-entry display) and one disclosed residual (T8). This is **not SALE_READY**. Excel, legal conclusions, L22/L23/L24 — **NOT VERIFIED**.

- Frozen SHA: `2d4b32122ef74628d06e3d7cbe5673e8d6c68f1b` (`git rev-parse HEAD`; tree clean apart from this report). Author PR #373, parent `9a133bb` (#360 R-1).
- Executor: anthropic/claude-opus-5.5 via OpenRouter, one attempt, no fallback. Fresh session; I did not read the author conversation or events. The author report was treated as a list of claims only.
- Input integrity: `sha256sum p1-inputs/*` matches `index.json` for all 8 entries (000…007; 006 and 007 are identical, `ca894d07…`).
- Run dir (scripts, profiles, PDFs, JSON): `…/corrections-20261005/acceptance/374/` — `acc.py` (own reference and UNO harness), `cmp_gen.py`, `result-p1.json`, `result-p5.json`, `print-*.pdf/txt`, `print-09/`, `gen-out/`, `author-tests.log`.

## Source review (diff HEAD~1..HEAD)

- `build_s1_candidate.py`: only `f08`/`f09` text and one new check. «Ввод» B5 (mandatory, 04 M12) and B6 (optional, ≥0). New «Проверки» row 13 «Сверка с бесспорной частью файла 04»: B5 not a number → БЛОК; <0 → БЛОК; B6 not a number or <0 → БЛОК; `ROUND(SUM(Акты!F5:F16)-(B5-N(B6)),2)<>0` → БЛОК.
- Cell-level diff of 08, parent vs HEAD (openpyxl, all sheets): «Оплаты», «Интервалы», «По дням» have 0 differences. «Расчёт» differs only in D2, which now points to `Проверки!C20`. «Проверки» rows 13–17 of the parent equal rows 14–18 of HEAD (shifted by one). The status formula is now `COUNTIF(C2:C18,"БЛОК*")`, so it includes the new row. Other changed cells are instruction text: «Как пользоваться» A3, «Акты» A2, «Ввод» A5:C6/A7. Rate, period, rounding and payment formulas are unchanged.
- The label pointer is correct: 04 «Взаиморасчёты» L12 = «БЕССПОРНАЯ ЧАСТЬ…» (M12), L10 = общий, L11 = спорная. In «Долг по актам», E/H/J/L/M headers match the 08 instructions.
- B6 ≥ 0 means B6 cannot hide an overstated column-F sum. Shown by T5 and T10.
- 08/09 zips have no `external*`/`vba*`/`.bin` parts and no `TargetMode="External"` rels.

## Generator reproduction

`python3 tools/build_s1_candidate.py --out <run>/gen-out`: all 12 kit files are byte-identical to the committed kit. That includes 00-START-HERE, MANIFEST and 04. `S1-ROUTE-MAP.json` is unchanged (`git status` clean). The commit changes only `08-raschet-procentov-395.xlsx` (`8f05aee9…08be`) and `09-pretenziya.docx` (`6f38de25…559d`) in the kit. No extra paths were needed, and START-HERE did not need to change: it only lists the files.

## P1 — own fixture, live Calc (UNO, isolated ru-RU profile `profile-ru-calc-p1`)

Own Python reference (`acc.ref`): day by day; a payment on day P reduces the debt from P+1; consecutive days with the same (debt, rate, year length) form one segment, rounded half-up to the kopeck; the total is summed per act. Values are typed into the **delivered** 08 (not an openpyxl copy) through the UNO cell API, then `calculateAll`. The #360 numbers come from the parent's accepted 04 table: J 950 000 / 320 000, M 650 000 / 220 000, H 1 000 000 / 400 000, L 700 000 / 300 000, M12 870 000, M10 1 000 000. Payments: 20.07 300 000 (A), 15.08 100 000 (B). Rates: 21 from 01.06, 19 from 15.09. End: 30.09.2026.

| Case | Expected | Actual (Calc) |
|---|---|---|
| T1 J/M, B5 870 000 | ГОТОВ, ref **45 678,91**, debt 870 000 | ГОТОВ, 45 678,91, 870 000,00, check «ок» |
| T2 H/L (both totals), B5 870 000 | БЛОК | ЗАБЛОКИРОВАН, «сверка … не сходится … 1 000 000,00 … 870 000,00» |
| T3 H/L, B5 empty | БЛОК (was ГОТОВ 51 019,17) | ЗАБЛОКИРОВАН, «не внесена бесспорная часть» |
| T4 J/M, B5 empty (missing reference) | БЛОК | ЗАБЛОКИРОВАН, «не внесена бесспорная часть» |
| T5 H/L, B5 870 000, B6 0 | БЛОК | ЗАБЛОКИРОВАН (does not match) |
| T6 J/M, B5 870 000,01 | БЛОК (kopeck) | ЗАБЛОКИРОВАН |
| T7 J/M, B5 as text «870 000,00» | БЛОК | ЗАБЛОКИРОВАН (message reads «не внесена», which is fail-safe) |
| T8 H/L, B5 = M10 1 000 000 | disclosed residual | **ГОТОВ, 51 019,17** — a third coordinated error, disclosed by the author; not closable without links to 04 |
| T9 only A, B5 870 000, B6 220 000 | ГОТОВ, ref A 37 287,68, debt 650 000 | ГОТОВ, 37 287,68, 650 000,00 |
| T10 J/M, B5 870 000, B6 −1 | БЛОК | ЗАБЛОКИРОВАН «число не меньше нуля» |
| T11 single-column error (F of B from L) | БЛОК | ЗАБЛОКИРОВАН |
| F1 fresh: 3 acts (X-17 512 345,67; Y-03 250 000,50; Z-9 99 999,99), same-day payment, rate 19,5; B5 = M12 700 000,49 | ГОТОВ, ref **56 106,11** | ГОТОВ, 56 106,11, 700 000,49 |
| F2 fresh, both totals copied (disputed 85 000,25), B5 700 000,49 | БЛОК (ref would be 63 273,44) | ЗАБЛОКИРОВАН «785 000,74 … 700 000,49» |
| F3 fresh, B5 empty | БЛОК | ЗАБЛОКИРОВАН |
| F4 fresh, B5 = M12 − 0,01 | БЛОК | ЗАБЛОКИРОВАН |

**P1: PASS.** The double total copy is rejected when 870 000 is entered, a missing reference blocks, and the correct transfer gives 870 000 / 45 678,91.

## Print (ru-RU Calc → PDF → pdftotext; Writer with a separate ru-RU profile)

- `print-T1`: «Ввод» B5 «870 000,00»; check 12 «ок»; «Статус ГОТОВ», «Проценты итого 45 678,91», «Долг … 870 000,00».
- `print-T2`: «ЗАБЛОКИРОВАН», «РАСЧЁТ НЕ ВЫПОЛНЕН — см. лист «Проверки»», «СТАТУС РАСЧЁТА ЗАБЛОКИРОВАН». `print-T4`: the «не внесена» message prints cleanly on 2 lines.
- **F-1 (non-blocking, new text):** the mismatch message wraps to 3 lines in the 110-wide column C, but row 13 has no height set. On the PDF (page 15, rendered `t2p15-15.png`) the third line («…долг вместе со спорной частью: в колонки D и F нужны только бесспорные суммы…») overprints «ок» of row 14 «Периоды без начисления». Status and both sums stay legible. Recommendation: set the row height or shorten the message.
- `print-09/09.txt` (4 pages): the new «Сверка перед отправкой: {{СУММА_ДОЛГА}} = … 08 … = «БЕССПОРНАЯ ЧАСТЬ» файла 04 … M12 … не «ок» — претензию не отправляйте» prints in full.

## P5 — percent typing / re-entry / paste (live Calc, `.uno:EnterString` on the selected cell, separate ru-RU profile `profile-ru-calc-p5`)

Rate cells and formulas are **unchanged** by #363, so this is pre-existing behaviour. I report observed cases only and make no universal claim.

| Typed into «Ввод» B12 | Stored | Check / status |
|---|---|---|
| `21` (General) | 21 | ок, ГОТОВ 45 678,91 |
| `21%` | 0,21, cell becomes percent format | «БЛОК: похоже на долю», ЗАБЛОКИРОВАН |
| `21` re-typed after `21%` | 21, **displayed «2100,00%»** | ок, ГОТОВ 45 678,91 (calculation correct) |
| `0,21` | 0,21 | БЛОК «похоже на долю» |
| `21 %` | 0,21 | БЛОК |
| `21,00` (into percent-formatted cell) | 21 → «2100,00%» | ок, ГОТОВ |
| `21.00` (ru-RU) | text | «БЛОК: ставка вне 0–100» (fail-safe, misleading wording) |
| B13 `19,5` then `19` | 19,5 / 19 | ок; 45 869,59 / 45 678,91 |
| B5 `870000`, `870 000,00`, `870000,00` | 870 000 | ГОТОВ |
| B5 `1000000` | 1 000 000 | ЗАБЛОКИРОВАН |

- **F-2 (non-blocking for R-1, pre-existing):** after a blocked `21%`, re-typing `21` computes correctly. But the percent format stays: `print-P5-reentry.txt` shows «2100,00%» on «Ввод» and in the «Ставка, %» column of «Расчёт», with status ГОТОВ and no warning. That calculation is meant to be attached to the claim. Recommended as a separate scope: a fixed number format or normalisation for B12:B71.
- **Paste: NOT VERIFIED.** Headless `.uno:Copy`/`.uno:Paste` had no effect: the value stayed at the previously typed 21. Clipboard paste was not proven.
- Excel's automatic percent entry (typing `21` into a %-formatted cell may store 0,21) — **NOT VERIFIED**.

## Author test suite (supplementary, not independent evidence)

I ran `python3 tools/test_s1_candidate.py` once at the frozen SHA: **58 «ок», 0 other lines** (`author-tests.log`; the Calc layer ran). That is 55 existing tests plus 3 new ones. The worktree stayed clean apart from this report. This run confirms nothing beyond the P1/P5 evidence above.

## Commands (run dir = `…/acceptance/374`)

`sha256sum p1-inputs/*` · `python3 tools/build_s1_candidate.py --out <run>/gen-out` · `python3 <run>/cmp_gen.py` · `python3 <run>/acc.py p1` · `python3 <run>/acc.py p5` · Writer: `soffice -env:UserInstallation=<run>/profile-ru-writer-09 --headless --convert-to pdf 09-pretenziya.docx` · `pdftotext -layout` · `pdftoppm -f 15 -l 15` · `python3 tools/test_s1_candidate.py`. LibreOffice 24.2.7.2. Profiles: `registrymodifications.xcu` with ooLocale and ooSetupSystemLocale = ru-RU.

## Remaining gates

- T8 (both totals plus B5 = M10) remains ГОТОВ 51 019,17. The author disclosed it; it needs a third coordinated error against the labels. The coordinator should decide whether this is acceptable.
- B6 is taken on trust: an understatement is possible, an overstatement is not.
- F-1 print overlap; F-2 percent display — separate fixes, not done here.
- `calc_edges.py`/`run_checks.py` were not run by me. Excel, legal, L22/L23/L24 — NOT VERIFIED. Exact-head CI must be read by the coordinator. No merge, deploy, price or contacts.
