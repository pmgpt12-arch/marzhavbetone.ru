# BRAND DECISION — «На стороне подрядчика»
Date: 2026-10-15. Owner-approved. Source task: [#653](https://github.com/pmgpt12-arch/marzhavbetone.ru/issues/653).

## Brand and domain
- Brand spelling (public): **На стороне подрядчика**.
- Full latin domain: **nastoronepodryadchika.ru**. Owner confirmed purchase 2026-10-15; direct TCI WHOIS verification: `REGISTERED, DELEGATED, UNVERIFIED`, registrar `REGRU-RU`, created `2026-10-15T10:26:33Z`, expires `2027-10-15T10:26:33Z`, NS `ns1.hosting.reg.ru`, `ns2.hosting.reg.ru`. From ai-workstation DNS A/AAAA resolution failed and HTTPS unavailable at verification; **DNS/TLS gate is not passed**.
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
Commit/branch + exact changed-files manifest; static and smoke checks; path-level 301 map; new-domain DNS/TLS verified; crawl/canonical/sitemap validated; mock checkout plus real approved live end-to-end payment and delivery verification, including old-buyer access; published social profile links and post crossposting checked separately. Only then mark DONE.

## Visual refresh approved 2026-10-15
- **OWNER DESIGN APPROVAL — 2026-10-15**: approved **A / «Инженерный премиум»**; no further work on option B is required.
- Final palette: graphite `#24292F`, warm white `#F7F6F2`, muted gold `#B08D57`, steel gray `#737C83`.
- Approved Figma file: https://www.figma.com/design/pOP8028A8kQlaox0FTjHK7; homepage desktop node `3:2` (1360×1197), homepage mobile node `3:45` (390×1643); concept product node `3:87` desktop / `3:114` mobile still require QA before design-to-code acceptance.
- Exact implementation gate: isolated feature branch, preserve existing content architecture, cart/payment/sales/access, no production publication before responsive visual QA and purchase gate. Do not treat a design prototype as a live site.
