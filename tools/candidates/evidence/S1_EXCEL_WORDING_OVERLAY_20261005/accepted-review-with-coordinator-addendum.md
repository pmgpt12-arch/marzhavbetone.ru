# Приёмка двух узких исправлений Excel

Оба exact drafts получили ACCEPT для текста и структурной изоляции. Owner approval относится только к исходным BEFORE-файлам; новые AFTER-файлы не согласованы владельцем. Официальная актуальность норм и человеческая юридическая приёмка не выполнены.

Поправка координатора к G5 исходного отчёта: статус 01/03 устарел. В базе a261 и фактической рабочей ветке уже находятся независимо принятые правки PR465/466; файл10 также принят и слит PR467. Это подтверждается отдельной квитанцией сравнения actual merged files. Новый эксперт не читал текущие01/03, поэтому его утверждение об их старом тексте нельзя использовать. Исходный отчёт сохранён полностью ниже без редактирования.

Визуальная проверка координатора: исправленная F19 видна полностью на листе Calc. Исправленная A12 полностью видна в single-sheet preview; стандартный Calc PDF режет лист по горизонтали (native print acceptance не выполнена). Это не новая приёмка владельцем в Excel.

Правило фабрики: паспорт независимой задачи, использующий более ранний экспертный отчёт, обязан приложить актуальную карту уже принятых исправлений; иначе остаточные статусы считать непроверенными.

---

# Independent narrow review: Excel wording drafts 02 (F19) and 08 (A12)

**Draft 0 (`02-proverka-i-kontrol-otveta.xlsx`, Карта рисков!F19): ACCEPT**
**Draft 1 (`08-raschet-procentov-395.xlsx`, Как пользоваться!A12): ACCEPT**

These verdicts cover only the narrow wording change and its structural isolation. **LEGAL_ACCEPTANCE_NOT_PERFORMED.** I did not check the official current text of the law (status: NOT_VERIFIED). Neither draft is owner approved. The owner's native approvals apply only to the BEFORE bytes listed below.

---

## 1. Input hashes (recomputed in this run)

All 7 inputs match the supplied byte counts and sha256 values.

| File | Bytes | sha256 | Match |
|---|---|---|---|
| `proof.json` | 2847 | `6da4a21d635fcf03417f72ff6a60635d66aad1d02afaf48ca83e00090ac6c369` | ✅ |
| `secondary-gk-395.txt` | 4584 | `32bbfef3a51c7ef5f6dad5ffe3421d15516fbd1f37d93fcbe9be29ae267f60c7` | ✅ |
| `MB001_S1_DOC09_CORRECTION_RECHECK_2026-10-05.md` | 11658 | `85566cd878328ffc1946539f2f0936e3892de68d4f623a5fddfcbb8aa56f08c8` | ✅ |
| `0-before.xlsx` (owner-approved native 02) | 32192 | `0a5c75b2816b93b6da4c0cfa395a5d9e5989ad6a2c44ce1edd70c8b3a7376fcc` | ✅ |
| `0-after.xlsx` (draft 02, **not owner approved**) | 27364 | `5918714b4e4e95abc546e1fe7a43f515af50680ecf75352a2949a2ebecac47f0` | ✅ |
| `1-before.xlsx` (owner-approved native 08) | 474439 | `9c2b69043ce6c09924236abfb0808659d0b739347e22aa9796b400440def3d92` | ✅ |
| `1-after.xlsx` (draft 08, **not owner approved**) | 474471 | `e0ed0206c17f1b3638bba14dd472c3acad0da80c87dd640169e9c094dec266b4` | ✅ |

In `proof.json`, `owner_source_sha256` and `draft_sha256` match the BEFORE and AFTER hashes above for both pairs.

## 2. Structural comparison (zipfile + XML, Python stdlib)

### Pair 0: file 02

- **ZIP parts:** 14 in both files, with the same names in the same order.
- **Only part with different bytes:** `xl/sharedStrings.xml`, 24444 → 24442 bytes.
  - sha256 before: `38de631327e32f9018d5a327de66ab9715117fba243f533d2dfb1896bba5bb7d`
  - sha256 after: `29a955eaee419ecc361ca4527566ef0fb4cb26e37960a75675039a58099bdb61`
