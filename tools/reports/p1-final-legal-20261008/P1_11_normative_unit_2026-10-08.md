```yaml
document: products-storage/01-zakrytie-rabot/11-slovar-poley.docx
document_hash: sha256:e6be105901473d4c47fe807b390c2ac8dd4700103637fb79f83df095ffcc5a3f
generator_hash: sha256:07333ff41837faba4195a4d89b54efd251f193e5788352bda28cec9d6c66b333
checked_at: 2026-10-08
checker: normative-checker
sources:
  source0: &source0 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102039276"
  source1: &source1 "http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102033239&rdk=157&&empire="
  source2: &source2 "http://pravo.gov.ru/proxy/ips/?doc_itself=&nd=102079219&page=all&rdk=89"
  source3: &source3 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102067058"
norms_checked:
  - {norm_id: gk-746, source_hash: sha256:8234d40258be23cd694a17f85a31430d3183d43aa1f8e43f34b0c51ee381239f, source_used: *source0, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-711, source_hash: sha256:8f6513bfebeb20b673b0772594deb336d8d665aae11936745cbc137afea91049, source_used: *source0, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-191, source_hash: sha256:464ff087a2d3d945f54b36c7e6c3ad38fd5b17f7c19a2a50d30ce852f5f2cac0, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-193, source_hash: sha256:ea6f7c3963bec9a3f7395b5772e41069e676c41c52a06779ea5092a521d11572, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-395, source_hash: sha256:07ae25b8650a6efb592a911c1ae0c8ff2ff876dfb8da065293113f120ac338bd, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-4-5, source_hash: sha256:6603e670456f0ab3a8ec287c3626d56613e7623428a3c7ba937c8b0cc1a67d44, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-125-126, source_hash: sha256:607a4103328f7a67401283a8cfe2b68893cb6c19dffadacd7e92100c1b7c4d30, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: nk-333-21, source_hash: sha256:9bbc4147e29d9ac82f3715096f20626d14cbc1a361c3a19f160e040f70b6abac, source_used: *source3, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: apk-35, source_hash: sha256:e5bada3501190b2b8dbab9ade625a9dadc38a2ba9f461368cbad1d20b65a60c4, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-37, source_hash: sha256:803b02c99e6e770221639289494473522f4eb47e145d4b9ad6748bce7fd8d225, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-330, source_hash: sha256:8c4714b2a6784a22607a162b1b5d63dcbc4063219d64100b963a096e80a9edb3, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-103, source_hash: sha256:b427064c0a4b88b083abf95d33057d742d97b4a0437fd9cce9be715333b8dcc3, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
verdict: NOT_VERIFIED
issues:
- id: CURRENT-11
  severity: material
  claim: Актуальность необходимых официальных норм на 08.10.2026
  norm_id: gk-746
  why: 'ACCESS/DEPENDENCY: не подтверждены текущие официальные тексты/редакции: gk-746,
    gk-711, nk-333-21'
corrections: []
escalation_required: false
escalation_reason: null
```

Исправлены неизменность всех подстановок и однократность заполнения: реквизиты и актуальные на дату суммы/сроки различаются. Для процентов используется14, для неустойки отдельный договорный расчёт. Цена иска/пошлина требуют обновления на дату подачи; формы01–05 используют собственные подписи полей.

Фикстуры применимого ожидания: общий срок от направления ещё не истёк; собственный ответ5дней истёк, ожидание нет; договор10дней от получения ещё не истёк. Во всех трёх STOP. Это ручное применение фактических инструкций, не календарный калькулятор и не проверка конкретного договора. Receipt: P1_final_batch_generated_acceptance_2026-10-08.json; для12 также P1_final12_generated_claims_acceptance_2026-10-08.json.

Тексты и редакции подтверждённых норм: P1_legal_freshness_consolidated_receipt_2026-10-08.json и P1_APK129_current_quote_2026-10-08.json. Файлы первичных источников: P1_durable_source_manifest_2026-10-08.json. Source hash связывает exact evidence, но для not_verified он не удостоверяет актуальность. Отсутствие доступа классифицировано как зависимость, не как юридический FAIL.

Для закрытия NOT_VERIFIED нужны текущие официальные тексты/редакции, сохранённое проверяемое evidence и новая сверка этого hash. Human-review закрывает только отдельную юридическую эскалацию и не заменяет официальный текст/evidence.
