F5 only:10 context-specific field names distinguish parties and dates. Old ambiguity reproduced by exact old XML comparison. Reversing only these10 renames restores the complete old DOCX bytes of document.xml; all other ZIP entries unchanged. Two replacement-all fixtures PASS. No legal, financial or page/printing edits. Independent acceptance and working merge pending.

{
  "status": "VERIFIED_MECHANICAL_F5",
  "base": "ccc6b5c3b0a799b67d5a87e9108555a99e0c60a7",
  "replacements": [
    [
      "Просим оплатить задолженность в срок до {{ДАТА}}",
      "Просим оплатить задолженность в срок до {{ДАТА_ОПЛАТЫ_ПО_ТРЕБОВАНИЮ}}"
    ],
    [
      "Приложение: реестр взаиморасчётов на {{ДАТА}}.",
      "Приложение: реестр взаиморасчётов на {{ДАТА_РЕЕСТРА_ВЗАИМОРАСЧЁТОВ}}."
    ],
    [
      "Истец: {{НАИМЕНОВАНИЕ_СУБПОДРЯДЧИКА}}, ИНН {{ИНН}}, ОГРН {{ОГРН}}, адрес: {{АДРЕС}}",
      "Истец: {{НАИМЕНОВАНИЕ_СУБПОДРЯДЧИКА}}, ИНН {{ИНН_ИСТЦА}}, ОГРН {{ОГРН_ИСТЦА}}, адрес: {{АДРЕС_ИСТЦА}}"
    ],
    [
      "Ответчик: {{НАИМЕНОВАНИЕ_ЗАКАЗЧИКА}}, ИНН {{ИНН}}, ОГРН {{ОГРН}}, адрес (по ЕГРЮЛ): {{АДРЕС}}",
      "Ответчик: {{НАИМЕНОВАНИЕ_ЗАКАЗЧИКА}}, ИНН {{ИНН_ОТВЕТЧИКА}}, ОГРН {{ОГРН_ОТВЕТЧИКА}}, адрес (по ЕГРЮЛ): {{АДРЕС_ОТВЕТЧИКА}}"
    ],
    [
      "претензия № {{НОМЕР}} от {{ДАТА}}",
      "претензия № {{НОМЕР}} от {{ДАТА_ПРЕТЕНЗИИ}}"
    ],
    [
      " / {{ФИО}} /     {{ДАТА}}",
      " / {{ФИО}} /     {{ДАТА_ПОДПИСАНИЯ_ИСКА}}"
    ]
  ],
  "input_context": "F5 independent415",
  "cost_usd": 0,
  "records": [
    {
      "file": "06-uvedomlenie-o-prosrochke.docx",
      "sha256": "013642c0ce8489add96fab5f7aadd0cbb696dd3940085d4b729c40d6f18b3c4d",
      "only10_placeholder_names_changed": true
    },
    {
      "file": "10-obrashchenie-v-sud.docx",
      "sha256": "59e3e01281a452d6c1852d876daac06d9537c9cd8e31fcc58e63fbde6bda13a1",
      "only10_placeholder_names_changed": true
    }
  ],
  "tests": "..                                                                       [100%]\n2 passed in 0.03s\n"
}
