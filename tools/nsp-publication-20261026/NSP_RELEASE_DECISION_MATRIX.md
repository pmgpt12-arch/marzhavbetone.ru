# НСП — руководящая матрица ТЗ №4.2

**Статус:** PARTIAL_READY_WITH_BLOCKERS. Выпуск и merge запрещены. 

| SKU | QA / версия | Staging | Release | Действие | Блокер |
|---|---|---|---|---|---|
| P1 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P2 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P3 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | PREVIOUS_RELEASE_PRESERVED | Сохранить действующую продажу, проверить регрессию | Existing buyer route E2E not reverified |
| P4 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P5 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | PREVIOUS_RELEASE_PRESERVED | Сохранить действующую продажу, проверить регрессию | Existing buyer route E2E not reverified |
| P7 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P8 | READY_CANDIDATE / 07a16f0d80fe | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | P8 later accepted edition unverified; HOLD |
| P9 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P10 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P11 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| P13 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| T2 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| T3 | NOT_FINAL_VERIFIED_IN_THIS_PUBLICATION / нет | NOT_TESTED | HOLD | Оставить анонс, серверный POST=409 | Final paid QA/release permission absent |
| FREE/checklist | FULL_QA_PASS / bd50ad14084f | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/dengi | FULL_QA_PASS / 024fe485d70b | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/dop-raboty | FULL_QA_PASS / e09176633507 | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/vozvrat-ks | FULL_QA_PASS / f0ffd8d55a44 | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/uderzhaniya | FULL_QA_PASS / 77ef9381b960 | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/dogovor | FULL_QA_PASS / b9a3fd2bb0e9 | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/bankrotstvo | FULL_QA_PASS / 68a1d82c16fb | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | QA04 Git provenance EVIDENCE_MISSING; release HOLD |
| FREE/avans | FULL_QA_PASS / 06d8e851d8bc | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/raschet-metrami | FULL_QA_PASS / bacf5f6cfacb | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/ispolnitelnaya-dokumentaciya | FULL_QA_PASS / 10c811a26bf0 | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |
| FREE/akt-skrytyh-rabot | FULL_QA_PASS / 85836ca18e58 | NOT_TESTED | HOLD | Анонсировать до разрешённой новой выдачи | Release HOLD; staging HTTP and browser not verified |

## Выпуск
- 11 бесплатных имеют FULL_QA_PASS и SHA источников; отдельного разрешения на выпуск нет.
- QA04: EVIDENCE_MISSING для Git-коммита при наличии проверенного локального архива.
- P8: QA01 READY_CANDIDATE, не FULL_QA_PASS, новая продажа закрыта.
- P3/P5: предыдущий выпуск сохранён, E2E новый не заявлен.
- Новая выдача исторических архивов заблокирована в `lead.php`, прямые старые статические `/downloads/*` не удалены.
- Browser/HTTP staging QA и выпуск только после отдельного прохода. PR #677 draft.
