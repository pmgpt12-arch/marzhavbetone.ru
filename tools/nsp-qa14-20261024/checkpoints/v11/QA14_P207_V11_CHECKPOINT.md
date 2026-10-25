# QA14 / Excel 07: checkpoint v11 / 2026-10-25

STATUS: RELEASE_BLOCKED. FULL_QA_PASS not assigned.

V11 workbook SHA-256: fe432915ee16c61decce5a968866767e3d605caf92738a05c69cdd71a211f237
QA ZIP SHA-256: ab4c34fbb6ccd4e9d4ba57d0e2a961cd0b65a9f9d65346b94053c338fd848e86
14 of 15 entries byte-identical to legal-v2. CRC PASS.
203 registry formulas and 100 source rows preserved exactly in OOXML.
Blank and single-row native Excel 2016 test PASS, 28 checks.
Native receipt SHA-256: e9c511cf715f7bb737f11c45544e2266e306c2e7b4d8d2de55cc09b99e41bda1
Blank and single-row PDFs: each 1 A3 page, images visually examined.
Subtotal and signature rows now follow the data row.

OPEN gates: sparse, partial, source row 103, 100 filled rows, save/reopen, all-page visual checks, actual customer print selection.
Office shared queue second submission blocked by platform safety control. No retries, no alternate channels.
Accepted historical 12/12 v9 calculation results preserved, not rerun or assigned to v11.
File 04 release configuration decision independent and pending.
No main/production/payments/public archive/QA13/QA15 changes.
