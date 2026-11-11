# NSP public static production canonical synchronization — 12.11.2026

This draft branch preserves the verified production versions of 43 articles, `article.css`, `kalkulyator.html` and `sitemap.xml`. All 46 bytes were independently SHA-256-verified against the live site.

The **38 changed paths** are relative to `main` ef686204e0e4937ea8589cd7dda06b12a7340d11; 8 of the 46 files already matched. The original site was not changed by this synchronization.

**Do not merge until a release owner verifies the legacy main-branch deployment workflow, current PHP/product masters and unrelated public asset drift.** A full-site deployment from obsolete `main` may regress verified production; this PR is intentionally draft.

The 32 edited articles were published 11 November 2026; their structured-data `dateModified` and sitemap `lastmod` were subsequently corrected to that date in a targeted transaction. All other article dates remain unchanged. The calculator T1 link was separately corrected in place using a live-SHA-guarded hotfix.

This is a **source synchronization PR**, not a deployment request or legal/content acceptance of all products.

**Whitespace gate:** Git reports trailing blank-line whitespace on 33 article HTML diffs. These exact bytes are verified against production (46/46 SHA); stripping whitespace here would break source-to-production integrity. Classify as inherited, non-functional source formatting and address it in a separately verified content release if necessary. No other whitespace error type was found.
