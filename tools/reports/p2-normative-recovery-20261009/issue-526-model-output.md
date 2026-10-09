# P2 independent model output — Issue #526

Provenance: exact OpenRouter anthropic/claude-opus-5.5 one attempt, recorded 2026-10-09. This is recovered model output from the dispatcher log; the original detailed JSON was ignored by git and not committed. For form 01, this verdict covers the earlier semantic version; the corrected version requires a fresh review.

```text
[Reading 32 lines from start (total: 32 lines, 0 remaining)]

2026-10-09T02:31:19Z executor: attempt=1 requested=OpenRouter/anthropic/claude-opus-5.5 actual=OpenRouter/anthropic/claude-opus-5.5 timeout=600s
Using the OpenRouter credential from the unencrypted global credential file /home/denis/.ori/credentials.json; run `ori auth migrate` to use OS credential storage.
Отчёт готов: вердикт **PASS**, два замечания уровня minor. Закоммитить его я не смог: песочница не дала выполнить `git add -f`, она требует разрешения. Сейчас файл лежит только в рабочей копии и попадает под игнорируемое правило `reports/`. Диспетчеру нужно выполнить:

```
git add -f tools/reports/p2-normative-06-20261009/review.json
git commit -m "P2: normative review of form 06 (suspension notice)"
```

**Вывод по форме 06.** Существенного противоречия со ст. 743 и 716 ГК РФ нет.
- **Границы приостановки.** Останавливаются только названные позиции и участок, остальные работы записаны отдельно как продолжающиеся. Это совпадает со словами «соответствующие работы» в п. 3 ст. 743.
- **Уведомление и доставка.** Приостановка опирается на уведомление 03 с подтверждением доставки. Доставка самого письма 06 и отметка о получении записываются отдельно.
- **Оплата и договор.** Расходы простоя форма только записывает и возмещения не обещает. Изменением договора себя не называет: подпись только подрядчика.
- **Маршруты А и Б.** По инструкции форма 06 нужна только в маршруте А. Для маршрута Б она не применима и п. 4 ст. 743 не обходит.

**Замечания (на вердикт не влияют):**
1. В строке «Срок» назван только срок по договору. Предложено добавить запасной: десять дней по п. 3 ст. 743, как уже сделано в форме 03.
2. Форма построена под порядок ст. 743: сначала уведомление, потом ожидание ответа. Нет выбора основания приостановки по п. 1 ст. 716, где предупреждать и останавливать работу нужно сразу. Если ждать срок в таком случае, по п. 2 ст. 716 можно потерять право ссылаться на это обстоятельство. Предложена строка «Основание приостановки» с двумя вариантами.

Норма order-344-appendix-3 к форме 06 не относится: форма не ссылается на приказ № 344/пр. Поэтому её редакцию я не сверял.

**Чем проверено:**
- `python3 tools/semantic_hash.py` даёт `sha256:a6bda5d4…89c08`, совпадает с заданием. Сырой sha256 файла совпадает с `receipt.json`.
- Распаковать DOCX песочница не дала. Поэтому я восстановил текст формы из генератора `build_paid_02_remaining_forms.py` и посчитал хеш по тому же правилу: получилось ровно `a6bda5d4…`. Значит, проверялся текст текущего файла. Так же сверена инструкция `00-INSTRUKCIYA.docx` (`e488a729…`).
- Хеши источников gk-743 и gk-716 пересчитаны по правилу `tools/legal_evidence.py` и совпали с сохранёнными. Каждая фраза о норме сверена с полным текстом статьи из сохранённых файлов КонсультантПлюс.
- JSON проверен через `jq`.

Файлы `Marzha_Factory_P0.md` и `Marzha_Communication_Standard.md` песочница прочитать не дала, поэтому язык отчёта по стандарту не сверен. Это отмечено и в самом отчёте.

**Что изменено:** создан только `tools/reports/p2-normative-06-20261009/review.json`, форма не правилась. Коммита, push и PR нет.
2026-10-09T02:37:33Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
2026-10-09T02:37:33Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
```
