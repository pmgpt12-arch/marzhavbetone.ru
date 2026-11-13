# Dzen RSS editorial release, 13 November 2026

This continues PR #744 on verified public source #741. Only rss.xml is deployed by the branch-specific manual workflow; the general website deployment and main branch are not changed. Do not merge this branch's source-probe.yml override into main.

Four full reader revisions (001–004) are serialized in data/site/dzen-editorial.json. Eight compact drafts are withheld pending content matching. The existing 29 GUID/link/pubDate/image identities are locked by release-identities.json; two newer source articles are withheld. The other 25 articles use current approved website source with their existing feed headlines, covers, and dates. Existing manually published article exclusions remain.

Acceptance: builder, RSS markup/content checks, five traffic/release contract tests, title contract checks; HTTPS cover/CTA checks. All 29 IDs, dates and covers preserved, four revisions checked exactly against editorial bodies, one target CTA per revision. The retention baseline article about GU in KS-2/KS-3 is not replaced by the different profit-angle draft.

Publication of the feed does not prove Dzen ingestion or replacement of already-published channel articles. User screenshot confirmed site verification, but feed connection and Dzen ingestion require separate evidence.

Before feed SHA-256: 62f921f7d72fba7596a430e25a51d639d9fc29fdf50b22496de6a09207416dc9
Candidate: 29d60ab71d520539164105a2182b8b704e27833b10dfa44b668ccecc5f2e512a

The PHP publisher refuses unexpected live hashes, verifies a private backup outside webroot, writes through a temporary file and atomic rename, and checks index.html remains unchanged. Failed HTTPS verification invokes a rollback guarded by the candidate hash.

## Verified live result
Release Actions run: https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/43386476216 — success. Independent public HTTPS returned 200 and exactly matched candidate SHA-256. All 33 old-cover and CTA endpoints returned 200. Controlled publish, rollback and concurrent-drift refusal tests passed. Dzen ingestion is not verified. The operational source-probe.yml override stays in the isolated deployment branch and is excluded from the clean source PR.
