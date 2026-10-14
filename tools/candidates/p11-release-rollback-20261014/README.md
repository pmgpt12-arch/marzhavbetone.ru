# P11 — контролируемый release/rollback-кандидат

Статус до независимой проверки: `PASS_AUTHOR_RELEASE_ROLLBACK_CANDIDATE_ONLY` — 32/32; независимая exact-head приёмка PENDING; release HOLD.

Это следующий изолированный этап после принятого PR #634. Он не меняет корневой runtime, server-local config, действующую выдачу, цены, SKU или оплату и ничего не развёртывает.

## Точный вход

- base: `297fdd6560dd158dc463c2e128ed580f1cdb17a2`;
- `products-config.php` blob `1d2a0225c3974d0fd44b9011b1b06803ceadb16e`;
- `download.php` blob `f642cf899acf0915e27ced6f626bdc78424c41c9`;
- `payment.php` blob `917edd032f203563dafff86d553c3863925082f1`;
- принятый ZIP SHA-256 `f365039ef568dbbe9c661a6e1f553d21ddd0b086c9172f1e5a4340fb7dfe7f70`;
- принятое отдельное письмо SHA-256 `c8f9d78cf2335f2acf52ab8d12258e4e3e799c9c87e3447edcc17c7f0f507ea5`;
- принятый builder/fixtures PR #633 и независимая HTTP-квитанция PR #634 SHA-256 `63b60bd8a1a00b172c4ebac53cdf59b6a6d997667563c42504eb795b3fe1b906`.

Любой drift останавливает сборку.

## Что строится

`build_release_candidate.py` повторно использует побайтно принятые outputs привязки для `products-config.php` и `download.php`. Единственная новая runtime-дельта — серверное назначение точного P11 edition в `payment.php` после серверной валидации SKU/цены, но до записи заказа и обращения к платёжному провайдеру.

Клиентские `price`, `name` и `edition` отбрасываются. При выключенном флаге или отсутствии точных источников новый P11 получает 503 до создания заказа и до provider-вызова.

Генерируются:

- `release-candidate.patch` — только три exact-source runtime-файла;
- `rollback-candidate.patch` — точное возвращение этих трёх файлов;
- `build-manifest.json` — SHA входов, outputs и обоих patch.

## Авторская проверка

`verify_release_candidate.py` выполняет только приватные временные PHP/CLI fixtures:

- точные SHA источников и принятых артефактов;
- детерминированную двойную сборку;
- PHP lint трёх outputs;
- синтетический P11 checkout с отключёнными native curl/mail и локальным provider-stub;
- сохранение серверного edition до provider-вызова;
- игнорирование клиентских цены/имени/edition;
- отказ без заказов/provider-side-effects при выключенном флаге и отсутствующем ZIP;
- `git apply --check --unidiff-zero`, применение release patch, byte-equivalence outputs, применение rollback patch и полное восстановление исходных байтов.

Реальные ЮKassa, webhook, SMTP, mailbox, production paths, server config, deploy и live orders не используются.

Фактический результат: **32/32 PASS**, exit 0. Outputs: products-config `a6427bdd…447dd` и download `2ccd9b25…91c92d` побайтно равны уже принятой привязке; новый payment-кандидат `10b1a663…3cbc9`. Release patch SHA-256 `b64a1c172a6787b5b163f21035dd37d10e8872d88c912df8f5de2adf55654f69`; rollback patch SHA-256 `395303d0e06ccec86bcaf2165a592344631b64db603c4a859dc59dd209758625`. Протокол `author-acceptance-v3.json` SHA-256 `bc3807e32fe551f4bb20625081031fc68b36993d0e45fb55d5fa82a20f1c2a54`.

Две ранние попытки не выдаются за PASS. Первая остановилась до payment-check из-за same-file curl-stub; вторая доказала, что PHP CLI не заполняет `php://input` из stdin. Диагнозы и неизменённые failure receipts сохранены в coordinator state. Узкое исправление harness использует `auto_prepend_file` для provider-stub и единственную проверяемую подстановку `php://input` → `STDIN` только во временной fixture-копии; кандидатные runtime-байты не менялись.

## Воспроизведение

```sh
python3 tools/candidates/p11-release-rollback-20261014/build_release_candidate.py \
  --repo . \
  --output-dir tools/candidates/p11-release-rollback-20261014

python3 tools/candidates/p11-release-rollback-20261014/verify_release_candidate.py \
  --repo . \
  --output tools/candidates/p11-release-rollback-20261014/author-acceptance-v3.json
```

Даже PASS этого этапа означает только проверенный candidate package. Production source nomination, права/пути, actual checkout/callback/provider, SMTP, rollout и rollback остаются отдельными gates. G1–G8 — 0/13, release HOLD.
