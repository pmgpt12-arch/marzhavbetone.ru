# MB001 P5 owner-native generator — independent acceptance (#452)

Date: 2026-10-05. Reviewer: anthropic/claude-opus-5.5 (OpenRouter), one attempt, no fallback.
Exact source: `218c4f8705f9ea2e805b7197f2f4463432686545` against accepted `57e694f7b112c7649112f0aaa469f30ccbc1fb5f`.
Scope: source/native integration only: the generator gate, the two native books, and the tests. Not whole-P5 finance/legal, not currentness, not SALE_READY. The owner's cosmetic approval is retained and was not re-reviewed.

## Verdict: CHANGES_REQUESTED (narrow)

The current output is correct. Both generated books are exactly the owner bytes. Their semantics match the accepted 57e694f values and formulas. The other nine buyer files are byte-equal. Most guards stop before the existing output is changed.

One acceptance item fails: the **defined-name guard ignores sheet-scoped names**. If a generator adds a local named range, the gate passes it, and the name is silently dropped from the published native file. The README promises the opposite ("именованный диапазон … gate блокирует молчаливую подмену"). A second, minor item: the temp file is not cleaned up if `replace` fails.

Requested changes (they do not touch the owner bytes):
1. In `write_owner_p5_workbook`, also compare per-sheet `ws.defined_names` (openpyxl 3.1 keeps local names there, and `_xlnm.Print_*` separately). Optionally also compare the raw native `<definedName>` set apart from `_xlnm.*`. Add a negative test for a sheet-scoped name.
2. Wrap `temporary.write_bytes/replace` in try/except that unlinks `*.approved.tmp` on failure.

## Inputs
- The worktree HEAD is `218c4f8…`, and the tree was clean at the start.
- All 14 entries in the immutable index match (sha256, byte size, and `git show <sha>:<path>` content). That covers 12 candidate entries at 218c4f8 and 2 original entries at 57e694f.
- `git diff --stat 57e694f 218c4f8`: 12 files, all declared P5 paths. In the buyer pack only 04/05 changed.

## Code inspection (build_paid_07.py, full diff and the relevant functions)
- `write_owner_p5_workbook` works in this order:
  1. Checks the pinned SHA256 of the template.
  2. Loads the template with openpyxl, for comparison only.
  3. Checks that sheetnames match in order.
  4. Compares the value or formula of every cell in the union of `_cells`, treating `""` the same as `None`.
  5. Compares the merged-range sets.
  6. Raises if there is any normal DV in the generated or approved book.
  7. Raises on a raw `dataValidation` substring in any native worksheet XML. This also catches `x14:dataValidation`.
  8. Compares the workbook-level defined names (attr_text).
  9. Only then writes `<name>.approved.tmp` in the same directory and calls `Path.replace`.

  Every raise comes before the write. The native bytes are written as-is, never through openpyxl.
- The comparison does not check number formats, print area/titles, freeze panes or styles. That is consistent with the design: those come only from the owner bytes, and generator drift in them never reaches the output. Observed: the gate passes number_format-only and print_area-only changes, as designed.
- `create_excel(defer_save=False)`: the default path still saves and prints the same way. The only difference is that it returns `wb` instead of `None`. Its other caller in this file is the 06 call at line 691, which ignores the return value. Other builders (`build_all.py`, `build_paid_06.py`, `build_free_*`) define their own `create_excel`, and none imports this one. 05 no longer goes through save → `load_workbook` → save.
- Observed side effect, not blocking: the historical evidence helpers `tools/candidates/evidence/MB001_P5_FIX2/rebuild_04_05_340.py` and `P5_PERCENT_INPUT/rebuild_04.py` copy only `build_paid_07.py` into a temp directory. With this change, a full rerun of them would hit FileNotFoundError on `templates/`. The new test only uses their reportlab stub.

