# MB001 S1 notification — independent review (Issue #441)

**Verdict: ACCEPT**

- Reviewed SHA (worktree HEAD, verified `git rev-parse HEAD`): `86b57412a1c7d2386e04b73e5e4ee77e36d27788`
- Author candidate (PR #439): `950106cceb546bab766e09cb6d02ceb98febb3a7`; test-contract fix (PR #440) = `950106c..86b5741`
- Reviewer: independent Claude agent (anthropic/claude-opus-5.5), single attempt, no source or buyer file changes. This report is the only output.

## Input gate (own check)
- All 15 entries in `s1-notification-inputs/index.json`: sha256 matches (`sha256sum`).
- `after.sha256` (12 buyer files) matches the actual `tools/candidates/s1-oplata-za-raboty/*` byte for byte; no extra files.
- `before.sha256` vs `after.sha256`: only `03-algoritm-dejstviy.docx` and `06-uvedomlenie-o-prosrochke.docx` differ.
- `git diff --name-only 950106c^ 86b5741`: builder, 2 candidate reports, 03/06 docx, `test_s1_candidate.py`, new `test_s1_notification_print.py`. `950106c..86b5741` touches only `test_s1_candidate.py` (+15/−4) and its report, so exactly two test assertions changed.

## Checks

| # | Check | Result | Evidence (own unless noted) |
|---|---|---|---|
| 1 | 06 prints only the letter to the customer | PASS | python3/zipfile paragraph diff, 06 from `950106c^` vs HEAD: 10 paragraphs removed (title, subtitle "Файл 06…", «Важно…» disclaimer, candidate note, «Как подготовить приложение» + text, «После отправки» + 3 bullets), 0 added. The 29 remaining paragraphs are parties, heading, intro, table, 4 letter paragraphs, signature. `f06` calls `new_doc(..., disclaimer=False)` and removes the title paragraph. |
| 2 | Business/legal wording of the letter unchanged | PASS | Same diff: every remaining paragraph matches the old text exactly (intro, п. договора/срок, сумма долга, требование + возражения, претензия/ст. 395 ГК РФ/арбитраж, приложение, подпись). Table header unchanged. |
| 3 | Removed guidance kept in 03 step 8 with correct worksheet addresses | PASS | 03 diff: 0 removed, 11 added, inserted after step 8's «Подтверждение/Следующий шаг: шаг 9/Развилки». The purpose paragraph from the old subtitle is kept word for word, the «После отправки» bullets are word for word, and the attachment text is kept with added row addresses. 03 says the «Важно» block and the candidate note also cover 06. Addresses checked against the builder: «Долг по актам» header row 4, C = «Документ (КС-2 / акт: №, дата)», D = «Последний день срока оплаты», range 5–34 (`$B$5:$B$34`); «Взаиморасчёты» header row 4, data from row 5, A–J ends at J «Общий долг нарастающим итогом», summary in L–M (M10/M12). |
| 4 | Distinct deadline/appendix dates; A4 | PASS | 06 has `{{ДАТА_ДОКУМЕНТА}}`, `{{ДАТА_ОПЛАТЫ_ПО_ТРЕБОВАНИЮ}}`, `{{ДАТА_РЕЕСТРА_ВЗАИМОРАСЧЁТОВ}}` and no bare `{{ДАТА}}`. `pgSz w=11906 h=16838` (A4). The filled PDF shows three different dates: 05.10.2026 / 20.10.2026 / 04.10.2026. |
| 5 | The two test changes keep coverage | PASS | (a) The disclaimer check for 06 now requires `не юридическая консультация` and `относятся и к файлу 06` in 03. The 06-without-service-text side is covered by `test_06_prints_only_the_letter` (exact LETTER match, no Title/Heading styles) and `test_06_has_no_service_leakage`. (b) The attachment check still requires the old «выгрузка из файла 04» to be absent from 06, and requires the unique heading «Как подготовить приложение» (1 occurrence in 03) plus «выделен» in 03. Exact moved text is checked by `test_03_step8_keeps_moved_guidance`. «выделен» alone is a weak marker (3 occurrences in 03), but the unique heading and the exact-text test make up for it. Neither change hides a defect: they follow the intended F-2 move. |
| 6 | Other buyer files unchanged | PASS | `after.sha256` vs `before.sha256` and the actual worktree: the other 10 files are identical. |
| 7 | Filled PDF: no tokens/service text, full signature, readable print | PASS | `pdfinfo`: 1 page, 595.3×841.9 pt (A4), LibreOffice 24.2. `pdftotext -bbox`: no `{{`/`}}`, no «Важно», «Редакция-кандидат», «Как подготовить», «После отправки», «Файл 06». All words inside the page (max x 501.6, max y 686.6). Signature line complete: «Генеральный директор, действует на основании Устава ___ / И. И. Иванов /». **Visual:** I opened `06-filled-1.png` (sha256 `8cc3c816…fb881`) myself. It is consistent with the coordinator's observation in `coordinator-print-check.json`: one A4 page, clean letter, table and signature readable. |

## Tests
- Own run: `python3 -m pytest tools/test_s1_notification_print.py tools/test_s1_a4.py tools/test_s1_unique_fields.py -q` → **10 passed in 0.32s**.
- Coordinator's result (not rerun here): `tests.stdout` reports 71 passed in 106.76s. The author's negative fixtures (old source fails 3 notification tests) come from `test-contract-report.md` and were not reproduced.

## Out of scope / remaining gates
- F6, outside this acceptance: the signature surname wraps («/ И. И.» then «Иванов /» on the next line, y 660.9 → 674.8), and blank table rows 3–12 still print in the filled letter. Both were seen in the PDF geometry and the PNG.
- Native owner Excel 08 is owner-accepted per the coordinator (`9c2b6904…3d92`) and was not rechecked here.
- No new legal or currentness judgment. No SALE_READY. Whole-product, legal and release gates stay open. No rebuild, render, export, git writes, merge or deploy.
