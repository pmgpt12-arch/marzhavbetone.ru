# S1: separate reviewed correction overlay for 02/08

Owner-native templates and their approved-sha256.json remain byte-for-byte unchanged. Two separately reviewed correction artifacts replace one shared string each: 02 Карта рисков!F19 and 08 Как пользоваться!A12. The generator now emits those exact texts; the native writer verifies the original owner lineage, independent report hash, correction hash, all ZIP members and unchanged parts, exact single raw text substitution, all decoded cells/formulas, validations, and workbook/worksheet scoped names before copying verified native bytes. File 04 keeps its original native output.

The exact-artifact independent report with coordinator addendum is pinned at SHA256 9ebc3d408fdf214acbf49b23526db6b7c394fe6a308ca28e3f0a369b173b620a. Raw independent report is preserved separately. Independent ACCEPT covers the two corrections and their isolation. It grants no fresh owner approval, official normative currentness, human legal acceptance, or sale/release approval.

Pending correction records fail before touching output. Write/replace failures clean the temporary file and preserve the previous output. Meaningful negative checks exercise hashes, review status/report, false owner lineage/approval, other ZIP parts, extra shared-string edits, wrong target, generator stale text/formula/validation, and global/worksheet names. Test-only ACCEPT records are explicitly fictional fixtures, separate from production evidence.

Two actual f02/f08 builds match the independently accepted artifacts exactly. All other 9 buyer files plus MANIFEST, original owner-template directory and file 04 are unchanged against base beffff4dd6f4abaee625e4aff32dab11fd9c1a0b. Full S1 suite: 105 PASS, 4 existing openpyxl read warnings, 109.47s. Activated narrow suite: 24 PASS. git diff --check: PASS.

Visual evidence covers the changed 02 sheet and complete A12 text in a single-sheet Calc preview. Default Calc PDF still clips 08 horizontally; this is not a native Excel print PASS. Fresh native Excel acceptance of the changed text remains false. Final legal and release gates remain open.
