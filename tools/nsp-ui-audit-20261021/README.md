# UI audit correction, 2026-10-21

Input: owner-supplied `NSP_audit_2026-10-21(1).zip`, audit snapshot after the Dzen release. Base: `1ff03c700e03c3980a2a437dd1c4efd3befb6ceb`, last verified main and production source.

## Reproduction

Node 22+, Playwright and @axe-core/playwright 4.14.0, Chromium/Chrome. Set `NSP_CHROMIUM` to a runnable Chrome binary (default `/usr/bin/google-chrome`), then:

```
node tools/nsp-ui-audit-20261021/verify_ui.cjs
python3 tools/nsp-ui-audit-20261021/test_email_checkout.py
python3 tools/nsp-final/validate.py
```

For isolated local dependencies, set `NODE_PATH` to their node_modules directory. Browser checks start an ephemeral loopback static server, map app-script.php to app.js, block external resources/analytics and mock payment.php. Outputs default to `/tmp/nsp-ui-evidence`; override with `NSP_TEST_OUTPUT`. `NSP_ONLY=checkout` repeats only checkout/calculator checks. The PHP test requires PHP CLI with curl/mbstring, uses temporary directories and a loopback fake provider, deliberately sends false client prices, and removes all fixtures. It creates no production order, delivery or email.

Full browser acceptance: 35 viewport/template cases; 10 WCAG A/AA axe analyses; four checkout widths, forward/backward keyboard cycling, native Escape and close, focus restoration, required email/unselected consent, empty optional contact and a two-item cart; calculator empty/zero/negative/large inputs and synthetic 10% example (not a current legal rate).

## Release

Existing bounded transaction in tools/nsp-final is reused, adding root CSS to the existing-file allowlist. No new public paths are created. All 88 HTML pages receive only the new shared CSS cache hash, except the three pages with explicit copy/flow edits. Main deploy stays frozen. Candidate: 90 static files = 88 HTML + app.js + shared CSS. Before/after manifest, price/button/robots signatures and before-source inventory are kept in tools/nsp-final.

Dry-run and publish are separate explicit request.json commits. Publication creates private unique configuration backups, checks unchanged root PHP and runtime master fingerprint/13 prices/TTL, retains original static files outside webroot, verifies exact HTTPS bytes for every changed file and effective app-script.php, and has guarded rollback.

## Scope limits

No real payment, email sending, buyer-master editing or new Office audit. Automated accessibility checks cover the five listed templates in their tested states and the checkout, not a blanket manual accessibility certification. Diagnostic results reached through every answer branch are not exhaustively audited. Analytics and indexing are not inferred from the audit's empty reports. Historical broad CI and delivery guarantees are not recertified here.

A separate branding debt was confirmed in the unchanged public free PDF `downloads/checklist-zakrytiya-rabot.pdf`: it has 20 checkpoints but an old brand/contact footer and old product counts. This release truthfully labels the on-page preview as 12 of 20; it does not replace that PDF or claim the full document rebrand is complete.
