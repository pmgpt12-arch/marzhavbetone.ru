# MB001 P5 native guard corrections — independent recheck (#455)

Date: 2026-10-05. Reviewer: anthropic/claude-opus-5.5 (OpenRouter). One attempt, no fallback, no blind retry.
Exact source: `4a2dd35e185a3478d4fc16fcfca2d67dc4be6549`, in an isolated worktree that was clean at start. It was reviewed against the original independently reviewed `218c4f8705f9ea2e805b7197f2f4463432686545` (#452 CHANGES_REQUESTED).
Scope: only the source/native guard corrections and the template relocation. Not whole-P5 finance/legal, not currentness, not public release, not SALE_READY. The owner's cosmetic approval, the 19 Calc checks and the formats were not re-reviewed (by instruction).

## Verdict: ACCEPT (narrow, source/native guard only)

Both #452 findings are fixed.
1. Sheet-scoped names are now compared per sheet. Local-name drift is rejected before the output is touched. Workbook names and local names that are legitimately present in the native file are preserved.
2. The atomic write is wrapped in `try/finally` with `unlink(missing_ok=True)`. A failed write or a failed replace keeps the old output and leaves no `*.approved.tmp`.

The accepted owner bytes are unchanged. The actual generator still publishes exactly the native bytes. The template relocation keeps `tools/templates` out of the product inventory.

## Inputs
- HEAD is `4a2dd35e…`, and `git status` was clean at start.
- All 6 entries in the immutable index match by sha256. The 5 repo files at HEAD equal their indexed local copies: `build_paid_07.py` `11b89cdd…`, `test_p5_owner_native.py` `7c1cea52…`, the correction report `864a3c32…`, template 04 `20165a12…` and template 05 `db0d99f7…`. Prior #452 was read from the index copy.
- The diff from `218c4f8` to HEAD has 2 commits.
  - `e3210eb` makes a byte-identical R100 rename of `products-storage/templates/p5-owner-excel/*` to `tools/templates/p5-owner-excel/*`, changes the locator by 1 line, and adds candidate/evidence docs.
  - `4a2dd35` adds +7/−2 lines to `build_paid_07.py`, +30 lines to the tests, and adds the correction report.
- No product package files changed after 218c. Buyer 04/05 stay at the owner SHAs, which the test checks.

## Code inspection (`products-storage/build_paid_07.py:71-104`)
- New per-sheet check: inside the sheet loop, `{k: v.attr_text}` of `actual.defined_names` is compared with the approved sheet's names, before the DV checks and before any write. This fixes #452 item 1.
- In openpyxl 3.1.2 (observed), `_xlnm.Print_Area`/`Print_Titles` load into `ws.print_area`/`print_titles`, not into `ws.defined_names`. Print layout therefore stays owner-only by design, which is consistent with #452.
- The existing workbook-level comparison is kept. Together the two comparisons detect a name moving between workbook and sheet scope in either direction.
- `try: write_bytes; replace; finally: unlink(missing_ok=True)`. On success the temp file has already been renamed, so the unlink does nothing. On any exception, including a `BaseException`, the temp file is removed and the old output is never touched, because `replace` is the only operation that mutates the output. This fixes #452 item 2.
- `P5_OWNER_TEMPLATES = Path(BASE_DIR).parent / "tools" / "templates" / "p5-owner-excel"` is resolved once at import. Monkeypatching `BASE_DIR` later, as the tests do, does not move it.

## Checks I ran
| Check | Observed |
|---|---|
| `python3 -B -m pytest tools/test_p5_owner_native.py -q -p no:cacheprovider` | **16 passed in 0.56s** |
| Unmodified `python3 -B tools/check_packages.py` | Final line: `Комплектов: 30, с расхождениями: 0 … расхождений в неадресуемых папках (к сведению): 6`. No `templates` package or `НЕТ МАНИФЕСТА` message. Only the existing informational historical-archive notes. |
| `ls products-storage/templates` | Does not exist. `git ls-files tools/templates/p5-owner-excel` lists 04, 05 and README. |
| Actual `build_paid_07()` into a temp BASE_DIR (PDF stubbed, `Workbook.save` spied) | 04 is `20165a12…` and 05 is `db0d99f7…`, both byte-equal to the templates. openpyxl `Workbook.save` was never called for 04/05 (1 save in total, the 06 path). No `*.tmp` left behind. |
| `git diff --check 218c4f8 HEAD` | One finding: `MB001_P5_NATIVE_GUARD_CORRECTION_2026-10-05.md:7: new blank line at EOF`. Cosmetic, in a docs file only. Not in source. |

### Own negative probes (`/tmp/p5_455/probes.py`; output pre-seeded with `PREV` unless noted)
Pinned templates: both books have one sheet each. There are no workbook names and no non-reserved local names; only the Print_Area is local.

| Probe | Result | Output | tmp |
|---|---|---|---|
| 05 sheet-local `localname` (the test covers only 04) | sheet-defined-name mismatch | unchanged | none |
| 04 sheet-local Cyrillic range `Итог` `$F$18:$F$19` | sheet-defined-name mismatch | unchanged | none |
| 04 sheet-local constant `k=0.13` | sheet-defined-name mismatch | unchanged | none |
| 04 workbook-level name added | defined-name mismatch | unchanged | none |
| 04 baseline / 05 baseline with no prior output | PASS | native bytes | none |
| 04 print_area-only change | PASS, by design: owner-owned and not taken from the generator | native bytes | none |
| **Re-pinned template with local `loc`**: generated has the same local name | PASS; the output `workbook.xml` keeps `<definedName name="loc" localSheetId="0">` plus Print_Area | native | none |
| … generated drops it / uses a different ref / moves it to workbook scope | sheet-defined-name mismatch (all 3) | unchanged | none |
| **Re-pinned template with workbook `loc`**: generated has the same name | PASS; output keeps `<definedName name="loc">` (no localSheetId) | native | none |
| … generated moves it to sheet scope | sheet-defined-name mismatch | unchanged | none |
| … generated drops it / uses a different ref | defined-name mismatch | unchanged | none |
| Real FS: output path is a non-empty directory, so `replace` fails | IsADirectoryError | directory content intact | none |
| Real FS: output directory is read-only, so the temp file cannot be created | PermissionError | unchanged | none |
| Stale `.approved.tmp` before a valid run | PASS; consumed | native | none |
| `BaseException` raised in `replace` on the temp file | propagates | unchanged | none |

The tests cover a partial `write_bytes` and a `replace` OSError through a `Path` monkeypatch. My real-filesystem failures and the `BaseException` case go beyond that mirroring.

## Prior review claims
- #452 item 1 (local name silently dropped): **resolved**. Confirmed for both books, all three name kinds, and scope swaps.
- #452 item 2 (temp file left after a replace error): **resolved**. Also true for write failures and non-`Exception` interrupts.
- #452 positive claims (exact native bytes, no openpyxl save of 04/05, other guards stop before any write): **still hold** at 4a2dd35, per the generator run and the baseline probes.
- The author's claim "16 passed in 0.55s" matches my run (0.56s).
- The author's CI/public evidence (`run_checks --class public` 39/39) is **attributed and not rerun**. I ran only `check_packages`.

## Non-blocking notes
- The blank line at EOF in the correction report trips `git diff --check`. Trim it if CI enforces this.
- `MB001_P5_OWNER_NATIVE_PASSPORT.json:20` still lists `products-storage/templates/p5-owner-excel/*` in its original scope. Line 66 records the move. This is historical and harmless.
- Carried over from #452: the historical evidence helpers that copy only `build_paid_07.py` would not find templates on a full rerun.

## Remaining gates (not accepted here)
- Fresh CI/public checks on this head, then integration into the working P5 chain.
- Main/deploy/live, price/SKU/payment and install are untouched and not accepted.
- General finance, legal currentness and public release / SALE_READY are not accepted.
- Owner cosmetic approval and the 19 Calc checks were not repeated (out of scope by instruction).

No source, test or product edits, and no git/gh writes. This report is the only file written in the repo. Scratch is in `/tmp/p5_455/` only.
