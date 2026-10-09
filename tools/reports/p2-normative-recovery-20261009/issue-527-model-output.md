# P2 independent model output — Issue #527

Provenance: exact OpenRouter anthropic/claude-opus-5.5 one attempt, recorded 2026-10-09. This is recovered model output from the dispatcher log; the original detailed JSON was ignored by git and not committed. For form 01, this verdict covers the earlier semantic version; the corrected version requires a fresh review.

```text
[Reading 28 lines from start (total: 28 lines, 0 remaining)]

2026-10-09T02:37:55Z executor: attempt=1 requested=OpenRouter/anthropic/claude-opus-5.5 actual=OpenRouter/anthropic/claude-opus-5.5 timeout=600s
Using the OpenRouter credential from the unencrypted global credential file /home/denis/.ori/credentials.json; run `ori auth migrate` to use OS credential storage.
Отчёт написан, вердикт **PASS**, но закоммитить его я не смог. Песочница не пропустила `git add -f tools/reports/p2-normative-11-20261009/review.json`, поэтому коммита нет. Файл пока лежит в игнорируемой папке как `!!`. Обходить запрет я не стал. Нужно выполнить `git add -f` и закоммитить файл с вашей стороны или со стороны диспетчера, иначе результат останется только в игнорируемом файле.

**Итог проверки формы 11**
- Нормы gk-743, gk-744, gk-709, gk-452 и gk-160 проверены по полным текстам статей. Противоречий нет ни по маршруту А, ни по маршруту Б, ни для смешанного случая.
- Форма — двустороннее письменное соглашение с подписями уполномоченных лиц. Поэтому называть его изменением договора правильно.
- Автоматическую оплату форма не обещает. Пункт 3 прямо говорит, что подписание не заменяет приёмку.
- По маршруту Б форма не утверждает, что у подрядчика было право на оплату без сообщения заказчику по п. 3 ст. 743.
- Проверка человеком не нужна (`escalation_required: false`).
- Два мелких замечания, на вердикт не влияют:
  1. В п. 1 формы основание по маршруту Б привязано к поручению 01, которого при этом маршруте обычно нет. В отчёте предложена формулировка.
  2. Инструкция отсылает к разделу «Основание», а в форме 11 такого раздела нет.
- order-344-appendix-3 к форме 11 не относится: форма не ссылается на приказ 344/пр и на акт скрытых работ. Поэтому редакцию приказа я не сверял, на вердикт это не влияет.

**Изменено:** создан только `tools/reports/p2-normative-11-20261009/review.json` в нужной структуре. Сама форма не правилась.

**Чем проверено:**
- `python3 tools/semantic_hash.py` даёт `sha256:5448777…c79e0e`, это совпадает с заданием. Сырой sha256 файла DOCX совпадает с `receipt.json`.
- Распаковать DOCX песочница не дала. Поэтому я восстановил текст из генератора `form11()` и посчитал по нему хеш тем же правилом, что в `semantic_hash.py`. Хеш совпал с хешем документа, значит проверялся именно текущий текст формы.
- Все пять `source_hash` пересчитаны через `jq` по правилу `tools/legal_evidence.py:55` (метка редакции плюс нормализованный текст), все совпали. Каждая фраза формы сверена с полным текстом статьи из этих файлов, без опоры на память.
- `jq -e` подтвердил, что отчёт — корректный JSON с пятью нормами.

**Что не удалось проверить:**
- Текст инструкции я взял из её генератора и с самим DOCX по хешу не сверял. Инструкция здесь только общий контекст.
- Файлы `Marzha_Factory_P0.md` и `Marzha_Communication_Standard.md` песочница прочитать не дала. Язык отчёта по стандарту не сверен, и это отмечено в `acceptance_note`.
2026-10-09T02:44:36Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
2026-10-09T02:44:37Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
```
