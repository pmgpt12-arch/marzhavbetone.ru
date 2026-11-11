# НСП — Office VM diagnostic, 03.11.2026 (QA v2 P4/P7)

**Status:** `GUI_EXISTING_ORIGINAL_OPEN_PASS / LICENSE_MODAL_REPRODUCED / COM_ROOT_CAUSE_UNPROVEN / FINAL_V2_NATIVE_NOT_RUN / RELEASE_HOLD`.

## Exact identities and unchanged product state

- Host: `ai-workstation`, connected Desktop Commander account `db`. Existing `systemctl --user nsp-office-vm.service` is `active/running`; Windows session `nspqa` (Session 1); no laptop access, no second guest.
- Buyer P4-v3 ZIP SHA-256: `bcba234220c0f52e5a86b5ba3c70c527d086146301030d1f32197e9fa6e264fc`.
- Buyer P7-review-v2 ZIP SHA-256: `99e877fc851843a79c8524f508529ecab7da049aa6886590fcbce68a97676e24`.
- Candidate-only P4/P7 QA-v2 ZIP SHA-256: `739bf32d811f48bd7e3f41d0b45418bddba4eb31e07b1db5d99abc3d30d3fcc6`; 7 candidate XLSX, 76 graphite fills, 7 gold instruction titles; [independent static QA](QA_V2_INDEPENDENT_ACCEPTANCE_R2_20261103.json) PASS.
- Guest Windows contains **only** the earlier exact original P4/35A file `C:\nsp_qa\p4-35a.xlsx` (not QA v2). Windows `certutil -hashfile ... SHA256` after this diagnostic returned `54ef5d86e81ab120910cc5ad1889c54ff5253951ec06a180be655eaf4cf65cc4`, matching original P4/35A. No last-version file was present in the inspected filename range.

## Observed GUI diagnostic

1. The existing Windows GUI was inspected through localhost-bound VNC **without new guest transfer or remote service**. The tasklist check before open showed no `EXCEL.EXE` or `WINWORD.EXE`.
2. With the existing single Office job reserved in `STATE.json` as `nsp-excel-gui-modal-diagnostic-20261103`, opened `C:\nsp_qa\p4-35a.xlsx` through the Windows GUI.
3. On this fresh open, **Microsoft Office LTSC Professional Plus 2024 Activation Wizard** appeared as a foreground modal window. It stated **24 days remaining** for running without activation (as displayed); no product key or license activation was attempted.
4. Pressing Esc dismissed the wizard. Microsoft Excel showed the original workbook, worksheet `Реестр`, its title, 11-column orange header, and populated UI/ribbon. **GUI opens correctly when modal dismissed.**
5. Excel was closed by Alt+F4 without saving. A subsequent `tasklist | findstr /i "excel.exe winword.exe"` yielded no processes. `certutil` on the original file matched the pinned SHA above. The own Office-state reservation was successfully released; `active_office_job=null`.
6. Windows after-exit/hash screen evidence: `/mnt/server-data/nsp/operations/qa-style-candidates-v2-20261103/com-diag/NSP_OFFICE_AFTER_EXIT_AND_SHA_20261103.png`, SHA-256 `bef994dc42f3dcc0d19c88a8d2afbed5769fa3b8de5c938bc1ed5ff56894d218`, 549285 bytes. The activation modal was observed directly in the live GUI but **its dedicated screenshot was not retained** in this stage; do not claim it was.

## Prior native COM evidence and classification

- Earlier `QA24_EXCEL_MIN_SMOKE_V2_HOST.json` (02.11) and its exact `QA24_EXCEL_MIN_SMOKE_V2_RECEIPT.zip`: PowerShell `New-Object -ComObject Excel.Application` produced `Workbooks`, but `Workbooks.Add().Worksheets` returned null (`WORKSHEETS_COLLECTION_NULL`). The owned Excel process was cleaned up. That task did not complete.
- Independent `QA24_OFFICE_LICENSE_READBACK_20261102.zip` and `QA24_OFFICE_OSPP_CORRECT_20261102.zip` show `OOB_GRACE`, not an activated Office license. Fresh GUI modal confirms activation prompts still occur.
- **Inference/HYPOTHESIS, NOT verified root cause:** a modal activation wizard may interfere with an invisible automation instance, but the available evidence does **not** prove it caused `WORKSHEETS_COLLECTION_NULL`. Likewise, `OOB_GRACE` alone does not prove unusability; native manual Excel GUI can open the existing file after dismissing the dialog.
- Infrastructure `TOOL_SAFETY_BLOCK` previously blocked transfer of a QA-v2 workbook into the Windows guest before execution. **Do not bypass by a new tunnel, different account, hidden route or alternate executor.**

## Next atomic gates

1. The owner may activate their existing properly licensed Office LTSC 2024 in the current Windows GUI; do not handle/display license keys in reports and do not use third-party activators or rearm. This is a proposed step to eliminate the recurring modal; it has **not** been completed here.
2. **After** verifying the modal no longer appears, do one bounded existing-supervisor `Workbooks.Add().Worksheets` test in `nspqa` Session 1, with clear owned PID, mutex, receipt, and cleanup. If that still fails, classify COM/Office state, not product file or model.
3. Only when the existing authorized transport accepts the request, stage the exact seven QA-v2 XLSX into the guest and verify all seven guest SHA. The prior transfer tool-safety block remains an explicit permission gate. **Do not silently work around it.**
4. Run native GUI/print verification for the exact final v2 SHA (P4/35A: F/G/K header wrapping and every printed page; P4/38: 2-wide A4 print; remaining five: print and font/fill on both sheets). Save native PDF/screens, full pages, checksums and per-file receipts, then seek release acceptance separately.

**Current VERIFIED DONE is diagnostic only.** `FINAL_V2_NATIVE_QA=false`; `FULL_QA_PASS=false`; `PUBLISH_ALLOWED=false`. The current paid archives, SKU, prices, checkout, historical orders and protected source SHA are unchanged.
