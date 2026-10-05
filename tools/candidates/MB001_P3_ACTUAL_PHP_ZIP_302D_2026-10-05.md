# P3: actual PHP ZIP at accepted 302d snapshot

execution_pattern: one_shot
primary_result: P3_exact_302d_actual_PHP_ZIP_membership_hash_CRC_and_02_06_metadata
feedback_loop_required: false
checkpoint_policy: verified_only
frozen_input_sha: 302d2e4d44bea16508b8e6e64211a2d10953aa51

Root independently read the full 172-line receipt and actual build.php and accepted this narrow packaging proof before documentary persistence. This report adds evidence only; product sources, templates, catalog and services remain unchanged.

The live working branch claude/cool-bardeen-pbwfsx was verified before and after execution at the exact frozen SHA. A focused preflight found no existing actual packaging proof for this exact head. PHP 8.3.6 with ZipArchive was already installed; no dependency install, model API, existing service or real order was used.

The actual products-config.php resolves p3 to 05-ks-bez-vozvrata and 05-ks-bez-vozvrata.zip. One real mvb_build_product_zip('p3') invocation used isolated PRODUCTS_DIR, ORDERS_DIR and DELIVERY_DIR. PHP exited 0 in 0.10249 seconds; the complete bounded proof finished in 3.37410 seconds.

| Check | Actual result |
|---|---|
| ZIP | 320206 bytes; SHA256 1d7b108f84472976ffffcf73c0e7a5567d28f2d86583d0a7b025ac5b0c140bcc |
| Membership | Exactly 11 buyer files, no duplicate members; all equal actual catalog source after explicit builder exclusions |
| Every file | Full bytes and SHA256 equal frozen Git input; ZIP CRC checked by testzip and explicit CRC32 |
| Service/template exclusion | MANIFEST.md, .htaccess and 00-PISMO-POSLE-POKUPKI.txt excluded; no tools/templates files delivered |
| XLSX 02 | Raw accepted bytes exact; SHA256 7d3a10560614401c36ef854cd3aead16961864479a9bfcb7d38dc78ab743c7f3 |
| XLSX 06 | Raw accepted bytes exact; SHA256 98f20a51a39c41d5cf0e0fd6766cbeb1e8906bbad087956b736b1482f18ab73d |
| Producer metadata | Both ZIP-delivered XLSX have exact source app.xml, Application Microsoft Excel and AppVersion 3.1; Application matches canonical literal in frozen build_paid_05.py |
| Input provenance | 15 actual Git blobs retained with full SHA, SHA256 and length in input-blobs.json; all copied inputs unchanged after execution |
| Source / runtime scope | No repository source edit, general-test rerun, Calc/Excel run, merge/deploy or model invocation in this proof |

Actual commands:
```text
timeout --kill-after=5s 60s python3 /home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/p3-actual-zip-302d/verify.py
timeout --kill-after=5s 30s php /home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/p3-actual-zip-302d/build.php
```
Actual cwd, exit and runtime are in php-execution.json. Receipt includes every member hash/CRC and both app.xml strings. Evidence directory P3_ACTUAL_PHP_ZIP_302D_20261005 contains the as-run scripts, passport, actual ZIP, logs, full receipt, actual 15 input blobs and original checksum manifest. PERSISTED_SHA256SUMS.txt authenticates the persisted set. The original SHA256SUMS.txt additionally lists the two isolation-only deny files retained on the server under the as-run directory; these are not product files and are not needed to replay the builder.

The verify.py and build.php are preserved as-run, with their original server paths. Do not execute them in-place as a test: they refuse an existing exact-source input and were used for one bounded proof, not introduced as a new framework. The original actual run directory retains all execution files.

Acceptance is packaging only. The previous 35-test metadata validation remains previously accepted and was not rerun here. Native desktop application acceptance and body/legal review were not performed. Application metadata is a producer compatibility label, not proof of an Excel application session. release_pass=false and sale_ready=false; no main/release authorization is implied.
