# MB001 L1-A — verification of existing source attribution

## Task passport before execution
- execution_pattern: one_shot
- primary_result: verified_existing_content_id
- feedback_loop_required: false
- checkpoint_policy: verified_only
- Objective: verify the requested article `content_id` → existing local lead form → existing event field without duplicate implementation.
- Exact base: `64b210e5ed4d631f74aee8f0e345fcc87ff1760e`.
- Inputs at base: `attribution.js`, `lead.php`, `materialy/dengi.html`, `tools/test_browser_events.js`, `tools/test_attribution_goals.js`, merged audit `tools/candidates/MB001_L1_Judicial_Free_Lead_S1_Audit.md`.
- Scope: this verification receipt only; runtime code already implements L1-A. No new router, cookie, store, endpoint, or transport.
- Acceptance: run the existing browser-event and navigation-goal regressions offline; verify valid article slug, query/hash removal, direct/search/external/non-article negatives, all form fields and existing content_id preserved, UTM retained, and no source overwrite in content_viewed.
- Dependency: none for existing attribution verification. Paid route to S1 and sku parsing are outside this unit and require their own release gate.
- Limits: no form submissions, mail, paid APIs, network/runtime alteration, product text/prices/SKU/payment changes, merge or deploy.
- Artifact: this Markdown receipt in an isolated codex branch; actual test output and checks below. Server delivery is assessed by reading lead.php only and will not be called.
- Discovery: the audit predates implementations `2884512fb19040f9023f7dfef58079c0cd384018` and `53858fbceaa8d5f5d7acdd022b55e84fff17fdbe`, both ancestors of the exact base. Recreating L1-A would duplicate completed work.

## Verified result
Existing implementation PASS within the bounded local form contract. No runtime repair is needed.
- `attribution.js` resolves an article slug from the current article or a same-host article referrer and adds one hidden `content_id` to the existing lead form. `/articles/index.html` is excluded.
- Direct/search/external/malformed/non-article entries have no inferred article source. There is no new persistent article store.
- `materialy/dengi.html` uses the existing lead.php form and attribution.js; app.js constructs FormData from the form, so the injected hidden field is carried without a separate form handler.
- Code observation in `lead.php`: nonempty sanitized POST content_id is assigned to the existing `funnel.magnet_delivered` payload, after response delivery. No event/server submission was executed. Runtime acceptance of delivery is not claimed by this receipt.
- Runtime files at the base are retained unchanged. The requested L1-A implementation already shipped in the repository before this task; the historical audit is a baseline, not the latest implementation state.

## Actual acceptance checks — 2026-10-05
| Command | Observed result |
|---|---|
| `node tools/test_browser_events.js` | Exit 0, 16 checks PASS; five source-attribution checks include nested negative cases, no PII in browser events, failures leave the page usable |
| `node tools/test_attribution_goals.js` | Exit 0, 381 tracked links: 290 product / 91 free-material links; 225 relative links; zero defects |
| `php -l lead.php` | Exit 0, no syntax errors |
| `git merge-base --is-ancestor 2884512fb19040f9023f7dfef58079c0cd384018 HEAD` | Exit 0 |
| `git merge-base --is-ancestor 53858fbceaa8d5f5d7acdd022b55e84fff17fdbe HEAD` | Exit 0 |

The existing tests execute attribution.js in a Node VM with mocked browser transport: no real analytics events, form submissions, emails, order/payment requests, or paid-model calls.

## Residual dependencies, outside this atomic task
- L1-B/L1-C paid routing and S1 text stay behind S1 acceptance/release and the owner gate. No historical audit prices are adopted.
- S1 SKU recognition and server payment linkage require separate scoped tasks; they are not evidence that article-source L1-A is absent.
- A suppressed referrer intentionally yields no source rather than a fabricated article. Multi-hop persistence is not implemented or asserted.
- The report does not establish deployed hosting state or real traffic/purchase metrics.

## Completion boundary
Artifact + existing regression results + exact implementation provenance satisfy the assigned bounded verification. This verified receipt may be integrated into the authorized working branch. Publication/deployment gates are preserved; no merge/deploy was performed.
