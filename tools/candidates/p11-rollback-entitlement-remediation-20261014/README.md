# P11 — безопасный rollback уже выданного edition

Статус: `PASS_AUTHOR_ROLLBACK_ENTITLEMENT_TRANSITION_ONLY`. Это изолированный candidate/evidence-пакет; независимая exact-head приёмка PENDING. Release HOLD.

## Причина

Независимый probe из registry #600, comment 6164170624, обнаружил класс `ISSUANCE_SWITCH_COUPLED_TO_EXISTING_ENTITLEMENT_READS`: прежняя функция `mvb_p11_binding_valid()` одновременно проверяла идентичность edition и флаг новой выдачи. После выключения флага уже выданный корректный ZIP и письмо оставались на диске, но reader возвращал null.

Принятый PR #635 не переписывается и не объявляется ошибочно релизным. Этот пакет строит исправленный кандидат поверх точного merge `03ebb0f1970a295d69fc6e8bc175d9e1d5191f76`.

## Узкое исправление

- `mvb_p11_binding_valid()` проверяет только точную неизменяемую структуру edition.
- `mvb_p11_stage_edition()` отдельно требует `MVB_P11_CANDIDATE_BINDING === true`.
- Новая выдача при выключенном флаге по-прежнему останавливается до заказа и provider-side-effect.
- Уже выданный корректный edition после выключения новой выдачи продолжает отдавать точный ZIP и retained letter.
- Неизвестный, повреждённый или отсутствующий edition по-прежнему закрывается без расхода квоты.

Корневые runtime-файлы не изменены. Патчи опубликованы только внутри этого каталога.

## Авторская проверка

`verify_transition.py` использует приватную временную PHP/CLI fixture:

- 69/69 PASS;
- enabled issuance сохраняет exact accepted ZIP/TXT;
- disabled-before-first-order не создаёт новую выдачу;
- disabled-after-issued-order сохраняет callback, письмо и download exact bytes;
- повторный callback не отправляет второе письмо;
- corrupt identity при выключенном флаге даёт fail-closed без счётчика;
- historical P11/T6 и P1 regression сохраняются;
- внешний HTTP/provider/SMTP/model/live — 0.

`verify_release_candidate.py` повторно проверяет release/payment-кандидат:

- 32/32 PASS;
- client price/name/edition отброшены;
- server edition сохранён до provider stub;
- disabled/missing source отказывает до order/provider side-effect;
- release/rollback patch применяются и возвращают точные байты.

## SHA-256

- helper: `22988c10c51a769110a9cfdbfdff8955e7a99e987eb3ea30721616f71e9b5fa8`
- products-config output: `c2cc7e74a3f267723fb2a504f23a97dd4cf68b408b3f899b7a7292959c441de7`
- download output: `2ccd9b2507cfc7e64eeada608825f507b4c780cd898c4cdc799cdce67691c92d`
- payment output: `10b1a663ab40eaac22b17f8041d397daeb12cc9d07117b4a29a881aab063cbc9`
- release patch: `fbe5a1310f85b27ac38cf3d99edacbe8077769ca22fc125eff0d97b28be128c3`
- rollback patch: `3f36e478207d8222481674c2e8e2f7677d14d7065a65d0b3f3afeefd432c92b0`
- release acceptance: `5ed9083393ce9da506c49f893c3e76357d98dbe75dc533c72951428ad3575935`
- transition acceptance: `499dc46a4644036522635d45132c1533171a66aa75ed6993f31d9dd56ee2df64`

## Ограничения

Production source nomination, server paths/permissions, actual checkout/provider/callback, SMTP/mailbox, rollout and emergency rollback remain separate owner-gated gates. Этот пакет не применяет патч, не развёртывает код и не разрешает live. G1–G8 — 0/13, release HOLD.
