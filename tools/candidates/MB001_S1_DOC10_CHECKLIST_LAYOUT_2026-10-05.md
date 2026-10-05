# S1 file 10: checklist row pagination

Only f10 first readiness checklist table receives cantSplit on its 13 rows, tblHeader on its header, and keepNext on header paragraphs. No font size, text, placeholders, court body, appendix table, native clean-copy instructions or other generator functions change. Existing appendix cantSplit/tblHeader flags are untouched.

Two actual f10 rebuilds are byte-equal at SHA256 d8d0cafe7849bc523cd8a2c9cf1e5c7056cf75a9bfd0146c2c7cf1fc7bd3be55. Text and all placeholders, 12 checklist items, 18 blank appendix rows and every other 10 buyer files plus MANIFEST match base 36c03150ac3b256621baaf144147cf490bfcf3f7. The only changed ZIP part is word/document.xml; canonical XML is identical after removing the first-table flags introduced by this change. AST comparison changes only f10.

Scoped court/assembly tests: 13 PASS, 58 deselected, 7.21s; output is in evidence/tests.out. Writer exported six A4 pages with a separate profile; page PNGs are rendered at scale-to 1400. Root viewed all six PNG pages and accepted the atomic first-table layout: row 7 is whole on page 2, the header repeats, no clipping/overlap observed, remaining sections readable. Root receipt pins exact source DOCX and all six PNG hashes. This grants no whole legal or sale/release acceptance. Commit/push are authorized; no main merge or publication.
