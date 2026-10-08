```yaml
document: products-storage/01-zakrytie-rabot/01-ks-2.docx
document_hash: sha256:e46dc1016b40dec40781175cb1d87d5fcf489a0fcf2aee33a12cc492ab1c38d1
generator_hash: sha256:d001466d361ef36c19a9614f60d19864558d385d066c620332c4fe8dbaada7fb
checked_at: 2026-10-08
checker: normative-checker
sources:
  source0: &source0 "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102039276"
norms_checked:
  - {norm_id: gk-753, source_hash: sha256:3addb79c003fa0e15b3150d7353f6559707ff7b1792931ad42a447b94f9848b7, source_used: *source0, source_class: not_verified, quote_obtained: false, verdict: не найдена}
verdict: NOT_VERIFIED
issues:
- id: CURRENT-01
  severity: material
  claim: Актуальность необходимых официальных норм на 08.10.2026
  norm_id: gk-753
  why: 'ACCESS/DEPENDENCY: не подтверждены текущие официальные тексты/редакции: gk-753'
corrections: []
escalation_required: false
escalation_reason: null
```

Проверен фактический объём сдачи/приёмки и замечания. Утверждения об официальной унифицированной форме отсутствуют.

Тексты и редакции подтверждённых норм: P1_legal_freshness_consolidated_receipt_2026-10-08.json и P1_APK129_current_quote_2026-10-08.json. Файлы первичных источников: P1_durable_source_manifest_2026-10-08.json. Source hash связывает exact evidence, но для not_verified он не удостоверяет актуальность. Отсутствие доступа классифицировано как зависимость, не как юридический FAIL.

Для закрытия NOT_VERIFIED нужны текущие официальные тексты/редакции, сохранённое проверяемое evidence и новая сверка этого hash. Human-review закрывает только отдельную юридическую эскалацию и не заменяет официальный текст/evidence.