- **Identical bytes:** all other 13 parts, including the 4 worksheets, `workbook.xml`, `styles.xml`, `theme1.xml`, `calcChain.xml`, `docProps/*`, `[Content_Types].xml` and the rels files.
- **Shared-string table:** `count=189` and `uniqueCount=180` are unchanged, with 180 `<si>` entries. Only index **94** differs, as a plain `<t>` in both files with no rich-text runs. The raw-byte diff is confined to that `<si>`.
- **Who uses each shared string:** I scanned every worksheet for `t="s"` cells. There are 189 such cells pointing at 180 distinct indices, and no index is unused. Index 94 has exactly **one** consumer: **Карта рисков!F19**.
  - No `t="s"` cells or `inlineStr` exist outside the worksheets.
  - Only `[Content_Types].xml` and `workbook.xml.rels` mention `sharedStrings`, and both are unchanged.
  - The old text no longer appears anywhere in the AFTER file. The new text does not duplicate any other entry.
- **Every cell, all sheets:** I compared all 1951 cells on type, style index, resolved value and formula XML. Only **Карта рисков!F19** differs.
  - Unchanged structures per sheet: Маршрут has 6 formulas, 7 merges and 1 DV; Карта рисков 18 / 2 / 1; Контроль ответа 400 / 2 / 1; Справочник 0 / 0 / 0.
  - Row 19 (`ht="28.8"`) and F19 `s="3"` are unchanged.
- **Before → after text:**
  - Before: «Если есть — выбор между неустойкой и процентами к специалисту (п. 4 ст. 395 ГК РФ).»
  - After: «Если есть — применение процентов требует оценки специалиста (п. 4 ст. 395 ГК РФ).»
  - Both strings match `proof.json` `cell_diff` exactly.
- **Observation, not a defect:** the ZIP *entry metadata* differs for all 14 entries. `external_attr` goes from 0 to 25165824 (unix mode 0600) and `flag_bits` from 6 to 0. Timestamps, compression method and archive comment are unchanged. This doesn't affect any XML part's content, so `all_other_zip_parts_exact: true` is accurate for part bytes. A later byte-level or semantic guard should not assume the ZIP container metadata is identical.

### Pair 1: file 08

- **ZIP parts:** 18 in both files, with the same names in the same order.
- **Only part with different bytes:** `xl/sharedStrings.xml`, 15175 → 15318 bytes.
  - sha256 before: `a59c49247936dfc048cf00b3cdf7abc90e60ed09566ff93f0951983751c92931`
  - sha256 after: `1ca2fcc2050e7f96e501d5d855f1f9394863d2b493c8c2947e01f774eab0b5a5`
- **Identical bytes:** all other 17 parts, including the 8 worksheets, `styles.xml`, `calcChain.xml`, theme, `docProps` and rels.
- **ZIP entry metadata:** identical for every entry.
- **Shared-string table:** `count=117` and `uniqueCount=94` are unchanged, with 94 `<si>` entries. Only index **11** differs, as a plain `<t>` in both files.
- **Who uses each shared string:** 117 `t="s"` cells point at 94 distinct indices, and none is unused. Index 11 has exactly **one** consumer: **Как пользоваться!A12**.
  - No inline strings or other references exist.
  - The tail of the old text («— выбор к специалисту») is gone from AFTER. The new text does not duplicate any other entry.
- **Every cell, all 8 sheets:** I compared 38,816 cells and 36,245 formulas. Only **Как пользоваться!A12** differs.
  - Unchanged structures: merges (Акты 2, Оплаты 2, Расчёт 2, По дням 1) and conditional formatting (Ввод 1).
  - Row 12 (`ht="28.8"`) and A12 `s="2"` are unchanged.
- **Before → after text:**
  - Before: «…проценты по ст. 395 ГК РФ по общему правилу не взыскиваются (п. 4 ст. 395 ГК РФ) — выбор к специалисту.»
  - After: «…проценты по ст. 395 ГК РФ по общему правилу не взыскиваются, если законом или договором не предусмотрено иное (п. 4 ст. 395 ГК РФ). Применение процентов требует оценки специалиста.»
  - Both strings match `proof.json` exactly. The text grows from 193 to 270 characters.

**Structural result for both pairs:** exactly one shared string changed, it has exactly one consumer, and that consumer is the designated cell. All other values, formulas, styles, merges, DV, CF and native XML parts are byte-identical.

## 3. Comparison with the supplied secondary source

The source is `secondary-gk-395.txt`: consultant.ru, `source_class=secondary`, currentness NOT_VERIFIED.

The relevant passage is L29, п. 4 ст. 395 ГК РФ: «В случае, когда соглашением сторон предусмотрена неустойка за неисполнение или ненадлежащее исполнение денежного обязательства, предусмотренные настоящей статьей проценты не подлежат взысканию, **если иное не предусмотрено законом или договором**».

