# НСП — P1 post-release QA delta (02.11.2026)

**Status:** READ_ONLY_DELTA_VERIFIED / NO_PRODUCT_CHANGE / FULL_QA_PASS_NOT_REASSIGNED  
**Scope:** only the current, owner-approved P1 edition and existing evidence. No new Office job, payment, production write, merge or protected buyer-file change. The portfolio custody checkpoint is `PORTFOLIO_RELEASE_ARCHIVE_CHECKPOINT.json` in this directory; do not create a parallel SKU registry.

## 1. P1 identity — observed and verified

- Buyer edition: **P1-layout-v1**, accepted by the owner on 30.10.2026 and released with independently recorded post-deploy readback.
- Public price: **29 900 RUB**; expiry of a generated delivery link: **3600 seconds**.
- Buyer archive: **18 members (8 DOCX, 4 XLSX, 3 XLS, 3 PDF)**, SHA-256 `99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada`.
- Release proof: [GitHub Actions run #41002994365](https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/41002994365); local immutable receipt `/home/denis/projects/nsp-qa13-20261024/p1-publication-20261030/live-evidence/P1_PUBLICATION_RECEIPT.json`: `P1_LAYOUT_V1_DEPLOYED_CURRENT_ARCHIVE_AND_HTTPS_VERIFIED`.
- The 02.11.2026 current paid archive `/mnt/server-data/nsp/product-library/accepted-current-20261102/paid/PAID_P1_current.zip` has the same SHA-256. Independent local `unzip -Z1` counted exactly 18 entries; `unzip -tq` returned no compression/CRC errors.

**Chronology safeguard:** earlier QA-13 `BLOCKED` evidence refers to a different, historical 20-member release contract. The subsequent 18-member edition was explicitly owner-approved and published. These statements must not be collapsed into either “P1 never published” or “historical QA-13 automatically became FULL_QA_PASS”.

## 2. Exact current workbook evidence

Read-only extraction from `PAID_P1_current.zip` on 02.11.2026 yielded:

| Buyer member | Observed SHA-256 | Evidence classification |
|---|---|---|
| `14-raschet-procentov-395-gk.xlsx` | `5deb085cd3d7b2d248fd52db8e18d0a6bc29f4b6b8838ea6e203463fd5b9ac30` | **Exact SHA matches** previously tested CALC V4 |
| `01-ks-2.xls` | `b09296147561df5afd9a38bbb196860a1a3a3268a8b26d9751c88d4c5bca6281` | Exact legacy original SHA |
| `02-ks-3.xls` | `d6922089bffcde2a00a30d62d8d7ea1d87676fe4de9ae44a3d0e9af4d821ed0a` | Exact legacy original SHA |
| `06-zhurnal-ucheta-rabot-ks-6a.xls` | `053c5f1603478ca08fbab8f522ed4448546941d4009c79a76bdc8af13248aa29` | Exact legacy original SHA |

Historical accepted calculator record: `/home/denis/projects/nsp-qa13-20261024/proof/QA13_V4_FINAL_GATE.json`, **11/11 named native receipts PASS**, calculation scenarios **9/9 PASS**, visual blank/filled pages **12/12 PASS**, exact workbook SHA above. The 30.10 reconciliation `resume-20261030/P1_EVIDENCE_RECONCILIATION_R1.json` binds that tested workbook to P1's current 18-member edition. **These are historical successful tests, not a new 02.11 Office execution.**

**Recovered and independently read back 02.11:** the original Windows Office 2024 native evidence ZIP `/home/denis/projects/nsp-office-vm/evidence/ROOT_QA13_NATIVE_20261029.zip` has SHA-256 `04bd5942bca86747f15e8f41a838661061d746efff14df9cf4156f4cab76d4fc` and CRC PASS. Its `worker-output\\native-receipt.json` and `supervisor-receipt.json` record all three exact current original XLS hashes as `NATIVE_PASS_VISUAL_PENDING`; for each, source SHA before/after is exact and the saved/reopened content and formulas match. Executor: Excel 2024, version 16.0 / build 17932, job `qa13-xls-office2024-20261029T022711971Z-1c68d856bcfb4000a138bd9b1a1a0006`. The earlier three Office 2016 XLSX-only agent FAILs were a tool/format routing limitation, **not an XLS corruption finding**. This is a reinspection of retained evidence; no new Office execution was performed.

**Addressed 6-page print visual check:** the three native PDF exports have the SHA values recorded in the same native receipt and are readable (`pdfinfo`): `01-ks-2.pdf` = 2 A4 landscape pages, `02-ks-3.pdf` = 1 A4 portrait page, `06-zhurnal-ucheta-rabot-ks-6a.pdf` = 3 A4 landscape pages. All six pages were rendered to JPEG and reviewed as a contact sheet. There are no obvious blank or severely clipped pages or cut-off table boundaries in that overview, **not** a sign-off for fine typography or a completed filled-form customer print scenario. Contact sheet is durably stored on HDD at `/mnt/server-data/nsp/operations/p1-qa13-legacy-xls-evidence-20261102/qa13_legacy_xls_contact_sheet.jpg` (SHA-256 `6a4d1bbf693f268eae32f90d91f6c2f99216a6a4c173b933179adc7e21210d79`, 350111 bytes).

## 3. Legal delta — source check 02.11.2026

1. [АПК РФ, ст. 229.2](https://www.consultant.ru/document/cons_doc_LAW_37800/d1d697c732991b313b62196970885c898cd9e06a/) still gives a **750 000 RUB** limit for the relevant contractual-documentary arbitrazh order procedure. The illustrative residual **5 100 000 RUB** does not fit that simplified route; underlying debt, admissibility, jurisdiction and procedural prerequisites still require an individual assessment.
2. [ГК РФ, ст. 395](https://www.consultant.ru/document/cons_doc_LAW_5142/93383099dc4f06165d8d4aac4eeb159db4f6da3d/) retains the governing historical-period key-rate rule and the contractual penalty limitation in its paragraph 4. Existing calculator tests cover changing rates, partial payments, calendar-year transitions and edge cases; no new rate has been invented.
3. [КС РФ, постановление № 61-П от 22.10.2026](https://www.consultant.ru/document/cons_doc_LAW_547338/) concerns the **specific public-budget / resource-supplying organization / inter-tariff compensation** regime. This is not a general repeal of statutory interest on ordinary construction subcontract payment arrears. No broad edit to P1's calculator is justified by the ruling alone. A genuinely matching budget/RСО fact pattern would require a separate legal scenario review.

This is an **addressed legal-delta check**, not a complete fresh legal acceptance of all 18 P1 documents.

## 4. Remaining gaps and next atomic work

- **P1-LEGACY-XLS-VISUAL:** opening, saving and reopening of three exact XLS originals is now **verified from historical Office 2024 native receipts**; all six exported PDF pages have been overview-inspected, with no evident gross clipping. If strict buyer-ready print acceptance is required, perform only an addressable **filled-form / detailed-print visual check**, not a broad native rerun, change to accepted ZIP, Office activation or new executor.
- **P1-E2E-CURRENT:** the 30.10 release explicitly did **not** execute a new real paid checkout/email. Historical synthetic 200/403/410 and 3600-second expiry tests are not eleven independent live purchase E2Es. Any new payment action is a separate scope and permission gate.
- **Other current paid editions:** use their exact release receipts and existing product-specific issues; the 11/11 release archive custody checkpoint does **not** award blanket `FULL_QA_PASS`.

## 5. Acceptance of this read-only checkpoint

- [x] Current P1 ZIP SHA and 18-member count checked on server.
- [x] Current P1 ZIP CRC test passed.
- [x] Four current workbook member SHA-256 hashes extracted and compared with named historical evidence.
- [x] CALC V4 native receipts and precise scope read from retained QA-13 gate.
- [x] Later 30.10 owner acceptance/release receipt supersedes older NOT_RELEASED assumptions without rewriting history.
- [x] Current published legal sources checked for the 750 000 RUB and narrow 61-П applicability.
- [x] Exact legacy `.xls` VM native output, three source hashes and saved/reopened content independently revalidated from retained primary ZIP.
- [x] 6/6 original VM PDF pages counted and inspected in a rendered contact sheet; no gross clipping observed.
- [ ] Filled XLS customer scenario and detailed print-readability acceptance independently repeated.
- [ ] Real paid checkout/email/delivery independently retested in this turn.

**DONE for this atomic unit:** evidence-only delta recorded; no product content, production environment, prices, SKU, customer records, Windows/Office runtime or payment system changed.
