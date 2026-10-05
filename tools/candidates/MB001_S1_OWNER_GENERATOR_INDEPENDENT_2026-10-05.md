# MB001 S1 owner generator — independent acceptance (PR431)

Verdict: **BLOCKED** — I couldn't run the required checks, because the sandbox would not let me execute anything except `git` and `sha256sum`. My static review found no blocking code defect. The coordinator needs to approve execution or rerun the checks.

- Observed HEAD SHA: `f15e3c04135ba163050e5186a1ff6b8ef31732ca` (`git rev-parse HEAD`, matches the target)
- Reviewer: an independent agent, not the author. I read no author conversations.
- Run dir: `/home/denis/.local/state/claude-dispatcher/recovery-20261004/owner-generator-review-20261005-1503/433` (no files were written there because every command was denied)

## Why BLOCKED

The contract requires my own narrow success/failure check, or `tools/test_approved_s1_excel.py`, run in my own temp directory. These commands were all refused with "requires approval":

- `python -m pytest -q -p no:cacheprovider tools/test_approved_s1_excel.py` (with and without `--basetemp=<run>/pytest`)
- `unzip -o -q -d <run>/t08 …/08-raschet-procentov-395.xlsx`, needed to inspect the 08 Проверки row 13 change
- `unzip -p …/08-raschet-procentov-395.xlsx xl/workbook.xml`

So I have not observed any build, any byte comparison of generated output, or any run of the fail-before-overwrite path. This is one attempt with no fallback, as instructed.

## Checks I actually ran

| Check | Result |
|---|---|
| `git rev-parse HEAD` | f15e3c04135ba163050e5186a1ff6b8ef31732ca |
| `sha256sum` of 04 template | `f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9`. Matches the owner acceptance at 2026-10-05T14:39:59+07:00 and `approved-sha256.json` |
| `sha256sum` of 02 template | `0a5c75b2…6fcc`. Matches `approved-sha256.json` |
| `sha256sum` of 08 template | `9c2b6904…3d92`. Matches `approved-sha256.json` and `new_template_sha256` in the delivered diagnosis |
| `git ls-files -s` | The committed `tools/candidates/s1-oplata-za-raboty/{02,04,08}` outputs have the same blob IDs as `tools/templates/s1-owner-excel/{02,04,08}` (8561621…, 37e1885…, 73ec536…). So the committed 04 output byte-equals the owner-accepted 04. This only proves the committed artifacts match; I did not regenerate them. |
| Static read of the `save()` delta, `approved_s1_excel.py` and the updated tests | See below |

## Evidence reused, not checked by me

- The author's report of two builds and 67 tests, the Calc/PDF check of the longest warning, and no test skips. These are delivered inputs 0, 1 and 3; I did not re-run them.
- The 08 diagnosis (input 2): Проверки row 13 height changed from 28.8 to 63 (copied from the original accepted source), all other ZIP parts are byte-equal, old owner sha `e84c78d3…`. I could not check this row delta because unzip was denied.
- The 08 M19 change is spelling only: the code diff shows `"Итого по акта́м"` → `"Итого по актам"` with no formula change. I did confirm this from the diff.

## Static review findings

The contract points I could confirm by reading the code:

- **The gate runs before any write.** `write_approved_layout` checks four things in order: the template hash, sheet names, every cell value and formula string (the union of generated and template cells, with `""` treated as `None`), validations, and workbook-scope defined names. Only then does it write the bytes to a `.approved.tmp` file and swap it in with `replace()`. If any check fails, an exception is raised before the temp file is written, so the prior output is untouched.
- **Stale bytes are not substituted.** If the source generator changes a formula or value, the build stops instead of silently writing the old approved bytes. This keeps the accepted semantics of original421 and literal426.
- **Normal and x14 validations are both covered.** `_native_validations` walks every element whose local name is `dataValidation`. That covers normal rules and x14 rules, whose `xm:sqref` and `xm:f` are read through child text. The parsed native rules are compared with the generator's normal rules.
- **`save()` behaves as described.** It sends only workbooks whose names appear in `APPROVED` through the gate and skips print/normalize post-processing for those files. That is intended, because the native layout is owned by the template.
- **The reader-test changes are representational.** `formulas()` now expands shared formulas through openpyxl, and the reaction-list test reads x14 validation through `_native_validations`.

Coverage gaps I found. None of them blocks acceptance on its own:

1. **Sheet-scoped names are not compared.** Only `workbook.defined_names` is checked; in openpyxl 3.1, `ws.defined_names` is a separate store. If the templates contain sheet-local names, they are unchecked.
2. **The validation rule tuple is narrow.** It holds `type`, `operator`, `allowBlank`, `formula1` and `formula2`. It does not include `showErrorMessage`, `errorStyle`, `showDropDown` or the prompt/error texts, and overlapping sqref ranges overwrite each other in the dict.
3. **Formulas are compared as strings.** An `ArrayFormula` or `DataTableFormula` object could compare unequal by identity. That would stop the build rather than write wrong bytes.
4. **A temp file can be left behind** if `write_bytes` fails partway. This is minor.
5. **Atomicity across files is not reviewed.** If 08 fails after 02 and 04 were already written, the earlier outputs stay in the new state.
6. **Tests:** `test_native_owner_bytes_survive` loads an unused `generated` workbook, which is harmless. No test changes a financial formula in 08 (the mismatch test only covers 04 `I5`), and no test covers a defined-name mismatch.

## Release gate

The native Excel owner review of the updated 08 (the row 13 height change) is still **open** and is not closed by this review. 02 and 04 are owner-accepted.

## What is needed to reach ACCEPT/CHANGES_REQUESTED

1. Approval to run `python -m pytest -q -p no:cacheprovider tools/test_approved_s1_excel.py --basetemp=<run>/pytest`.
2. Approval to run `unzip -d <run>/t08` (or a read-only openpyxl script) to compare the 08 row 13 delta against the old owner file `e84c78d3…`.

If both pass, my static review supports **ACCEPT** for the source integration, with gaps 1–6 as follow-ups and the updated 08 native review as an explicit release gate.
