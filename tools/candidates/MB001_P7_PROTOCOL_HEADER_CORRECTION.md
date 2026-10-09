# P7 B1 protocol header correction

AUTHOR CANDIDATE, independent acceptance required. No Word/legal/private-reference or SALE_READY claim.

{
  "issue": 401,
  "parent": "554cd52edf2f3f75b0182db13d64927e136c92c4",
  "worktree": "/home/denis/projects/marzhavbetone.ru/.worktrees/codex-p7-header-401-20261005",
  "branch": "codex/p7-header-401-20261005",
  "source_sha256_before": "1299ec0cdf1d88bf982a91db03ed79986e255f4917ee19ee4a94b8e7c704c28b",
  "source_sha256_after": "96e0b2177c4935758fedbc86a9657ea79124b67a6a7aadd8be28a749d7db8c46",
  "only_OOXML_change": "first protocol row trPr/tblHeader",
  "all_other_parts_equal": true,
  "old_negative": "FAIL missing tblHeader",
  "new_positive": "PASS header flag and actual Writer every protocol-table page",
  "printed_pages": 12,
  "headers_per_page": [
    true,
    true,
    true,
    true,
    true,
    true,
    true,
    true,
    true,
    true,
    true,
    false
  ],
  "signature_only_last_page_excluded": true,
  "initial_bad_gate": "required header also on signature-only page; diagnosed and narrowed, product unchanged",
  "targeted_tests": "pytest targeted suite exited0; stdout not retained, no count claimed",
  "LLM_author_calls": 0
}

Old generator exactly reproduces old10; new generator exactly reproduces new10. All bytes except document.xml unchanged; removing first-row tblHeader reproduces old document.xml exactly. Buyer originals other than10 unchanged. Existing reviewer fictional filled fixture reused only as author supplemental rendering; fresh reviewer must independently verify. Actual Writer PDF repeats both captions on every protocol-table page; signature-only last page excluded. Full text and normative clauses unchanged. Existing P7 nonblocking N1-N5 remain; only B1 addressed. No site deployment or changes to untouched02-09.
