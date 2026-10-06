# S1: actual merged snapshot 6077 — final mechanical verification

execution_pattern: one_shot
primary_result: final_actual_merged_S1_full_tests_and_two_complete_rebuilds
feedback_loop_required: false
checkpoint_policy: verified_only
frozen_input_sha: 6077a5d6cdba42cbef6f2452b799b5c118f8c5d2

VERIFIED snapshot after working-branch merge #473. This proof remains pinned to6077; later f03 guidance increments require their own narrow composition proof and do not rewrite these results.

Full suite executed once:105 passed,4 named openpyxl read warnings,104.36s pytest time; exit0, no named skips. Wall time of the test command105.38s; entire independent parallel pipeline106.29s within bounded200s. Two ACTUAL complete CLI S1 builds executed independently, exit0,3.67s/3.62s. Three detached worktrees prevent shared R.ROUTE_MAP races.

| Check | Verified result |
|---|---|
| All12 generated outputs | build1=build2=tracked6077=independentlyaccepted output source |
| Native owner04 | SHA256f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9; raw owner bytes preserved |
| Reviewed correction02 | SHA2565918714b4e4e95abc546e1fe7a43f515af50680ecf75352a2949a2ebecac47f0 |
| Reviewed correction08 | SHA256e0ed0206c17f1b3638bba14dd472c3acad0da80c87dd640169e9c094dec266b4 |
| Helpers/templates/registries/review report | All12 checked paths byteexact against accepted d0d484b31945e39b93acc1fb6b4f5ac7333202ca |
| RISKS/f02/f08 AST | Exact accepted d0d484 overlay, including new02 risk wording |
| f01 AST + output | Exact accepted3f22f63cbbd838d6b7cef1c01f2d8863f82dbaad |
| f03 AST + output | Exact accepted473source4f86bf1aa88aef4b2b085d96ed998bd3ed70ba45 |
| f10 AST + output | Exact accepted472sourcec19c63ac56e9217c8c544ba9b1c68b5700a25324 |
| Route map | Bothbuilds=tracked6077=acceptedoverlay; SHA2561e5d5f5b4862cd66627a6610e3883ec39c943493c8273feed2d7729850689501 |
| Post-execution trees | tests/build1/build2 all clean |

The four warnings name test_libreoffice_прогон, test_допработы_выход_B5_маршрут, test_н2_детальная_проверка_называет_ситуацию_В and test_н3_детальная_проверка_не_теряет_вторую_границу. openpyxl warns about unsupported DataValidation extension during reading. Owner/native artifact bytes were separately compared and remain unchanged.

Exact test command:
```text
timeout --kill-after=5s 180s python3 -m pytest -q tools/test_s1_a4.py tools/test_s1_candidate.py tools/test_s1_court_appendices.py tools/test_s1_court_clean_copy.py tools/test_s1_notification_print.py tools/test_s1_reviewed_excel_corrections.py tools/test_s1_unique_fields.py tools/test_approved_s1_excel.py
```

Actual build commands, each from its own detached6077worktree:
```text
timeout --kill-after=5s 120s python3 tools/build_s1_candidate.py --out /home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/s1-final-verification/build-1
timeout --kill-after=5s 120s python3 tools/build_s1_candidate.py --out /home/denis/.local/state/claude-dispatcher/recovery-20261005/mechanical/s1-final-verification/build-2
```

Orchestration: timeout --kill-after=5s 200s python3 verify.py. Actual cwd/commands/exits/times are in tests-execution.json, build-1-execution.json and build-2-execution.json. final-proof.json contains all fullSHA source mappings and output hashes; tests.log names warnings; both build directories preserve actual generated artifacts. SHA256SUMS.txt authenticates receipt/code/log/output files.

This is mechanical integration/build acceptance. Native Excel acceptance of the new correction text remains false, official currentness NOT_VERIFIED, human legal acceptance NOT_PERFORMED, sale_ready false. No source edits, merge/deploy or model API calls were performed by this verification.
