```yaml
document: products-storage/01-zakrytie-rabot/13-uvedomlenie-o-prosrochke-oplaty.docx
document_hash: sha256:c98727eaf8b30694e31e5c8783aee012b088712886bf81da8af5a088adeab02d
generator_hash: sha256:5ec4c7717520f7d2ac08e5429cd2ca1dd833d398b230800f8aef2eb782bd64c6
checked_at: 2026-10-08
checker: normative-checker
sources:
  source0: &source0 "http://pravo.gov.ru/proxy/ips/?doc_itself=&nd=102079219&page=all&rdk=89"
  source1: &source1 "http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102033239&rdk=157&&empire="
norms_checked:
  - {norm_id: apk-4-5, source_hash: sha256:6603e670456f0ab3a8ec287c3626d56613e7623428a3c7ba937c8b0cc1a67d44, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-395, source_hash: sha256:07ae25b8650a6efb592a911c1ae0c8ff2ff876dfb8da065293113f120ac338bd, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-128-148, source_hash: sha256:5ab245b1975ce0794aaa5595c88088d4fa12e607e23d34c37bea8932e9b9628e, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-129, source_hash: sha256:77c6756834469e8b99a136cecf0a13a501356ceb7d1d79f14816f6ae59185262, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-330, source_hash: sha256:8c4714b2a6784a22607a162b1b5d63dcbc4063219d64100b963a096e80a9edb3, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-110, source_hash: sha256:f4204c910a45b86d889d836ffe5c334efb6a2105d093e59fe624a29fc120f815, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
verdict: PASS
issues: []
corrections: []
escalation_required: false
escalation_reason: null
```

Согласованы одна и та же ветка процентов/неустойки в основании и предупреждении, проверка даты начала/условий и удаление иной ветки. Неподтверждённое заявление о полной сверке16.08.2026 удалено.

Фикстуры применимого ожидания: общий срок от направления ещё не истёк; собственный ответ5дней истёк, ожидание нет; договор10дней от получения ещё не истёк. Во всех трёх STOP. Это ручное применение фактических инструкций, не календарный калькулятор и не проверка конкретного договора. Receipt: P1_final_batch_generated_acceptance_2026-10-08.json; для12 также P1_final12_generated_claims_acceptance_2026-10-08.json.

Тексты и редакции подтверждённых норм: P1_legal_freshness_consolidated_receipt_2026-10-08.json и P1_APK129_current_quote_2026-10-08.json. Файлы первичных источников: P1_durable_source_manifest_2026-10-08.json. Source hash связывает exact evidence, но для not_verified он не удостоверяет актуальность. Отсутствие доступа классифицировано как зависимость, не как юридический FAIL.

Для закрытия NOT_VERIFIED нужны текущие официальные тексты/редакции, сохранённое проверяемое evidence и новая сверка этого hash. Human-review закрывает только отдельную юридическую эскалацию и не заменяет официальный текст/evidence.
