# NSP Product Publication Matrix — checkpoint 2026-10-26

Status: INVENTORY_IN_PROGRESS; NOT PUBLICATION_READY_VERIFIED_PASS.

## Verified source inventory
- Main registry: `products-storage/ARTIFACT-REGISTRY.json`, status `ACTIVE_PARTIAL_SEED`; 13 target SKU, 19 runtime roots, 218 file SHA-256 records. These are inventory records, NOT release approvals.
- Runtime product configuration: `products-config.php`; existing site catalog: `katalog.html`.
- Historical QA matrix `tools/nsp-qa01-20261023/READINESS_MATRIX.json` returned 404 on main. Search other QA branches/artifacts; do not substitute historical masters.
- Current assignment baseline: 11 free QA candidates and P8 accepted; P1 QA-13 PAUSED; P2 QA-14 RELEASE_BLOCKED. Exact accepted archive SHA, current release permission and staging download evidence remain unverified.
- Prior P3 and P5 releases documented in PR #665 and #667; check live/current SHA before classifying ALREADY_PUBLISHED_VERIFIED.
- Existing customer-route draft PR #676 is NOT deployed. Do not infer its test PASS applies to this catalog.

## Release safety
- Do not change protected buyer archives, QA-13, QA-14, production, main, payment settings, orders or prices.
- Announcements: no cart, checkout, downloadable archive, false availability, unverified dates, or prices.
- Existing SKU and canonical URL must be reused. Do not invent products or duplicate published pages.
- Until verified QA + archive SHA + release permission, mark each product NOT_READY/BLOCKED rather than available.

## Next atomic verification
1. Locate exact accepted free QA-02–QA-12 artifacts and P8 QA receipts in GitHub branches and compare their SHA-256 with actual files.
2. Reconcile 13 target SKUs and existing runtime SKUs with catalog HTML, live state and retired P12.
3. Produce row-by-row matrix (SKU, title, type, QA, Git SHA, archive SHA, URL, live state, price source, release permission, action).
4. Only then modify storefront pages and run isolated staging browser/PHP QA, create draft PR and rollback instructions.

No production publication authorized.
