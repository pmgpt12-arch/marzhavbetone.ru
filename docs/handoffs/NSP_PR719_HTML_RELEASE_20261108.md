# NSP PR #719 — production HTML-only publication receipt

Date: 2026-11-08 (UTC). Site: https://nastoronepodryadchika.ru

## Verified release

- Source of agreed names: PR #719, `feat/nsp-product-names-20261108` @ `ca6e2b2`.
- Isolated release workflow: `ops/nsp-pr719-targeted-deploy-20261108` @ `a3af425`.
- Production run: https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/42448751567 — SUCCESS.
- GitHub Actions gates: `PREFLIGHT_PASS 28/28`, `NAME_GATE_PASS 11 paid + 10 free + 11 subtitles`, `BACKUP_PASS`, `UPLOAD_PASS 28/28 SHA-256 match`.
- Backup outside document root: `$HOME/nsp-pr719-backup-20261108T045808Z` (28 HTML originals; no secrets or backups placed in public web root).
- Independent public HTTPS checks: 11/11 paid catalog titles, 10/10 free catalog titles, 11/11 subtitles, 11/11 paid detail headings/subtitles, 10/10 free detail pages; all HTTP 200 and `PUBLIC_VERIFIED_PASS`, `FREE_DETAIL_VERIFIED_PASS`.
- No change to SKU, price, href, src, ZIP archives, payment scripts, config.php. Retired T2/T3 still absent from public catalog.

## Incident and preventive gate

- Two earlier simultaneous release runs `42448067778` and `42448091850` conflicted; the SHA concurrency checks detected the race and both rolled back. The public page state was verified after rollback. These runs are NOT successful releases.
- Root cause: concurrent workflow_dispatch runs before workflow-level serialization. Fix: GitHub Actions `concurrency.group: nsp-pr719-production-html-single-writer`, `cancel-in-progress: false`, commit `a3af425`.
- After the fix, dry-run `42448610550` completed successfully before the one successful production run.

## Remaining independent source-of-truth task

GitHub `main` is not reconciled with the current production catalog and still contains retired T2/T3 in its source. The general legacy deploy must remain disabled. Do NOT merge PR #719 or reactivate broad `--delete` deployment until a separate production-to-GitHub baseline reconciliation is reviewed and validated. This source reconciliation is not necessary for the completed HTML-only publication but remains a release-management dependency for future full deployments.
