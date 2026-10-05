# P3 deterministic producer metadata

Passport beforeedit: execution_pattern=iterative; primary_result=byte reproducibility acrossinstalledopenpyxl versions; feedback_loop_required=true; checkpoint_policy=verified_only. Base f8bfdc569b9d561b87595aa9d6b5f28f76871e02. Scope existing _freeze_ooxml in build_paid_05.py and XLSX02/06 producer metadata only, no styles/formulas/content/legal/price/SKU/live. Input rawZIPdiff: onlydocProps/app.xml differs between3.1.5delivered and3.1.2server, styles andallbusinessXML byteidentical. False StyleProxycomparison excluded, copy comparison confirms0deltas. Acceptance existinggenerator reproduction test andbuyer checks, two realrebuildbyteequal, all changedbuyerparts app.xmlonly. No installs; systempython existingAIOSreportlab importscope only.

Actual existingtests: ...................................                                      [100%]
35 passed in 1.44s

Producer metadata only: [{"file": "02-reestr-prilozheniy.xlsx", "parts": ["docProps/app.xml"], "sha256": "7d3a10560614401c36ef854cd3aead16961864479a9bfcb7d38dc78ab743c7f3"}, {"file": "06-zhurnal-peredachi.xlsx", "parts": ["docProps/app.xml"], "sha256": "98f20a51a39c41d5cf0e0fd6766cbeb1e8906bbad087956b736b1482f18ab73d"}]
Class SERIALIZER_VERSION_METADATA_DRIFT; rule pin compatibility label inexistingfreezer, gate existing byte-reproduction test plusunchangedbusinessZIPparts.
