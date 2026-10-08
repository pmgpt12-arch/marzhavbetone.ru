```yaml
document: products-storage/01-zakrytie-rabot/14-raschet-procentov-395-gk.xlsx
document_hash: sha256:4ca6d9b9cfa4393cfcfe93d29467e95f1f02c9e24cac7332ca166664fea11a7a
generator_hash: sha256:cfa6d9151881922f4a264e12b09380a294a20bc69f7b4cabf26715b97d3d7bdf
checked_at: 2026-10-08
checker: normative-checker
sources:
  source0: &source0 "http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102033239&rdk=157&&empire="
  source1: &source1 "https://vsrf.ru/media-proxy/upload/iblock/021/0211e9ae21e6d77ac6ce9494b752844f.pdf"
  source2: &source2 "https://vsrf.ru/documents/all/8524/"
norms_checked:
  - {norm_id: gk-395, source_hash: sha256:07ae25b8650a6efb592a911c1ae0c8ff2ff876dfb8da065293113f120ac338bd, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-191, source_hash: sha256:464ff087a2d3d945f54b36c7e6c3ad38fd5b17f7c19a2a50d30ce852f5f2cac0, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: gk-193, source_hash: sha256:ea6f7c3963bec9a3f7395b5772e41069e676c41c52a06779ea5092a521d11572, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: ppvs-7-2016, source_hash: sha256:497ad663e265c9f3db9120a57f7ea8f3d3369a4a11cc0af2e3bc5f66452093f6, source_used: *source1, source_class: not_verified, quote_obtained: true, verdict: не найдена}
  - {norm_id: gk-319, source_hash: sha256:e867e3c2b8e8081acc332734b0936e3b8c1d445328227acf3e88224c747a75bd, source_used: *source0, source_class: official, quote_obtained: true, verdict: подтверждена}
  - {norm_id: ppvs-7-2016-49, source_hash: sha256:3103024e011fa468ce6ee75b9ffd9f4213b24ca8074f5ac34123af96a3f12b4c, source_used: *source1, source_class: not_verified, quote_obtained: true, verdict: не найдена}
  - {norm_id: plenum-54-37, source_hash: sha256:1699e59e2e54509a69723ea0f38aac6151e68ccdfd330e617d4cb9ce5d095630, source_used: *source2, source_class: not_verified, quote_obtained: true, verdict: не найдена}
verdict: NOT_VERIFIED
issues:
- id: CURRENT-14
  severity: material
  claim: Актуальность необходимых официальных норм на 08.10.2026
  norm_id: ppvs-7-2016
  why: 'ACCESS/DEPENDENCY: не подтверждены текущие официальные тексты/редакции: ppvs-7-2016,
    ppvs-7-2016-49, plenum-54-37'
corrections: []
escalation_required: false
escalation_reason: null
```

Прочитаны окончательные A47/C4/A51/A19 и связанные формулы:319 касается процентов за пользование и издержек,395 следует после основного долга; платёж уменьшает базу со следующего дня;365/366 и разрыв периодов проверены отдельно. Полнота текущей редакции Пленумов не установлена. Функциональная LiveCalc-проверка root не заменяет нормативный источник.

Тексты и редакции подтверждённых норм: P1_legal_freshness_consolidated_receipt_2026-10-08.json и P1_APK129_current_quote_2026-10-08.json. Файлы первичных источников: P1_durable_source_manifest_2026-10-08.json. Source hash связывает exact evidence, но для not_verified он не удостоверяет актуальность. Отсутствие доступа классифицировано как зависимость, не как юридический FAIL.

Для закрытия NOT_VERIFIED нужны текущие официальные тексты/редакции, сохранённое проверяемое evidence и новая сверка этого hash. Human-review закрывает только отдельную юридическую эскалацию и не заменяет официальный текст/evidence.
