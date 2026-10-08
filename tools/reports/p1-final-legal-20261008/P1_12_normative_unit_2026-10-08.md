```yaml
document: products-storage/01-zakrytie-rabot/12-pretenziya-na-neoplatu-po-ks-2.docx
document_hash: sha256:a153d78cf294791007c2ae200331195a54dd39639c88e535199deb6750235a1b
generator_hash: sha256:c6f0e48fbe933d169f90354a84890c3b2c952812340dfc60a44945dba6abb794
checked_at: 2026-10-08
checker: normative-checker
sources:
  source0: &source0 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102039276"
  source1: &source1 "http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102033239&rdk=157&&empire="
  source2: &source2 "http://pravo.gov.ru/proxy/ips/?doc_itself=&nd=102079219&page=all&rdk=89"
  source3: &source3 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102067058"
norms_checked:
  - {norm_id: gk-711, source_hash: sha256:8f6513bfebeb20b673b0772594deb336d8d665aae11936745cbc137afea91049, source_used: *source0, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-746, source_hash: sha256:8234d40258be23cd694a17f85a31430d3183d43aa1f8e43f34b0c51ee381239f, source_used: *source0, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-753, source_hash: sha256:3addb79c003fa0e15b3150d7353f6559707ff7b1792931ad42a447b94f9848b7, source_used: *source0, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: gk-395, source_hash: sha256:07ae25b8650a6efb592a911c1ae0c8ff2ff876dfb8da065293113f120ac338bd, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-314, source_hash: sha256:8fc58b629bdef50acd16b2bdecef12a48f66248e763b0f8226b060746a92d64f, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-193, source_hash: sha256:ea6f7c3963bec9a3f7395b5772e41069e676c41c52a06779ea5092a521d11572, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-4-5, source_hash: sha256:6603e670456f0ab3a8ec287c3626d56613e7623428a3c7ba937c8b0cc1a67d44, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-128-148, source_hash: sha256:5ab245b1975ce0794aaa5595c88088d4fa12e607e23d34c37bea8932e9b9628e, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: nk-333-40, source_hash: sha256:9c91f155ecf4f6a42f54806cc6960b5c9cf6cbd08aa10c9ae7e6ff829ca5ddb7, source_used: *source3, source_class: not_verified, quote_obtained: false, verdict: не найдена}
  - {norm_id: apk-110, source_hash: sha256:f4204c910a45b86d889d836ffe5c334efb6a2105d093e59fe624a29fc120f815, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-202, source_hash: sha256:98689b9271ff5cc84673e7beeb5dec26d9163a3efc989409dae9a7ea55105efd, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-309, source_hash: sha256:63ae9f33e88a92bd41c8bc45058b1ade42aa6d92bc0fb6e568e5af783bfab17d, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-310, source_hash: sha256:1fce76406728a24d7860cbcbc9bd55faf5c22f3fd8c7eddd300a3e5efa147b4f, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-330, source_hash: sha256:8c4714b2a6784a22607a162b1b5d63dcbc4063219d64100b963a096e80a9edb3, source_used: *source1, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-129, source_hash: sha256:77c6756834469e8b99a136cecf0a13a501356ceb7d1d79f14816f6ae59185262, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: apk-125-126, source_hash: sha256:607a4103328f7a67401283a8cfe2b68893cb6c19dffadacd7e92100c1b7c4d30, source_used: *source2, source_class: official, quote_obtained: true, verdict: подтверждена}
verdict: NOT_VERIFIED
issues:
- id: CURRENT-12
  severity: material
  claim: Актуальность необходимых официальных норм на 08.10.2026
  norm_id: gk-711
  why: 'ACCESS/DEPENDENCY: не подтверждены текущие официальные тексты/редакции: gk-711,
    gk-746, gk-753, nk-333-40'
corrections: []
escalation_required: false
escalation_reason: null
```

Независимо применён полный пятишаговый переход к договорной неустойке: заголовок, основание/период/сумма, требование, предупреждение, приложение. В оперативной penalty ветке нет395, СУММА_ПРОЦЕНТОВ или автоматического будущего начисления. Исправлены стадии129/148, категорическое исключение202 при договорном порядке и категорические выводы о доказательствах доставки.

Фикстуры применимого ожидания: общий срок от направления ещё не истёк; собственный ответ5дней истёк, ожидание нет; договор10дней от получения ещё не истёк. Во всех трёх STOP. Это ручное применение фактических инструкций, не календарный калькулятор и не проверка конкретного договора. Receipt: P1_final_batch_generated_acceptance_2026-10-08.json; для12 также P1_final12_generated_claims_acceptance_2026-10-08.json.

Тексты и редакции подтверждённых норм: P1_legal_freshness_consolidated_receipt_2026-10-08.json и P1_APK129_current_quote_2026-10-08.json. Файлы первичных источников: P1_durable_source_manifest_2026-10-08.json. Source hash связывает exact evidence, но для not_verified он не удостоверяет актуальность. Отсутствие доступа классифицировано как зависимость, не как юридический FAIL.

Для закрытия NOT_VERIFIED нужны текущие официальные тексты/редакции, сохранённое проверяемое evidence и новая сверка этого hash. Human-review закрывает только отдельную юридическую эскалацию и не заменяет официальный текст/evidence.
