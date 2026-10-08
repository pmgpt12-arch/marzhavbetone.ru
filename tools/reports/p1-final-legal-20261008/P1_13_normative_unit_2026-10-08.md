```yaml
document: products-storage/01-zakrytie-rabot/13-uvedomlenie-o-prosrochke-oplaty.docx
document_hash: sha256:8f3566b5f132cae1b85a666250bfd1c4af32fffdd63dceae1e5b782b81a81de6
generator_hash: sha256:0d14d45bf257a5863aa5234d3fa52b922a5dd749f3623589635d75ea72ece71b
raw_document_hash: sha256:6f73237e36ee70cf8aab727aa6a962e559e05cc9e41de671c981f969f412663b
reviewed_container_hash: sha256:2f8e291f6029ae1f67d4d5ea3825401ee40b47642a698213bf333ac30dad0a45
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

Narrow grammar delta: прочитан новый generated13 /workspace/scratch/d88c71a3c278/p1-docx-source/grammar13/02-Уведомление-о-просрочке-оплаты.docx, raw SHA256 2f8e291f6029ae1f67d4d5ea3825401ee40b47642a698213bf333ac30dad0a45. По реальной инструкции применён целый penalty-абзац; получено «начисляется неустойка / начисленной неустойки / её начисление». Interest-ветка: «начисляются проценты / начисленных процентов / их начисление». Предупреждение о суде согласовано с каждой веткой. Полный paragraph diff: ровно одна инструкция, остальные юридические/досудебные положения неизменны. Нормативный PASS прежних6 источников повторно связан с новым SEM; новой сети и полного прогона не было. Receipt: P1_13_grammar_generated_acceptance_2026-10-08.json.

Окончательная root-сборка: выдаваемый raw sha256:6f73237e36ee70cf8aab727aa6a962e559e05cc9e41de671c981f969f412663b; receipt /tmp/p1-root-grammar13-final-20261008/root-rebuild-receipt.json. Обе выдаваемые копии побайтно равны. SEM совпал с independently accepted generated13; source02 и lib неизменны. Локальный прочитанный контейнер sha256:2f8e291f6029ae1f67d4d5ea3825401ee40b47642a698213bf333ac30dad0a45 и его путь grammar13 сохранены для аудита. Обновлена только привязка контейнера13; другие8 результатов неизменны, новой нормативной сверки или сети не было.
