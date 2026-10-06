# Independent numerical Calc review

ACCEPT — restricted P8/P13 cached numerical fixture evidence only. Reviewer is not the author.

Fresh read-only Python/openpyxl/hashlib/zipfile verification exited 0. Verified full manifest membership, sizes and SHA256 of 20 artifacts, and both raw inputs against supplied and before/after SHA256. All 1178 P8 and 2 P13 formulas per fixture remain exact; value changes are limited to designated inputs. P13 D/F/G/I context inputs are designated in run_calc.py, although fixtures.json lists only numeric inputs.

Independent cached XLSX reads confirmed all 780 expected/actual comparisons. Error scan covered 1848 nonempty cached cells with zero error cells. An independent 36-month event ledger derived from fixtures confirmed:

| Profile | Commission | Total cost | Maximum cash gap | Gap month | Negative months | Closing balance |
|---|---:|---:|---:|---:|---:|---:|
| A | 900 | 85900 | 36400 | 3 | 3 | 14100 |
| B | 0 | 85000 | 56500 | 3 | 4 | 15000 |

Retention is 5000 and returns in month 6. P13 estimates total 45000; ratio is 0.75 for profit 60000 and cached blank for profit zero. Input labels and illustrative source sheets were read; source examples are fictional and are not this fixture.

Bound command logs show exit 0, empty stderr, separate profile paths and stdout pointing at the three actual outputs. All outputs identify LibreOfficeDev 26.8.0.0.alpha0 build 2c87e51eeaa2b413ff4ae097b2705eea1995d8e5. Exact source/artifact bindings, recorded Calc commands and arithmetic results are in review.json.

Limits: no Calc rerun; historical execution is assessed through logs and actual output metadata, and current source hashes match recorded before/after rather than independently recreating temporal state. No PDF/layout/legal/currentness/human Excel/Microsoft Excel compatibility/SaleReady gate is accepted. No network/model calls, DC, Git writes or GitHub comments were performed by this reviewer.
