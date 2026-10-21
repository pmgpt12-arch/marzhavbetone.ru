# Selected homepage v3 design QA

Source truth: user archive `assets/desktop-selected.png` (1487×1058 px), exact requirements preserved in `tools/nsp-layout-v3-20261021/TZ.txt`. Mobile reference is proposed, not a separate approval.
Implementation: `tools/nsp-layout-v3-20261021/evidence/home-1440.jpg` (1440×1058 CSS px, deviceScaleFactor 1), `/tmp/nsp-layout-evidence/home-390.png` (390×844 CSS px, density 1). Same initial home route, no dialogs, empty cart. Desktop reference resized to 1440 px width preserving aspect ratio; remaining bottom canvas padded white. Full comparison: `evidence/desktop-comparison.jpg`; focused header comparison: `evidence/header-comparison.jpg` in the same task directory.

## Findings and fixes

- P2, initial hero: heading wrapped with only «объекту» on the second line; building nearly absent after the first crop. Fixed with a desktop-only first-word span and an aspect-preserving right-aligned source composition. The final combined comparison shows the selected two-line desktop hierarchy and crane/building at right. Mobile retains natural wrapping.
- P2, enlarged text: long brand and heading words overflowed at 200% text size. Fixed component word wrapping and header/nav reflow. Repeated all six widths with exact doubled computed font sizes; PASS.
- Lab diagnostic: first local Lighthouse LCP 3036 ms, CLS 0, with uncompressed HTTP/1.1 static serving. Render-blocking CSS accounted for the delay. Corrected development serving to use gzip, matching verified production `Content-Encoding: gzip`; repeated affected measurement: Lighthouse 12.6.1 LCP 2286 ms, CLS 0. No comparison of scores across environments is claimed.

## Required fidelity surfaces

- Typography: current project font stack retained, no external font. Desktop brand 24 px and H1 64 px, mobile brand 18–19 px and H1 38–40 px follow explicit TZ over image-generated type sizes. Exact approved text retained. No fixed mobile line breaks.
- Layout: 520 px desktop hero; clean text field at left, construction at right; three directions with simple dividers immediately below. Mobile vertical list, CTA within the first 360×800 and 390×844 viewport. No nested card decoration.
- Colors: #F5F3ED paper, #252A2E text, muted gold accents; all six home axe passes have zero violations. Gold is decorative or an underline, not low-contrast small text.
- Assets: supplied crane artwork preserved as raster, aspect ratio preserved, no fabricated SVG construction art. One responsive resource per viewport, desktop/mobile within 250/150 KiB. Standard icons are unmodified Lucide library paths, ISC license retained. Cart remains the existing working button with dynamic count; its visual treatment intentionally preserves the shared purchasing component.
- Copy: exact hero, subheading, buttons and three stage descriptions match TZ. Paths are distinct; existing situation picker and product mechanisms preserved. Secondary destinations remain available from page blocks/footer and mobile menu.

## Browser and interaction evidence

Cloud browser preview opened and inspected at terminal.local; actual catalog CTA followed. Cloud browser console contains only extension metadata errors from a chrome-extension URL; no site JS error was observed. Automated Chromium 153 checks cover widths 360,390,768,1366,1440,1920; 200% text; six axe passes; three context-preserving catalog routes; diagnostics; cart open/close; responsive image request count; no new first-party failed requests. Menu Escape returns focus to toggle. Existing UI regression: 35 layout checks, 10 axe cases, four mocked checkout cases, calculator boundaries PASS. No real payment or email.

Safari/iOS is untested. Local preview remains available. Browser evidence and exact SHA will be included in release report after GitHub Actions verification. No actionable P0/P1/P2 design finding remains in the checked build. No further P3 iteration is required for this delivery.

final result: passed
