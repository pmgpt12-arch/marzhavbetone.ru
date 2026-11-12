# Dzen source preflight — 12.11.2026

## Correction
The initial Dzen branch used main ef686204 as if it were the current publication source. This missed already prepared PR #705 and the production source synchronization PR #741.

## Observed and verified
Canonical article source: sync/nsp-public-canon-20261112, SHA 738041b5ae4bc69e93e346c55af73aa012300d74 (PR #741). Independent fresh HTTPS comparison: 46/46 canonical files match live, including all 43 articles. Only 8/46 files from main ef686204 match live. See source-base-recheck.json.

The 32 rewritten articles were already published in release #739; the remaining 11 are earlier approved references. A Draft PR does not mean its content is unpublished.

Metadata correction is reused from #705 (1a9d31bb74570c83d348e91d7f31c226b729f26d), including its existing title/domain/description tests. Do not create a competing metadata fix.

## Required preflight for subsequent Dzen work
1. Pin the source commit, published release receipt, and matching live hashes for the exact input files.
2. Read the latest relevant week of release/synchronization PRs; do not silently choose main as the publication authority.
3. Distinguish live defects, outdated main copies, staged source fixes and actual unpublished changes.
4. Search the existing PR/task before implementing a fix.
5. Only then derive channel copy or prepare a source change. Preserve the verified website articles; Dzen adaptations are separate editorial revisions.

This is a documented task preflight, not a claim that a global automatic source gate is already deployed. The existing mandatory metadata and Dzen link regression tests run in this branch.

## Release state
PR #744 is stacked on #741 for review. Neither PR has been merged into main by this task. No live deployment, website edit, payment, public Dzen edit or RSS publication was performed.

Recheck the 29-item published RSS against a 31-item generated candidate before any publication. This is a feed release-content decision, not a need to rewrite the 43 approved website articles.
