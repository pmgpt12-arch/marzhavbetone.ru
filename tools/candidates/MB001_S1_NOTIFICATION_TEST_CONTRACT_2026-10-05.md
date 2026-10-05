# Notification acceptance test contract correction

Scope: exactly two stale assertions in tools/test_s1_candidate.py. The agreed customer notification06 contains only the letter; its internal guidance belongs in algorithm03 step8. The existing all-DOCX disclaimer assertion now requires disclaimer in03 and explicit coverage of06. The attachment-print assertion now checks retained guidance in03 and absence of old export instruction in06. No product/source builder or buyer file changed from author439950106cceb546bab766e09cb6d02ceb98febb3a7.

Observed coordinator validation: 71 tests PASS in106.76s, covering notification5, A4, unique fields and existing S1 candidate checks. Test evidence in ROOT/notification-test-contract-20261005-1530/tests.stdout. Author negative fixtures show old source fails three notification tests. Independent frozen-output review is still required before merging author439. Whole-product, legal and release gates remain open.