The previously accepted C2 reasoning (file 09, ¶10) is my benchmark. It found that «по общему правилу не взыскиваются, если иное не предусмотрено законом или договором» plus a referral to a specialist follows п. 4 without overclaiming and removes the impression of a free choice.

### Draft 0, F19: ACCEPT

- **Removes the false free choice.** «Выбор между неустойкой и процентами» suggested the creditor may freely pick either remedy. Under п. 4, once a contractual penalty exists, interest is excluded by default, so that framing contradicted the source. The new text drops it.
- **No overclaim.** «Применение процентов требует оценки специалиста» states no rule that isn't in the source. It doesn't say interest is recoverable or that it is excluded. It points to п. 4 and sends the question to a specialist.
- **The trigger matches the source.** «Если есть» refers to the row label «Условие о неустойке за просрочку оплаты». That corresponds to «соглашением сторон предусмотрена неустойка» and is a subset of «неисполнение или ненадлежащее исполнение денежного обязательства».
- **Picks no legal option.** It neither prefers interest nor penalty, nor applies the law/contract exception.
- **N1 (non-blocking):** F19 is less informative than the accepted C2 standard because it doesn't state the default exclusion or the law/contract exception. In a one-cell risk map that leaves everything to a specialist, this is incomplete but not inaccurate. If wording is aligned across files later, consider «по общему правилу проценты не взыскиваются, если иное не предусмотрено законом или договором; оценка специалиста».

### Draft 1, A12: ACCEPT

- **The exception is added accurately.** «если законом или договором не предусмотрено иное» matches the source's «если иное не предусмотрено законом или договором» word for word in substance, including both sources of the exception: law and contract.
- **The default rule is preserved.** «по общему правилу не взыскиваются» corresponds to «не подлежат взысканию».
- **The trigger is correct.** «договор устанавливает неустойку за просрочку оплаты» matches «соглашением сторон предусмотрена неустойка». A statutory penalty, which п. 4 doesn't cover by its text, isn't mentioned, so nothing is overclaimed.
- **The free choice is removed.** «— выбор к специалисту» is replaced by «Применение процентов требует оценки специалиста», a neutral referral that picks no option.
- **Same as accepted C2.** The wording is substantively identical to the C2 text accepted for file 09 ¶10, so files 08 and 09 now agree on this point.
- The surrounding sentence «Оплаты уменьшают основной долг» is unchanged and outside this review's scope.

## 4. What I separated and did not do

| Area | Status |
|---|---|
| Consistency with the supplied secondary text (п. 4 ст. 395) | **Consistent**, both drafts |
| Currentness of the official law text | **NOT_VERIFIED** (secondary source only, no network) |
| Human or legal acceptance | **LEGAL_ACCEPTANCE_NOT_PERFORMED** |
| Owner approval | Applies to BEFORE bytes only (`0a5c75b2…6fcc`, `9c2b6904…3d92`). AFTER drafts (`5918714b…47f0`, `e0ed0206…b5a5`) are **NOT owner approved** |
| Native Excel visual check | **NOT_PERFORMED**. I make no render or recalculation claim |
| Financial formula audit | Not performed (out of scope). Formulas were only checked as identical XML |
| Choosing a legal option for any dispute | Not done |

## 5. Remaining gates

1. **G1, human legal gate:** legal acceptance of both wordings, plus verification against the current official text of ст. 395 ГК РФ.
2. **G2, owner approval of the drafts:** the AFTER files need their own owner decision. I make no claim that would replace the approved owner hashes.
3. **G3, native visual check (Excel/LibreOffice):**
   - A12 grows from 193 to 270 characters in a column about 149 characters wide. Row 12 keeps `ht="28.8"`, which fits about 2 lines, so the text may be clipped.
   - F19 got shorter (83 → 81 characters), so it's low risk.
4. **G4, semantic-guard integration (later task):** account for the changed `sharedStrings.xml` hashes above and the ZIP entry metadata change in pair 0.
5. **G5, cross-file consistency:** `CONSISTENCY_GATE_01_03_10_OPEN` from the previous report is still open. Files 01 and 03 still contain the «выбор между неустойкой и процентами» wording. They are outside this review and need their own fix and recheck.
6. **N1 (optional, non-blocking):** align F19's wording with the C2/A12 wording.

---
No files were edited, nothing was written to disk, and no network, git or gh was used. The only tools used were read-only Python (`zipfile`, `xml.etree`, `hashlib`) and Read.