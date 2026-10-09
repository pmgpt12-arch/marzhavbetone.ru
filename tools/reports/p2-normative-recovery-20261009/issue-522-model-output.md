# P2 independent model output — Issue #522

Provenance: exact OpenRouter anthropic/claude-opus-5.5 one attempt, recorded 2026-10-09. This is recovered model output from the dispatcher log; the original detailed JSON was ignored by git and not committed. For form 01, this verdict covers the earlier semantic version; the corrected version requires a fresh review.

```text
[Reading 29 lines from start (total: 29 lines, 0 remaining)]

2026-10-09T02:06:47Z executor: attempt=1 requested=OpenRouter/anthropic/claude-opus-5.5 actual=OpenRouter/anthropic/claude-opus-5.5 timeout=600s
Using the OpenRouter credential from the unencrypted global credential file /home/denis/.ori/credentials.json; run `ori auth migrate` to use OS credential storage.
Форма 01 прошла нормативную проверку: вердикт **PASS**, существенных противоречий с нормами gk-743, gk-744, gk-452 и gk-160 нет. Форму я не менял.

**Вывод по существу**
- Документ называет себя поручением, а не изменением договора. Если меняются цена, срок или другие условия, форма прямо требует соглашения сторон.
- Оплату форма не обещает. Цену и срок она отправляет в отдельные документы: расчёт 07, обоснование 05, соглашения 11 и 12.
- Полномочия инициатора и обоих подписантов записываются.
- Форма относится только к маршруту А, когда работы ещё не начаты. Это совпадает с инструкцией. Маршрут Б к ней не применяется.
- Нашёл два мелких замечания, на вердикт они не влияют. Предлагаемые исправления записаны в отчёте:
  1. Фраза «заполненные ссылки указывают, какие условия согласованы отдельно» неточна. Расчёт 07 и обоснование 05 — это не согласованные цена и срок. Кроме того, по инструкции соглашение 11 оформляют уже после поручения, поэтому при подписании поручения это поле обычно пустое.
  2. В тексте формы прямо не сказано, что поручение оформляют до начала работ. Предложил добавить эту оговорку, чтобы форму не заполняли задним числом.
- Норма order-344-appendix-3 к форме 01 не применяется: форма не воспроизводит акт скрытых работ. В сохранённых данных есть только исходный текст приложения 2023 года. Поэтому для формы 04 вопрос о редакции 23.06.2025 остаётся открытым.

**Что изменено**
- Создан только `tools/reports/p2-normative-01-20261009/review.json`.

**Чем проверено**
- `python3 tools/semantic_hash.py …01-prikaz-na-dopobem.docx` дал `sha256:5f93881f…07f85`, это совпадает с заданием. Сырой sha256 файла совпадает с `receipt.json`.
- Распаковать DOCX песочница не разрешила. Поэтому я восстановил текст формы из генератора `build_paid_02_remaining_forms.py` и посчитал его хеш по тому же правилу. Хеш совпал точно, значит, проверялся текст именно текущего файла.
- Все четыре source_hash я пересчитал по правилу `tools/legal_evidence.py`, и они совпали с `full-evidence.json`. Каждую фразу формы сверял с полным текстом статьи из этого файла, без памяти.
- `jq` подтвердил, что JSON корректен.

**Что требует внимания**
- Правило `reports/` в `.gitignore` игнорирует новый файл: в `git status` он помечен как ignored. Его нужно добавить через `git add -f`, как и остальные отчёты в `tools/reports/`. Коммит я не делал.
- Песочница не дала прочитать `Marzha_Communication_Standard.md` и `Marzha_Factory_P0.md`, поэтому текст отчёта по стандарту языка не сверен.
- Текст инструкции я брал из её генератора. Совпадает ли он с текущим `00-INSTRUKCIYA.docx`, не проверял.
2026-10-09T02:11:43Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
2026-10-09T02:11:43Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
```
