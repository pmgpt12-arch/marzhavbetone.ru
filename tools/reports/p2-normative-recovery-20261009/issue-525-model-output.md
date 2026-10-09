# P2 independent model output — Issue #525

Provenance: exact OpenRouter anthropic/claude-opus-5.5 one attempt, recorded 2026-10-09. This is recovered model output from the dispatcher log; the original detailed JSON was ignored by git and not committed. For form 01, this verdict covers the earlier semantic version; the corrected version requires a fresh review.

```text
[Reading 35 lines from start (total: 35 lines, 0 remaining)]

2026-10-09T02:25:22Z executor: attempt=1 requested=OpenRouter/anthropic/claude-opus-5.5 actual=OpenRouter/anthropic/claude-opus-5.5 timeout=600s
Using the OpenRouter credential from the unencrypted global credential file /home/denis/.ori/credentials.json; run `ori auth migrate` to use OS credential storage.
Отчёт написан и проверен, но я не смог его застейджить или закоммитить. Песочница запросила разрешение на `git add -f tools/reports/p2-normative-05-20261009/review.json`, и я его не получил. Сейчас файл лежит в рабочей копии и игнорируется (`git status --ignored` показывает `!!`). Его нужно добавить диспетчеру, иначе результат останется только в игнорируемом файле:

```
git add -f tools/reports/p2-normative-05-20261009/review.json
git commit -m "P2: normative review of form 05"
```

**Вердикт: PASS**, эскалация не нужна. Форма 05 не противоречит ст. 708, 452 и 743 ГК РФ:
- Она только рассчитывает влияние на срок: предлагаемая дата стоит рядом с действующей, а срок меняется соглашением 12.
- Документ односторонний, заказчик лишь отмечает получение. Изменением договора форма себя не называет.
- Об оплате в форме ничего нет.
- Уведомление 03 она не подменяет и не утверждает, что ожидание решения или приостановка сами продлевают срок.
- Деления на маршруты А и Б в форме нет. Строка «Основание» подходит обоим маршрутам, и для Б противоречия с п. 4 ст. 743 нет.

Найдено четыре мелких замечания, на вердикт они не влияют:
1. Колонку «Новая дата» лучше назвать «Предлагаемая дата».
2. В строку «Согласование» стоит добавить пункт договора о порядке изменения сроков (п. 2 ст. 708).
3. Реквизиты соглашения 11 на шаге 4 инструкции обычно ещё неизвестны. Предлагаю «если уже подписано».
4. В таблице инструкции форма 05 отнесена только к случаю А. Но в случае Б шаг 7 ведёт к соглашению 12, а оно ссылается на обоснование 05. Нужно исправить таблицу на «А, Б» и дополнить шаг 7.

Приказ № 344/пр в применимые нормы формы 05 не входит, и в её тексте на него ссылок нет. Поэтому его редакцию я здесь не сверял.

**Что изменено:** создан только `tools/reports/p2-normative-05-20261009/review.json`. Форму 05 я не правил.

**Чем проверено:**
- `python3 tools/semantic_hash.py` для формы 05 даёт `sha256:f8064e88…58da0`, совпадает с задачей. Сырой sha256 DOCX совпадает с `receipt.json`.
- Распаковать DOCX песочница не дала. Поэтому я восстановил текст формы 05 и инструкции из их скриптов сборки, и хеши совпали с semantic hash точно. Значит, проверялся текст текущих файлов.
- Хеши всех трёх норм пересчитаны через `jq` и `sha256sum` по правилу `tools/legal_evidence.py` и совпадают с сохранёнными. Каждая фраза сверена с полным текстом статьи из сохранённого источника КонсультантПлюс. Редакции взяты из этих источников (сохранены 09.10.2026), по сети заново не проверялись.
- Структуру JSON и состав норм проверил `jq -e`.

**Чего не хватило:** чтения файлов `~/.config/ai-business-os/Marzha_Factory_P0.md` и `Marzha_Communication_Standard.md`. Песочница его не разрешила, поэтому язык отчёта по стандарту не сверен. Это же записано в `acceptance_note`.
2026-10-09T02:31:02Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
2026-10-09T02:31:02Z Исполнитель: requested=OpenRouter/anthropic/claude-opus-5.5 (контракт Issue, transport openrouter_api, fallback forbidden); actual=OpenRouter/anthropic/claude-opus-5.5; попыток 1 из 1, лимит попытки 600с; каталог live; стоимость: not_metered.
```
