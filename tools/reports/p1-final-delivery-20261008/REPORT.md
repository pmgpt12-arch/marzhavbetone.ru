# P1 final 19-file delivery: independent isolated integration

2026-10-08. **PASS for the isolated technical delivery path, not SALE_READY.**

Frozen buyer-content HEAD: `fd25ffa87c37068bad99be2bf4af57790dfd8e1f`. Actual integrated site HEAD observed both before and after execution: `ea05d91175e3e5edfab8604edabb37020900341c`. Bound source HEAD from the root manifest: `9290d65ae72c87bd8880f390cfa00c13be5acf5f`. The frozen content commit was verified to be an ancestor of the actual HEAD; each of the four executed runtime files was byte-equal to its frozen Git blob. The actual 19 source-file SHA256 values matched the frozen manifest and every entry of its runtime ZIP before testing. Report/preview commits after the content freeze do not substitute for these byte checks.

Frozen/current edition and actual NEW HTTP ZIP SHA256:
`258b6a6556a32a06ebf947b3d1b2a98857d04457490e93920d9a3ce22f8d236f`.

The standalone harness copied actual `payment.php`, `products-config.php`, `webhook.php`, `download.php` and all 19 buyer files to a fresh scratch tree. It supplied its own config, order/delivery directories, a loopback-only payment API mock and a PHP server with `sendmail_path=/bin/false`. It never read production config/orders, called real payment endpoints or visited the synthetic checkout URL; no email was sent. Ports were chosen dynamically, independently of root's CI run.

## Actual results

One bounded invocation completed with rc0 and **10 checks passed**:

1. Actual checkout writes the P1 pending order with its immutable server pin before the local payment API observes it. A client price of 1 and forged edition do not control the order: one P1 item, 249000 kopeks, API amount 2490.00 RUB.
2. A new checkout after the fixture source changes pins exactly the frozen release edition.
3. Real HTTP `webhook.php`, querying the local API rather than trusting forged callback status/metadata, marks both orders paid and preserves their different pins.
4. Old HTTP download contains precisely the 19 marked prior-fixture entry hashes.
5. New HTTP download contains precisely the 19 frozen actual buyer-file hashes.
6. New downloaded bytes are byte-equal to the root's frozen runtime ZIP, not merely a matching file inventory.
7. Repeated real callback preserves the old issued token, edition, creation/expiry and consumed-download counter.
8. Removing the old pinned ZIP gives HTTP500, does not rebuild it from new sources and does not consume a download.
9. Corrupting that pinned ZIP gives HTTP500 and does not consume a download.
10. All original 19 buyer files and four original runtime files remain byte-unchanged.

The OLD fixture is deliberately **synthetic**: the same 19 names, with one visible test marker in the first DOCX. Its ZIP SHA256 is `e19ac5a83ceb3bd7015a53f9e093ce113d5b8bb5edfb9785429f15b4f8592505`. It proves pending/issued edition preservation across a source change; it does not reconstruct or certify a historical buyer's archive. Both actual HTTP ZIP responses are preserved alongside the receipt.

Receipt `receipt.json` SHA256:
`641740ffe850c268f28653e3b45a0dcfca4dfe5ac48e79b7a3374c5601293ccf`.
Harness SHA256: `7f11317de9a5c838e7c5671c79932f20caf1a7fa5716dfbd06ad062e2ae719a6`.
The receipt contains complete old/new 19-entry hashes, runtime hashes, observed HEADs, the two pre-API pin audits and all ten check results. It includes no production payment or personal data.

## Reproduction and limits

```bash
timeout 28s python3 verify_actual_p1_delivery.py \
  --site /home/denis/projects/marzhavbetone.ru/.worktrees/codex-p1-final-20261008 \
  --head fd25ffa87c37068bad99be2bf4af57790dfd8e1f \
  --manifest /tmp/p1-final-release-20261008/candidate-manifest.json \
  --buyer-dir /home/denis/projects/marzhavbetone.ru/.worktrees/codex-p1-final-20261008/products-storage/01-zakrytie-rabot \
  --receipt-root /tmp/p1-actual-release-integration-20261008
```

Actual run scratch: `/tmp/p1-actual-release-integration-20261008/p1-actual-integration-wz3xv1l7`. The new harness's syntax/help and inventory hash/duplicate/traversal primitives were checked before use. Current runtime/tests were read after the scoped c1da575 correction; the existing immutable-edition test has 14 checks. The actual registry `tools/ci_checks.yaml` lines24–30 registers it as public/blocking with no missing-input skip. This unit does not rerun root's separate public CI or claim hosted Actions execution.

**Production inventory remains BLOCKED.** Verified counts of pending/paid legacy P1 orders without edition are unknown, production hosting/order paths and access are unconfirmed, and an authoritative original archive for any such historical order has not been established. Local mock orders and this marked OLD fixture provide no evidence of zero production legacy orders. No migration, deployment, payment, publication or production order mutation occurred. Before publication root must retain this blocker until an authorized read-only production inventory and any required migration plan based on authoritative historical archives are independently verified. Legal/content/render acceptance and whole-product sale readiness remain separate gates.