## Actual checks run by me
| Check | Observed |
|---|---|
| `python3 -B -m pytest tools/test_p5_owner_native.py -q -p no:cacheprovider` | **13 passed in 0.50s** |
| Raw OOXML of both templates (zipfile and regex, my own) | 11 parts each. No vba/externalLink/connections. `dataValidation`=0, `x14:`=0, `<extLst`=0, no conditionalFormatting or sheetProtection, no `t="shared"`/`t="array"` formulas. definedNames are only the local `_xlnm.Print_Area` (04: `$A$1:$H$42`) and, for 05, `_xlnm.Print_Titles` (`$1:$1`) plus Print_Area (`$A$1:$M$22`). Merge counts are 26 and 1. |
| Template semantics vs the **accepted 57e694f buyer files** (my own cell-grid walk, not the gate) | 04: 107 non-empty cells, 55 formulas, 0 value/formula diffs. 05: 29 non-empty, 1 formula, 0 diffs. Sheetnames, merge sets, print area/titles and freeze (05 `A2`) are all equal. The **only** number-format differences are `DD.MM.YYYY` → `dd\.mm\.yyyy` (04: 20 cells, 05: 57 cells). |
| Real `build_paid_07()` into a temp BASE_DIR (PDF stubbed), with spies on `openpyxl.Workbook.save` and `save_workbook` | 04 sha `20165a12…` and 05 sha `db0d99f7…` exactly equal the owner/committed bytes. The only openpyxl saves were 06 (via `save_workbook` → BytesIO). **04/05 are never saved by openpyxl.** No `*.tmp` left behind. |
| My own PHP `ZipArchive` build of the committed pack, with the same exclusion list as `mvb_build_product_zip` | 11 entries, and the set equals the receipt's. Every sha256 equals `delivery-receipt.json`. 04/05 equal the owner SHAs. **The other 9 are byte-equal to the 57e694f blobs.** |
| Freshly regenerated DOCX/06 | They differ from the committed files, which is expected because of timestamps. The 9-file claim concerns the committed delivery content, and that is what I verified. |

### Negative guard checks (my own, beyond the tests; output pre-seeded with `PREV`)
| Mutation | Result | Output unchanged | tmp |
|---|---|---|---|
| 05 `E21` formula `SUM(E2:E19)` | semantic mismatch | yes | none |
| 05 label `D21` deleted | semantic mismatch | yes | none |
| 04 extra cell `Z99` | semantic mismatch | yes | none |
| 04 numeric `A18` 1 → `"1"` | semantic mismatch | yes | none |
| 04 sheet rename / extra sheet | sheet mismatch | yes | none |
| 04 new merges `G5:H5`, `A44:B44` | merged-cell mismatch | yes | none |
| 05 list DV `F2:F20` | validation mismatch | yes | none |
| Native 04 with injected `x14:dataValidations` (hash re-pinned) | native validation mismatch | yes | none |
| Corrupt zip (hash re-pinned) | BadZipFile, not ValueError | yes | none |
| Template missing | FileNotFoundError | yes | none |
| Corrupt template, original hash (from the tests) | hash mismatch | yes | none |
| **04 sheet-scoped defined name `localname`** | **PASSED — not blocked; output replaced by native without the name** | no | none |
| `Path.replace` raises OSError | error propagates | yes | **`04-…approved.tmp` left behind** |
| Stale `.approved.tmp` before a valid run | overwritten and consumed | output == native | none |

Note: my first merge probe (`A40:B40`) passed only because openpyxl's `MultiCellRange.add` drops ranges already contained in an existing merge (`A40:F40`). That was a test artifact, not a gate gap.

### Date format
`_полный_формат_даты` accepts exactly `DD.MM.YYYY` and `DD\.MM\.YYYY`, case-insensitive. In Excel number formats `\.` is a literal dot, so the displayed result is identical. My template-vs-accepted comparison shows this is the only format change. The tests reject `DD.MM.YY`, `General` and `MM/DD/YYYY`. The narrow equivalence is acceptable.

## Author claims — attributed, NOT independently verified
- "19 Calc/PHP regression checks PASS, 19.37 s" (`evidence/P5_OWNER_NATIVE/calc.out.txt`), covering Calc ru-RU input, saved results, date display/print, and PDF. **NOT VERIFIED**: I did not rerun Calc or Writer. They were not needed for the integration verdict, because the native bytes are owner-approved and pinned.
- The owner mapping receipt, `semantic differences=0`, in `owner-format-transfer-map-20261005-1412/receipt.json`: not read (outside the index). My own template-vs-57e694f comparison above covers the same claim independently.
- `git diff --check` PASS: not rerun.

## Not checked / out of scope
Legal currentness, P5 sale readiness, prices/SKU/payment/live delivery, whole-pack DOCX/PDF content. No source, test or config edits; no git/gh writes. My scratch artifacts are in `/tmp` only (`p5_452_own.zip`, `p5_452_own_checks.py`, temp directories).
