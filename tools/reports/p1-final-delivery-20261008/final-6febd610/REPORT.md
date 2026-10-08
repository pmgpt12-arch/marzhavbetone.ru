# P1 final edition 6feb — independent real-path integration repeat

2026-10-08. **PASS: all ten isolated technical checks, rc0.** This supersedes the previous 258b technical candidate for final delivery evidence; the full earlier audit remains preserved.

Actual site HEAD before and after execution, also frozen content HEAD: `3015b88228ed38ea04a4e3013122d1d4a72fd6e2`. Final source binding: `bf40c826c3eb09352aa611c8d35258d7b720f16b`.

Actual NEW HTTP ZIP is byte-equal to the final frozen runtime ZIP, SHA256:
`6febd610f5739be90c298cb6b02d555ffafd7ac04aafc0d52fa2b05189c663c4`.

All 19 delivered entry hashes match all 19 current buyer sources and the final root manifest. Independent comparison with the preserved 258b manifest found exactly one changed buyer file: `13-uvedomlenie-o-prosrochke-oplaty.docx`, old raw hash `19f460448ebb9946605fa1a8180f3f10139c89c9d2d19caa31633c0cf1ce506f`, final raw hash `6f73237e36ee70cf8aab727aa6a962e559e05cc9e41de671c981f969f412663b`. The other 18 raw hashes are identical. Root describes this source delta as grammatical; this unit verifies delivered bytes and does not grant a new legal approval. All four executed runtime hashes are identical to the earlier integration run.

The same unchanged harness (`verify_actual_p1_delivery.py` SHA256 `7f11317de9a5c838e7c5671c79932f20caf1a7fa5716dfbd06ad062e2ae719a6`) again created fresh scratch-only config/orders/masters, a loopback API mock and PHP HTTP server with `sendmail_path=/bin/false`. Actual endpoints were `payment.php` → `webhook.php` → `download.php`; no direct prepare-function shortcut replaced the callback. No production config or orders were read or mutated by this unit, no real payment/checkout URL was used and no email was sent.

Ten checks passed: server pin present in a pending order before the local payment API; forged client edition/price ignored and one P1 item priced at 249000 kopeks; new pin equals final edition; real webhook trusts the local API over forged callback metadata/status; prior and new HTTP downloads each match their exact 19-file SHA maps; NEW downloaded bytes equal the root archive; repeated callback preserves issued edition/token/expiry/counter; missing pin denies without rebuilding or counter consumption; corrupt pin denies without counter consumption; all original 19 source files and four runtime files remain unchanged. The ten individual check entries and pre-API audits are retained in the raw receipt.

The marked OLD fixture is synthetic, not an authoritative historical archive. Its final-run SHA256 is `1a0632e666f63ef33a7b2bf0d3f9928030b6dcad5758889cb31856337816b114`. The actual OLD and NEW HTTP ZIPs are saved alongside `receipt.json` and `frozen-candidate-manifest-final.json`.

Raw programmatic receipt SHA256:
`ff17bbc5c837aa10828577863c0263578822ac8ca43bcda0322936f614fa8121`.
Actual run directory: `/tmp/p1-actual-release-integration-final-20261008/p1-actual-integration-4275kj2a`.

```bash
timeout 28s python3 verify_actual_p1_delivery.py \
  --site /home/denis/projects/marzhavbetone.ru/.worktrees/codex-p1-final-20261008 \
  --head 3015b88228ed38ea04a4e3013122d1d4a72fd6e2 \
  --manifest /tmp/p1-final-release-20261008/candidate-manifest-final.json \
  --buyer-dir /home/denis/projects/marzhavbetone.ru/.worktrees/codex-p1-final-20261008/products-storage/01-zakrytie-rabot \
  --receipt-root /tmp/p1-actual-release-integration-final-20261008
```

Production context has advanced beyond the earlier access uncertainty. **Root reports** that existing read-only sales-report workflow run `37754706198` retrieved 16 production order files and produced aggregates of seven paid test purchases totalling seven rubles and one unpaid purchase. This agent did not independently inspect those production records. The partial aggregates are preserved as parent-reported evidence in `production-context.json`; neither product-name grouping nor those aggregates establishes zero real P1 purchases, per-order legacy edition/pin status, or authoritative historical ZIP provenance. The raw harness receipt remains unaltered; its generic unverified-production note is qualified by this newer context.

**The publication blocker remains the per-P1 historical inventory/archive verification, not an assertion of zero orders or wholly absent production access.** Pending/paid P1 legacy counts without edition and the original archives belonging to such orders remain unverified in this unit. No automatic migration from current masters is justified by these tests. No runtime/source edits, deployment, publication, legal certification or SALE_READY claim were made.
