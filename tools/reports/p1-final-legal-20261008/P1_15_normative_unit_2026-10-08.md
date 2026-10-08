```yaml
document: products-storage/01-zakrytie-rabot/15-algoritm-pri-zaderzhke-oplaty.docx
document_hash: sha256:2f0d7b36f7fb9e2c9edf9579af000817b3a67e40894a75ace5949102cd946cb8
generator_hash: sha256:5a30afd64117a760e5561682d774205399ce05d45aa6ec792f81e85ef3fd4431
checked_at: 2026-10-08
checker: normative-checker
sources:
  source0: &source0 "http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102033239&rdk=157&&empire="
  source1: &source1 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102039276"
  source2: &source2 "http://pravo.gov.ru/proxy/ips/?doc_itself=&nd=102079219&page=all&rdk=89"
  source3: &source3 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102078527"
  source4: &source4 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102067058"
  source5: &source5 "https://vsrf.ru/documents/own/8524/"
  source6: &source6 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102117007"
norms_checked:
  - {norm_id: gk-328, source_hash: sha256:d665aecc72e98ba800d67b794b9193de63370cb6fe2be6a64d20d28de90c41ab, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-719, source_hash: sha256:64fbfc1a96e2496634448694e152d5e98419a408a5b1aef8972c7c04635d63aa, source_used: *source1, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-753, source_hash: sha256:3addb79c003fa0e15b3150d7353f6559707ff7b1792931ad42a447b94f9848b7, source_used: *source1, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-196-200, source_hash: sha256:8091b6e68da357e550817f01ed1bf995fa876ccd4f61a122dfcdde156ea93b24, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-4-5, source_hash: sha256:6603e670456f0ab3a8ec287c3626d56613e7623428a3c7ba937c8b0cc1a67d44, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: fz-127-7, source_hash: sha256:98c23588fc9bdfa76b4d38ea25317c12e0cf5eaab1419cff7dc12b7c9fd39735, source_used: *source3, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-395, source_hash: sha256:07ae25b8650a6efb592a911c1ae0c8ff2ff876dfb8da065293113f120ac338bd, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: nk-333-21, source_hash: sha256:9bbc4147e29d9ac82f3715096f20626d14cbc1a361c3a19f160e040f70b6abac, source_used: *source4, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: plenum-54-57, source_hash: sha256:6b25fc2f5eea86c326bf5f9ab0cfbfe006fcf9aebcf585f5bf235e6f1248b572, source_used: *source5, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: fz-229-8, source_hash: sha256:6b04f4e3e7e53eafcde7da591d411fed73f0fed06f6cd7585ff8d7f3e9a6d1e6, source_used: *source6, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-330, source_hash: sha256:8c4714b2a6784a22607a162b1b5d63dcbc4063219d64100b963a096e80a9edb3, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
verdict: NOT_VERIFIED
issues:
- id: CURRENT-15
  severity: material
  claim: Актуальность необходимых официальных норм на 08.10.2026
  norm_id: gk-719
  why: 'ACCESS/DEPENDENCY: не подтверждены текущие официальные тексты/редакции: gk-719,
    gk-753, fz-127-7, nk-333-21, plenum-54-57'
corrections: []
escalation_required: false
escalation_reason: null
```

Маршрут самодостаточен по договору/актам/оплатам. Долг на начало расчёта отличен от текущего остатка; выбранные проценты рассчитываются14, неустойка отдельно по договору. Контрольная линия отражает применимое досудебное ожидание, а не собственный срок ответа.

Фикстуры применимого ожидания: общий срок от направления ещё не истёк; собственный ответ5дней истёк, ожидание нет; договор10дней от получения ещё не истёк. Во всех трёх STOP. Это ручное применение фактических инструкций, не календарный калькулятор и не проверка конкретного договора. Receipt: P1_final_batch_generated_acceptance_2026-10-08.json; для12 также P1_final12_generated_claims_acceptance_2026-10-08.json.

Тексты и редакции подтверждённых норм: P1_legal_freshness_consolidated_receipt_2026-10-08.json и P1_APK129_current_quote_2026-10-08.json. Файлы первичных источников: P1_durable_source_manifest_2026-10-08.json. Source hash связывает exact evidence, но для not_verified он не удостоверяет актуальность. Отсутствие доступа классифицировано как зависимость, не как юридический FAIL.

Для закрытия NOT_VERIFIED нужны текущие официальные тексты/редакции, сохранённое проверяемое evidence и новая сверка этого hash. Human-review закрывает только отдельную юридическую эскалацию и не заменяет официальный текст/evidence.
