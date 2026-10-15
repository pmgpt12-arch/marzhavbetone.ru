# P3 — Excel 2016-compatible isolated candidate (HOLD)

Base: PR #646, exact SHA 2d15f145d162c1042cd06e624561a21b276d7276.

Confirmed problems: PR646 XLSX 06 (SHA 862daec8…acea14f3) disables seven data-validation error alerts and fails Workbooks.Open in Excel 2016. The older PR642 file opens in the same environment. This is a compatibility defect of the PR646 source package, not a VPN, transport or model error.

Current candidate: 06-zhurnal-peredachi.xlsx, SHA-256 7efe0218defcad70921a87dcce04700a75fd8a5075a25be3874ccf9785c153a0. Seven blocking alerts restored; isolated LibreOffice XLSX normalization. Previous unnormalized candidate SHA 7cd0cb3e… was superseded and must not be nominated.

Limited verification: 50/50 formulas preserved except semantically equivalent FALSE to FALSE() in R5; seven validation rules have showErrorMessage=true, errorStyle=stop; conditional formatting unchanged; ZIP CRC clean. Native Excel 2016 opened this exact file, then the scenario harness stopped at Locked=True in B5 even though sheet protection is disabled. Locked=True also occurs in previously accepted files. Native UI typing/paste and buyer-scenario acceptance remain OPEN. LibreOffice rendered three A3 pages, no full independent visual approval.

Test: python3 tools/candidates/p3-validation-alerts-20261015/test_validation_alerts.py. Runtime hashes are recorded in receipt.json.

Candidate only. Do not merge or release; no canonical storage/runtime, pricing, SKU, payment, VPN or production change. G1–G8 remain open.
