# Cached baseline P4/P9: local DOCX visual observations

Exact input bytes from commit `264d75a06d59de82602dc1bcef347913c44cc648` were read, rendered, compared with PDF text, and visually inspected on every page. P4 original: 2 pages; fictional filled-copy scenario: 2 pages; P9 glossary: 7 pages. Original SHA-256 before/after is identical for both files. No product edits, server actions, Git mutations, or API calls.

LibreOfficeDev 26.8.0.0.alpha0 local runtime differs from the server's 24.2 and Microsoft Word. This report describes this render only.

P4: no clipped or overlapping text. Inventory breaks across the page boundary in both blank and filled scenarios; the final page has substantial spare space. Signature blanks are intentional. Filled copy is explicitly marked fictional and exercises longer party names and a document list; repeated generic source placeholders receive generic values and are not a legal-use example.

P9: all seven pages inspected. Page2 carries only two lines before the Parties table starts on page3. Long field tokens wrap inside words in tables; text remains visible, but copying tokens manually is less convenient. Continuation table header on page4 is visible. Warning box, procedures, tables, cross-kit mapping, and final workflow remain readable with no observed overlap or clipped cells. Literal tokens retained because this file explains token definitions rather than being a submission form.

Initial P9 page3 PNG was truncated despite rc0. Failed PNG retained. One specifically authorized extraction of page3 from the unchanged PDF passed PIL.verify and was inspected. No original DOCX rerender occurred.

Complete per-unit source/PDF matching is in `text-coverage.json`, each source paragraph or table cell has a locator; command outputs, profiles, timing and output hashes are in `run.json`. Observations and explicit acceptance limits are in `observations.json`.

Legal/currentness/human acceptance, Microsoft Word compatibility and SaleReady remain NOT_VERIFIED. Pagination and token wrapping are observations; no automatic release approval follows from this result.
