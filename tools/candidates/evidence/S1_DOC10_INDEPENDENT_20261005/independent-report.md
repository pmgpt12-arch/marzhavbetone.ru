# MB001 S1: independent narrow review of the one-line correction to file 10 (A2 analogue)

**Verdict: ACCEPT** (for this one-line correction only)

**LEGAL_ACCEPTANCE_NOT_PERFORMED.** Official currentness of the cited text: **NOT_VERIFIED**. This is not a normative PASS, not legal acceptance, and not layout acceptance.

## 1. Binding and input hashes

I recomputed all hashes in this run. All 7 match the task specification exactly.

| Input | Bytes | sha256 | Match |
|---|---|---|---|
| root-visual.json | 303 | `3d80c3f9…8221` | ✅ |
| before.docx | 42965 | `b1700cad…1ebb` | ✅ |
| after.docx | 42981 | `129769e5…94bc` | ✅ |
| scope-proof.json | 1866 | `777838e1…f8c` | ✅ |
| generator.diff | 2297 | `0ad59dac…8c` | ✅ |
| MB001_S1_DOC09_CORRECTION_RECHECK_2026-10-05.md | 11658 | `85566cd8…5f8c` | ✅ |
| secondary-apk-4.txt | 12295 | `49f9dccef…9317` | ✅ |

**Binding to the commits.** The candidate `07eebbb4…` and its parent `a261eee1…` are tied to these files only through the supplied hashes. git was not allowed, so I did not check that the commit tree contains these exact bytes. The `before_sha256` and `after_sha256` values in scope-proof.json match the files.

## 2. DOCX structure check (Python zipfile and python-docx 1.1.0)

**ZIP parts**
- Both archives have the same 17 parts, in the same order.
- Each entry's `date_time` and `compress_type` are the same in both.
- Only one part has different bytes: **`word/document.xml`** (40688 → 40740 bytes).

**XML**
- The old string occurs once in before and zero times in after. The new string occurs zero times in before and once in after.
- `xa.replace(OLD, NEW) == xb` returns **True**. So the XML differs only by this text, with no changes to run properties, attributes or structure.
- The byte difference (+52) equals the difference in UTF-8 length between the two strings.

**Text (python-docx)**
- Both files have 41 paragraphs, 3 tables and 230 text elements (paragraphs plus every table cell).
- **Exactly one element changed: `T0R2C1`.** That is table 0, "Раздел А. Проверочный лист готовности", row 2, column "Проверка".
- All other checklist rows and the other two tables (the attachment list with 19 rows and the specialist handover list with 16 rows) are word-for-word identical.
- The claim template text in section Б (the court body) is unchanged.
- The `{{…}}` placeholders are the same set, with the same counts, before and after.

| | Text of T0R2C1 |
|---|---|
| Before | «…истёк (по договору, а если не установлен — по ч. 5 ст. 4 АПК РФ, со дня направления претензии)» |
| After | «…истёк (по договору или закону, если ими установлен иной срок, а иначе — по ч. 5 ст. 4 АПК РФ, со дня направления претензии)» |

## 3. Generator diff check

- There is one hunk, `@@ -1703,7 +1703,7 @@ def f10(out: Path):`, with exactly 1 line removed and 1 line added. It sits in the item list of the `table(...)` under section А.
- The quoted string in the `-` line equals OLD **exactly**, and the one in the `+` line equals NEW **exactly**.
- Replacing OLD with NEW in the `-` line gives exactly the `+` line, so the second tuple element («Файл 02, «Контроль ответа»») and the syntax are untouched.
- The `text_diff` in scope-proof.json matches both strings exactly.
- Limitation: I saw only the supplied diff, not the full generator. I could not confirm that the commit contains no other changes, and I did not rebuild the file.

## 4. Wording check against the source and the accepted A2

**Source:** `secondary-apk-4.txt`, L32, part 5, paragraph 1 of art. 4 of the Arbitration Procedure Code (АПК РФ): «…по истечении тридцати календарных дней со дня направления претензии (требования), если иные срок и (или) порядок не установлены законом или договором.» L39 gives the revision note as «(часть 5 в ред. Федерального закона от 01.07.2017 N 147-ФЗ)».

- **What the old wording got wrong:** it named only the contract as a possible source of a different deadline («по договору, а если не установлен»). It left out "law", which the source names alongside the contract. This is the same defect that A2 fixed in file 09.
- **The new wording:** it names both sources («договору или закону, если ими установлен иной срок»). It keeps the fallback to the 30-day rule of part 5 of art. 4 of the Code, and it keeps the start of the period «со дня направления претензии». → **Matches the source** and makes no new claims.
- **Consistency with the accepted A2:** the accepted A2 wording in file 09 was «из договора или закона, если ими установлен иной срок, а иначе — из этой нормы, со дня направления претензии» (recheck report, A2 section). The new wording in file 10 follows the same structure and wording. It closes the file 10 part of the open gate that the recheck report named (CONSISTENCY_GATE_01_03_10_OPEN, the line on `10-obrashchenie-v-sud.docx`).
- **"Иной порядок" (a different procedure):** this is not mentioned. As with A2, I do not count it as an overclaim, because this checklist row is only about the deadline.

**Secondary text vs. official currentness.** `secondary-apk-4.txt` is a secondary excerpt from a commercial legal-database site (consultant.ru): `source_class=secondary`. It includes the vendor's notes and links (for example L35–36, «КонсультантПлюс: примечание»). This review only confirms that the wording matches **that excerpt**. Whether the official, currently in-force text of part 5 of art. 4 of the Code matches it has **not been checked** (no network access allowed).

## 5. Blockers

**None** for the scope of this correction.

## 6. Remaining gates (none of them block this correction)

1. **Layout gate.** root-visual.json is author/coordinator evidence only. It says `final_layout_acceptance: false` and notes a pre-existing issue: checklist row 7 splits across pages without a repeated header. I did not view any renders. The new text is 52 bytes longer, which may move the row and page breaks in table 0, so a person needs to look at the layout again.
2. **Official-currentness gate.** The wording needs checking against the official, currently in-force text of art. 4 of the Code (part 5, paragraph 1). The checklist row «АПК РФ, действующая редакция» already sends the user to the current version.
3. **Human legal gate.** LEGAL_ACCEPTANCE_NOT_PERFORMED. No legal choice for any individual dispute was required or made.
4. **Consistency gate for files 01 and 03.** According to the recheck report, the same uncorrected wording was still in `01-karta…` (the C2 analogue) and `03-algoritm…` (the C2 and A2 analogues). I did not check whether those were fixed elsewhere; this candidate does not touch them. Note that scope-proof lists 01 and 03 among the unchanged files, so as of this commit that gate stays open for them.
5. **Not done:** independent tests (the author's "13 PASS" was not checked), rebuilding the generator, viewing renders, and confirming the files against git.

## 7. Conclusion

- The one-line correction to file 10 is **acceptable (ACCEPT)**:
  - Only `word/document.xml` changed.
  - Only one table cell (T0R2C1) changed.
  - The generator line matches the DOCX change exactly.
  - The wording matches the condition in the supplied secondary excerpt of part 5 of art. 4 of the Code, and matches the accepted A2.
- Layout, official currentness and human legal acceptance remain open, as do the gates for files 01 and 03.

I made no external requests, no edits to files, and no git/gh calls. I used only Read and python3 for local, read-only checks.