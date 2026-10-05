# MB001 S1 literal — independent acceptance A-1 (run 426)

**Verdict: ACCEPT (A-1 only).** Not SALE_READY, not a legal opinion, not an assessment of the whole product. Native Excel was not measured.

## Identity

| Item | Expected | Actual | Source |
|---|---|---|---|
| Frozen source SHA (PR423) | f95cc76832234d0927b2300aee2bbb67cc9bd9f6 | f95cc76832234d0927b2300aee2bbb67cc9bd9f6 | `git rev-parse HEAD` in own worktree (observed) |
| Parent | — | 15f67a5186a7f835116634489c24f827dc8291f3 | `git show HEAD` (observed) |
| Mechanical closure head | f95cc76… | f95cc76832234d0927b2300aee2bbb67cc9bd9f6 | 02-proof.json `head` |
| Input hashes 00–05 | index.json sha256 | all 6 match | `sha256sum` (observed) |

Executor: anthropic/claude-opus-5.5, OpenRouter, one attempt, report-only. I did not repeat the Calc, fixture, rebuild or full-scan steps; those results come from the saved run-424 evidence and closure proof.

## Defect under review (from original run-421 report)

A-1, High: the new column-I block message in `04-uchet-raschetov-i-otpravok.xlsx` was a single 293-character string literal, used in 500 cells. Excel's documented limit for a text constant in a formula is 255 characters. Requested fix: split the literal with `&` or shorten it, add a gate that rejects literals over 255 in workbooks 02/04/08, and re-run scenarios B2 and L1c.

## Code delta assessment (observed: `git show --stat HEAD` + 04-source-delta.diff)

The commit touches 4 files: `tools/build_s1_candidate.py` (+2/−2), `tools/test_s1_candidate.py` (+27), the author's correction report, and the built `04-…xlsx`. No other buyer file is in the commit, which matches proof.json `other10buyer_plus_manifest_equal`.

- **Build change.** The diff only closes the literal after `…учитывается один раз, зачётом. ` with `"&` and reopens it at `"Если это отдельный платёж…`. The trailing space stays inside the first part, so the joined text is the same string. Nothing else in the `f04` formula changes: no condition, no function, no cell reference. This is the narrowest fix the original report asked for.
- **Gate.** `test_литералы_формул_совместимы_с_Excel` extracts `"…"` literals, handles doubled `""`, and measures length in UTF-16 code units. That is the same as the character count for Cyrillic text. It asserts the 255/256 boundary, the split case and the escape case. It then scans every worksheet `<f>` in the 02, 04 and 08 workbooks. The closure reports `literal_boundary_gate: PASS stdlib`. I did not rerun it.

## Evidence assessment

| Check | Evidence | Result |
|---|---|---|
| Old 04: literals over 255 | static.json `old04_scan`: 500 cells, length 293, column I only | defect reproduced |
| New 02/04/08: literals over 255 | 0 / 0 / 0; max 140 / 226 / 206 (226 with DV included, per scope contract) | PASS |
| Split is literal-only | `collapse`: 500 changed cells, sheet1 I5:I504, `collapse_recovers_all_original: true`, `literal_lists_equal: true` | PASS |
| No change outside the split | proof.json `xml_tree_equal_after_only_literal_collapse: true` | PASS |
| Other 10 buyer files + MANIFEST | proof.json: 11 sha256 entries equal | PASS |
| Narrow rebuild from source | proof.json `narrow_rebuild_equal: true` | PASS |
| B2 old vs new (Calc) | calc.json: same I message, M10–M12 blocked, M15 = 1, acts blocked, C3 «НЕ ГОТОВ»; `old_vs_new_identical_B2: true` | PASS (block kept) |
| L1c old vs new (Calc) | calc.json: I all «ок», M10 = 550000, M12 = 550000, M15 = 0, acts 550000/450000 «да», C3 «ГОТОВ»; `old_vs_new_identical_L1c: true` | PASS (no false block) |

**Flag in static.json `zip.members_differing_beyond_split`: classified as a measurement-instrument defect (false positive), not a product defect.** The raw-XML normalization looked for the joining sequence as `&quot;`. In the file, the formula ampersand is serialized as `&amp;`, so the split sites were never normalized. The parsed-tree comparison after collapsing the literals is the authoritative check, and it is equal (proof.json `previous_static_nonsplit_flag`). This explanation fits the code delta: the only change in the 04 sheet is the `"&"` insertion.

## Residuals (none block A-1)

1. **Native Excel not measured.** That Excel would show a repair dialog or drop the formulas for the old file is still a hypothesis; no one observed it. The 255 bound is enforced from documentation. Acceptance in Excel itself (and in a Russian locale) is still open.
2. **Gate coverage (Low).** The repo test scans only worksheet `<f>` cells. It does not scan data-validation, conditional-formatting or defined-name formulas. Run 424's independent scan did include DV (max 226), so no current violation exists. A future long DV literal would not be caught by the repo gate.
3. **Out of A-1 scope.** R1/R2 from run 421, the 08 workbook beyond the literal scan, outgoing documents, the legal review and the owner's Excel style versions. Financial 14 independent PASS is reused, not re-measured.
4. **Process (from 03-timeout-diagnosis).** Run 424 timed out without writing a report. In this run the checkpoint was written before any evidence was read.

## Coordinator reading

A-1 is closed at f95cc76832234d0927b2300aee2bbb67cc9bd9f6. The code delta is literal-only. Old and new produce the same calculation in B2 (block) and L1c (550000), and the repo now has a gate for this defect class. Next steps belong to the coordinator: exact-head/CI/findings gates, then permitted integration. Native Excel, owner Excel style integration and site copy remain separate dependencies. No publication, live price, SKU or payment action follows from this report.
