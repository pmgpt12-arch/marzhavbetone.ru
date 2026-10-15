# BRAND DECISION — «На стороне подрядчика»
Date: 2026-10-15. Owner-approved. Source task: [#653](https://github.com/pmgpt12-arch/marzhavbetone.ru/issues/653).

## Brand and domain
- Brand spelling (public): **На стороне подрядчика**.
- Full latin domain: **nastoronepodryadchika.ru**. Owner confirmed purchase 2026-10-15; direct TCI WHOIS verification: `REGISTERED, DELEGATED, UNVERIFIED`, registrar `REGRU-RU`, created `2026-10-15T10:26:33Z`, expires `2027-10-15T10:26:33Z`, NS `ns1.hosting.reg.ru`, `ns2.hosting.reg.ru`. Initial DNS/TLS failure was resolved on 2026-10-15: both authoritative NS return A `37.140.192.133` for apex/www, no AAAA; public SSL is Let's Encrypt valid through 2027-01-13, apex/www HTTPS 200. **DNS/TLS gate PASS; checkout/site-release gate remains HOLD**.
- Old domain **marzhavbetone.ru** MUST remain under control and serve per-path 301 redirects when migration is enabled.
- The old domain name and operational identifiers in records are not blanket replace targets.

## Mission and audience
- Work for the **performing party**, not against the customer: professional document workflow, reliable records of performed work/changes, calculations and acceptance, preventive handling of disagreement, lawful claims and earned payment.
- Specialization remains construction in its broad sense: buildings, industrial facilities, roads, bridges, engineering structures, transport and equipment providers.
- Owners/operators of construction machinery form a separate future product **section**, not a separate brand.
- No slogan implying all contractors are always right. Do not lead with confrontation.
- Working short positioning: «Практические инструменты для строительного подрядчика». Optional core message: «На стороне тех, кто выполняет работы».

## Channels
- Instagram: branded primary visual/social channel, editorial workflow remains independently managed. Rename public name, @username and biography only with verified session; verify availability before claiming ownership.
- Facebook: **crosspost only** from Instagram if supported; no independent editorial calendar, marketing spend, publishing effort, or channel KPI. Do not assume account/sync access.
- Telegram: rename existing channel and links when accessible. Preserve subscribers, channel ID and published history.
- Dzen: rename existing page when accessible. Preserve historical publication URLs and audience.
- Update profile/site URLs only **after** the new domain passes full release gates.

## No destructive resets
- Keep public SEO pages, cases, product catalogs, documents, payment processing, buyer access and order history.
- Preserve seller identity and legal records.
- Existing product QA and release process is independent of the rebrand. No blanket re-export of archives without an approved separate task.

## Gate order
R0 inventory & SHA / dependency map (domain, metadata, static brand, code, e-mail, payments, legal);
R1 changed branding in feature branch with checks; R2 registration+DNS+TLS+redirect staging;
R3 successful payment/webhook/order/buyer-access end-to-end;
R4 channel name/profile updates;
R5 independent release validation with rollback; publish only after PASS.

## Provisional risk register
- Hardcoded `SITE_URL` in `config.php` and YuKassa webhook documentation.
- `webhook.php` and `contact.php` mail headers include the old domain; preserve functioning mailbox until independent deliverability confirmed.
- `nginx-marzhavbetone.conf`, `setup-server.sh`, `check-server.sh` have old-host settings.
- HTML pages contain canonical, OpenGraph and image URLs with old host.
- QA helpers reference the current canonical host, so test assertions need coordinated updates.
- The legal entity/seller does NOT change with the marketing brand.

## Release proof
Commit/branch + exact changed-files manifest; static and smoke checks; path-level 301 map; new-domain DNS/TLS verified; crawl/canonical/sitemap validated; mock checkout plus a real approved end-to-end payment and delivery verification, honouring the explicitly agreed **one-hour** validity of download links (no perpetual legacy URL promise), while preserving order records; published social profile links and post crossposting checked separately. Only then mark DONE.

## Visual refresh approved 2026-10-15
- **OWNER DESIGN APPROVAL — 2026-10-15**: approved **A / «Инженерный премиум»**; no further work on option B is required.
- Final palette: graphite `#24292F`, warm white `#F7F6F2`, muted gold `#B08D57`, steel gray `#737C83`.
- Approved Figma file: https://www.figma.com/design/pOP8028A8kQlaox0FTjHK7; homepage desktop node `3:2` (1360×1197), homepage mobile node `3:45` (390×1643); concept product node `3:87` desktop / `3:114` mobile still require QA before design-to-code acceptance.
- Exact implementation gate: isolated feature branch, preserve existing content architecture, cart/payment/sales/access, no production publication before responsive visual QA and purchase gate. Do not treat a design prototype as a live site.

## Verified progress — 2026-10-16
- **Approved theme A**: 88/88 source HTML pages use new brand and scoped graphite/white/gold CSS. Chromium representative desktop/mobile UI and non-payment cart tests PASS 6/6; 3/3 injected UI faults rejected. Favicon/touch icons updated in R1 branch.
- Exact 88-page allowed transformation vs 2026-10-12 source baseline: PASS; [source proof](https://github.com/pmgpt12-arch/marzhavbetone.ru/blob/feature/rebrand-na-storone-podryadchika-20261015/docs/brand/exact-rebrand-transformation-proof-20261016.json).
- **Live visual-only preview**, noindex, no PHP/payments/forms: https://nastoronepodryadchika.ru/rebrand-preview-20261016/index.html; 88 preview HTML, 6/6 browser render, 0 payment requests; GitHub Actions [run 38785928382](https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/38785928382) PASS. It predates updated favicon asset commit; root domain still shows Reg.ru placeholder.
- New site root on Reg.ru shared hosting distinct from old: read-only SSH [run 38784188132](https://github.com/pmgpt12-arch/marzhavbetone.ru/actions/runs/38784188132) PASS; old config/orders exist, new config absent. Old commercial website is still serving buyers.
- SEO hostname candidate changes prepared separately in [R2 draft PR #661](https://github.com/pmgpt12-arch/marzhavbetone.ru/pull/661): 902 of 902 approved old-host references changed with all 84 sitemap route paths retained, link audit PASS. No PHP, redirects or production deployed.
- Historical source-pinned snapshot checks dated 2026-10-12 intentionally remain red after the brand changes; do not mutate those accepted snapshots. Release needs successor versioned acceptance, real payment/email/download and cutover gates.

## Audience and above-the-fold copy — 2026-10-16
- **OWNER APPROVED audience line:** «Для исполнителей работ и услуг в строительстве». Exact wording is the shared umbrella for the site and social profiles. Do not replace precise legal terms «подрядчик» / «субподрядчик» in contracts, product facts, titles or relevant search contexts.
- **OWNER-APPROVED FINAL HOMEPAGE OFFER (2026-10-16):** «Практические системы для решения спорных вопросов с заказчиком». The previous «Оформляйте результат. Защищайте заработанное.» is a rejected slogan and must not return. Audience eyebrow remains «Для исполнителей работ и услуг в строительстве». Supporting lead: «Готовые комплекты документов, расчёты и пошаговые алгоритмы действий — от согласования условий договора и дополнительных работ до приёмки результата, оспаривания удержаний и получения оплаты.» Primary CTA: «Подобрать решение под свою ситуацию →» (link `#situations`). This is the public offer, not a new SKU or a legal service guarantee.
- **Revised issue-card copy:** «Результат принят, оплата задерживается» replaces «Работы закрыты, но денег нет» on the homepage, including the matching sales situation label. The supporting first-card text is «Приёмка результата работ или услуг подтверждена, срок оплаты прошёл либо заказчик переносит расчёт.» Specific P1 product contents remain KS-2/KS-3: do not silently represent that product as a universal service-acceptance package.
- **SOURCE GATE:** synchronize `index.html` with `tools/rebuild_index_2026-08-14.py`. Run the 390/1360 native browser/layout/cart checks, ensure unchanged product SKU/prices, and keep approved copy changes outside unrelated financial/product data. The original 88-page strict source proof remains a historical acceptance artifact; a new versioned diff gate must explicitly whitelist these two copy changes, rather than weakening old evidence.
