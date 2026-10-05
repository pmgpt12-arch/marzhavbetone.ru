# P2/P3 — current composition inputs (2026-10-05)

## Паспорт до проверок
- execution_pattern: one_shot
- primary_result: P2_P3_current_composition_inputs
- feedback_loop_required: false
- checkpoint_policy: verified_only
- Цель: закрепить актуальные принятые corrections в original working candidates P2/P3 и установить достаточные входы следующей composition; не повторять правовую или продуктовую экспертизу.
- Exact site base: 64b210e5ed4d631f74aee8f0e345fcc87ff1760e.
- P2: Issue305 → PR312, head1be0493ae194b2647c4b22c98e9981b9c5e64a54; original integration PR405, accepted N1/N2 report396, N3 report399/PR395.
- P3: Issue304 → PR314, headf8bfdc569b9d561b87595aa9d6b5f28f76871e02; original integration PR404, accepted C1/C2 report394.
- PR313 относится к T2, PR315 к P7: в P2/P3 эту нумерацию не использовать.
- Paired source: AIOS PR560+564 для P2, source currentmain79dd869b2f4bea4482d62bef046367f1b42ce4c1; AIOS PR532 head3313ca9cab02e3384c4a4e6bf6d99002d6f7a63e для P3.
- Scope: read-only inspections, own pinned Git refs/worktree snapshots, existing targeted tests/rebuild into run directories; durable sourcepin/commands/evidence/report only.
- Acceptance: live PR/currentmain metadata + commit ancestry + accepted product blob equality + isolated source rebuild/hash + targeted test actual results; list unresolved observations/gates separately from failures.
- Negative cases: productready не следует из mergedworkingbranch; accepted earlier SHA недостаточен без blob equality; skipped тест не считать PASS; missing pair source не восполнять догадкой; legal verdict по старому contenthash не переносить.
- Запреты: runtime/main/sku/pricing/payment/contacts/public deploy; никакие paidmodels/новая legalreview. Не запускать existing evidence script build00.py: он hardcodes author WT и копирует outputs обратно. Для доказательства source rebuild копировать генератор в изолированный run, accepted sources не менять.
- DONE: этот паспорт + hash/metadata/commands evidence + проверенный exact remote commit отчёта. Следующий writeunit выделяет root после чтения результата.

## Результат наблюдений и supersession
Это historical receipt исходного снимка, а не current readiness verdict. Root сообщил о последующих accepted changes; проверен live GitHub readback и ancestry.

- На pinned P2 1be0493…: существующие tests `test_p2_forms_buyer_text.py test_p2_kit_instruction.py test_delivery_artifacts.py` дали **28 passed, 6 xfailed**, exit0. Xfails не считаются закрытием STOP02/04/05.
- На pinned P3 f8bfdc56…: `test_p3_buyer_kit.py test_delivery_artifacts.py` при доступном существующем reportlab дали **34 passed, 1 failed**, exit1; failure `test_generator_reproduces_delivered_files` был только producer metadata двух XLSX02/06. Остальные ZIP parts byte equal; semantic hashes совпали.
- **Этот FAIL superseded**, не текущий дефект. PR459 merged2026-10-05T13:41:25Z: accepted source4135aba99e392cf805efcae40cd81f02a571197a → actual original P3 head302d2e4d44bea16508b8e6e64211a2d10953aa51. Обе ancestry проверки старогоhead и fix→actualhead exit0. Точный source diff в JSON: freezer canonizes Application label Microsoft Excel. Body PR459 сообщает35testsPASS; повторный запуск без новых изменений не нужен и здесь не выполнен.
- P3 PR314 всё ещё OPEN; working merge459 не равен release/main merge. P2 PR312 likewise working candidate.
- AIOS560+564 source already mergedmain79dd869b2f4bea4482d62bef046367f1b42ce4c1; старый drafted sourcegate PR405body не использовать как текущую блокировку. AIOS532 P3 snapshot3313ca9cab02e3384c4a4e6bf6d99002d6f7a63e оставалсяOPEN при исходном чтении.
- Не выдаю complete source-to-buyer reproduction/Word/Excel/legal/release PASS на основании этого неполного старого снимка. Root уже ведёт newer actual merged evidence; не дублировать accepted checks. Изолированные источники не изменены.
- Raw outputs, argv, ancestry и current fixdiff сохранены в `MB001_P2_P3_COMPOSITION_EVIDENCE_2026-10-05.json`. Git receipt допустим в authorized workingbranch; publicrelease gates отдельно.

Command used (cwd isolated pinned p2/p3 WT):
```sh
PYTHONPATH=/home/denis/projects/ai-business-os/.venv/lib/python3.12/site-packages PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -rx -rs -p no:cacheprovider <targeted test files above>
git merge-base --is-ancestor f8bfdc569b9d561b87595aa9d6b5f28f76871e02 302d2e4d44bea16508b8e6e64211a2d10953aa51
git merge-base --is-ancestor 4135aba99e392cf805efcae40cd81f02a571197a 302d2e4d44bea16508b8e6e64211a2d10953aa51
```
