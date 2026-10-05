# S1 outgoing reconciliation act registration clarification

F7: instruction07 now explicitly includes the outgoing reconciliation act in its list of documents and requires a separate row in04 Transfer Register for the act sent to the customer at step6. Existing incoming-document instruction is preserved; the added paragraph explicitly says it covers documents received from the customer.

Only f07 builder body and07 DOCX changed; every other buyer file and every other source function is byte/AST unchanged. Native ZIP parts other than word/document.xml are identical to base. Two builds are byte-identical. No new legal assertion or source-currentness judgment.

Observed print QA: actual Writer PDF has2A4 pages. Coordinator opened both pages. The first rendering split the email row across pages; corrected locally in f07 with cantSplit for6 rows and repeated header. Final pdf-v2: rows stay whole, repeated header visible, added outgoing-act and original incoming-act paragraphs fully readable, no clipping or overlap. This small source-local pagination correction avoids changing common table helper or other documents. Base abe3939498336970af25891fecacfb8748eeca17; receipts ROOT/s1-outgoing-act-clarity-20261005-1540.

ACCEPTED by coordinator for narrow F7 instruction/pagination scope after mechanical and visual evidence. No whole-product, legal, price or publication acceptance. Working branch merge only after GitHub checks. F2 for04/10, F4 and F6 remain separate.
