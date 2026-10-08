# Reviewable proposal: one-shot P1 production inventory

Status: **AUTHORING AND TESTED ONLY; not pushed, not run against production.** Branch must be `codex/p1-production-inventory-20261008`, created from the current integrated site candidate. Root reviews the committed diff before any feature-branch push. No main merge or deployment is proposed.

## Exact read scope and transport

Workflow reuses the existing sales-report `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT` with fallback22 and `DEPLOY_PATH` with fallback `www/marzhavbetone.ru`. Values are never printed. SSH uses `IdentitiesOnly=yes`, `BatchMode=yes`, `StrictHostKeyChecking=yes`, `ConnectTimeout=20`, `ConnectionAttempts=1`. One remote `python3 - <quoted SITE_PATH>` invocation receives the reviewed script on stdin. No host temporary/script files are created. Missing host Python3 or access fails sanitized, without retry, install, guessed path or fallback command.

The script reads only the established site `orders/order_*.json`, and existing ZIPs referenced by paid explicit-P1 delivery entries in `orders/delivery`. It does not search alternate directories or invent filenames for unissued orders. Root additionally authorized a bounded read of exact site `config.php` solely to parse the static `ORDERS_DIR` declaration: one `__DIR__.'/orders'` or absolute literal compared to the known path. Only true/false/null is emitted; PHP is never required/evaluated, and no other constants or file contents are printed. Dynamic/unparseable/changed configuration makes counts partial/lower bounds, rather than certifying zero P1 orders in a possibly obsolete folder.

Directory/file descriptors are anchored, regular-file checked, opened read-only with `O_NOFOLLOW`; config/order/archive symlinks are rejected. Production JSON, ZIP bytes and config values remain in host process memory; the runner receives only anonymous schema-validated JSON. No order IDs, names, contact details, tokens, prices, timestamps, actual site path, unknown product names or arbitrary ZIP member names enter artifacts/logs. Known public P1 filenames may be listed. Unknown names are counted; archive references use SHA256 fingerprints instead of private basenames. Raw remote stdout/stderr/exception strings are never logged or retained if schema validation fails.

No production files, cache, orders, locks, email, payment or hosting config are written. No production PHP/config is imported. No archive is built, repaired, extracted or migrated. File access-time updates by the operating system are not a programmatic write/migration; tests verify unchanged names, content and modification times plus absence of write flags.

## Anonymous JSON schema, version1

| Field | Meaning / allowed values |
|---|---|
| status | SCANNED_KNOWN_SCOPE / PARTIAL / INCOMPLETE / FAILED_SANITIZED; transport can produce TRANSPORT_FAILED_SANITIZED |
| configured_orders_dir_matches_known_path | true, false or null only; static declaration comparison, no config execution |
| order_files | Matching-file, valid-object, malformed/unreadable/unsafe, oversize, changed and deadline counts; no filenames |
| status_counts | paid / pending / canceled / waiting_for_capture / other_or_missing counts |
| item_sku_position_counts | Fixed known SKU enum plus other_or_missing; labels/names do not classify P1 |
| p1_order_counts | Orders identified by explicit sku=p1 or delivery p1 key; status, issued/unissued/invalid entry, no/valid/malformed/conflicting pin, and joint counts |
| archives | Paid P1 issued reference groups: reference fingerprint, anonymous reference counts, recorded expected SHA, existing actual SHA, current ZIP CRC/member checks and pin match/mismatch |
| known_p1_members / unknown_member_count | Only the fixed 19 public P1 names are emitted; arbitrary names never leave the host |
| archive_state_group_counts / paid_p1_archive_reference_state_counts | Existing readable / missing-in-known-scope / corrupt or unsupported / unsafe / changed / bounded-limit states |
| counts_are_lower_bounds / scan_entries_stable | Partial coverage and file-signature consistency; no silent skips or fake zeros |
| historical_inventory_complete / historical_authority_verified | Always false: current-file/pin match alone cannot establish historical original/archive or pin-creation time |
| remaining_blockers | Fixed enum explaining unknown paths, historical authority, unclassified SKU, incomplete/unissued legacy and unreadable archives |

The SSH wrapper rejects unexpected fields, labels, enum values, malformed SHA values and unknown member names even in valid JSON. CLI/user data cannot become shell syntax: destination fields are validated and the site path uses `shlex.quote`. Anonymous archive SHA is evidence of current referenced bytes, not automatically proof of the original purchased edition. Valid recorded pins are checked against the issued basename and actual current ZIP; inconsistent pins are not rewritten. Unissued/pending records are counted, never assigned a current archive or synthetic edition.

## Bounded once-only workflow

Push trigger is limited to the exact feature branch and new workflow file. Job additionally requires `github.event.created == true`, so later pushes do not repeat the inventory. There is no dispatch, schedule, pull-request, main/deployment route, retry loop or automatic migration. Read-only GitHub permission is `contents: read`; checkout does not persist credentials. Job timeout is five minutes. Script deadline180s, SSH wrapper215s, max1000 order files/2MiB each,100 referenced archives/64MiB each,500 ZIP members/128MiB uncompressed each. Limit/consistency failures remain explicitly partial/unverified. Hardened standard-library tests run before host access. Only `inventory-output/P1_inventory_report.json` is uploaded for seven days.

Actual production attempts authorized for this unit: **at most one**, performed only after root reviews and pushes this exact branch. No blind retry follows failure.

## Verification and concrete next release decision

Local command `python3 -m unittest discover -s tools/tests -p 'test_p1_production_inventory*.py' -q`: **26 tests pass**. Tests cover legacy current archive without historical certification, actual SHA/CRC, no archive guess for paid/pending unissued, literal SKU versus product-name ambiguity, valid/mismatched/conflicting pins, missing/corrupt references, symlink/traversal protection, type/privacy attacks, JSON/config limits and races, static-only config parsing, read-only file-open flags and unchanged fixtures, sanitized transport failure, strict SSH quoting/options, and exact branch-creation-only workflow scope. Synthetic fixtures contain private markers and arbitrary member names; tests reject their appearance in reports.

After the one read: inspect completeness/config match before interpreting counts. For any paid/pending unissued P1 without a pin, require an authoritative original archive before a separately reviewed migration. For paid issued unpinned references, keep the saved reference unchanged; a readable current legacy ZIP may still have been overwritten, so its historical origin/time remains a blocker. Missing/corrupt or pin-conflicting references require recovery from authoritative originals, never reconstruction from current masters. If the known scope is fully verified and no explicit P1 records exist, state precisely that scoped observation; do not infer zero real/all-time P1 purchases from name groups or missing data. Propose publication only after root combines this evidence with owner-approved historical scope and the separate content/legal/final-artifact gates.

Optional legal-host probe is a separate disabled proposal requiring root review. It is not part of this inventory's read scope or first approval; no network/body downloads are silently added here.
