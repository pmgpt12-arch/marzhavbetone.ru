# Public checklist revision 2026-10-21

Atomic scope: one public PDF at downloads/checklist-zakrytiya-rabot.pdf. Base main: f051f0f8640e96cca2215ce7b757ad6a33a48a64. Work branch: fix/nsp-free-checklist-20261021. No buyer master or payment/mail configuration edits.

Observed HTTPS 404 twice (GET and HEAD). Read-only Actions run 39579452360 confirmed downloads and the PDF absent; production lead.php still points at this exact URL. Absence is an explicit manifest before=null, not permission to overwrite an unknown file. The old repository PDF is preserved in the base commit; its SHA is before-source.json.

Root cause/class: public downloads were excluded from the migration's static snapshot and targeted deployment. Page/paid-delivery acceptance did not cover this separate free file. Rule: the specific URL promised by a download must return the accepted bytes. New gate checks the PDF's branding, metadata, 20 checkpoints, catalog names/prices/file counts and nine link annotations, plus rebuilds from content.json. Targeted release verifies actual HTTPS bytes and PDF Content-Type. The broader ten free archives require a separate bounded follow-up; this one-file repair does not assert they are available.

The existing static transaction is extended for creation of ONLY this named public PDF. Dry-run makes no public writes. Apply may create downloads with 0755 and the file with 0644, records any created directory privately, guards against concurrent files/symlinks, preserves existing files and snapshots config privately, and rolls back to file/directory absence. The isolated regression exercises original HTML/CSS rollback plus PDF creation, no-write dry-run, concurrent creation rejection, symlink/path rejection, idempotent rollback and preservation of unrelated files.

## Reproduce

Dependencies: Python, reportlab 4.4.9, pypdf 6.10.0, DejaVu Sans regular/bold (NSP_FONT_DIR may override the system directory). No network API or model call is used to author this PDF.

```
python3 tools/nsp-free-checklist-20261021/build.py
python3 tools/nsp-free-checklist-20261021/verify.py
pdftoppm -scale-to 1300 -png downloads/checklist-zakrytiya-rabot.pdf /tmp/checklist
python3 tools/nsp-final/test_transaction.py
python3 tools/nsp-final/validate.py
```

Both pages were rendered and visually reviewed. 19 checklist sentences are preserved; the one terminology change replaces зачёты with списания в одностороннем порядке, following the owner's language rule. Four product cards now use accepted P1/P2/P7/P4 names, 20/15/13/25 files and 29,900/24,900/24,900/24,900 RUB; all contacts and metadata use the new identity. New PDF SHA: pdf-validation.json. Generated text is checked against content.json and current catalog; it is not accepted merely because the generator ran.
