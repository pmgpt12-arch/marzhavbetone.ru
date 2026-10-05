# MB001 S1 unique fields — independent F5 review

- Source PR: 429, SHA `c9f480de1c7eb2e8ef123f077449ef69a24ee015` (worktree HEAD verified equal)
- Scope: F5 only (10 contextual placeholder renames)
- Inputs: `s1-f5-inputs/index.json` (0-receipt.json, 1-passport.json)
- Reviewer: independent (not the author)
- **Verdict: ACCEPT**

## What I checked myself

1. **Code delta** (`git show HEAD -- tools/build_s1_candidate.py`): 12 changed lines, 6 removed and 6 added, all in `f06` and `f10`. Every changed line differs from the old line only in the token names:
   - f06: `{{ДАТА}}` → `{{ДАТА_ОПЛАТЫ_ПО_ТРЕБОВАНИЮ}}` (payment deadline), `{{ДАТА}}` → `{{ДАТА_РЕЕСТРА_ВЗАИМОРАСЧЁТОВ}}` (registry date)
   - f10 claimant: `ИНН/ОГРН/АДРЕС` → `ИНН_ИСТЦА/ОГРН_ИСТЦА/АДРЕС_ИСТЦА`
   - f10 respondent: `ИНН/ОГРН/АДРЕС` → `ИНН_ОТВЕТЧИКА/ОГРН_ОТВЕТЧИКА/АДРЕС_ОТВЕТЧИКА`
   - f10 pretension: `{{ДАТА}}` → `{{ДАТА_ПРЕТЕНЗИИ}}`; f10 signature: `{{ДАТА}}` → `{{ДАТА_ПОДПИСАНИЯ_ИСКА}}`
   - No other wording, calculation or layout code changed. No Calc or spreadsheet files are in the commit.
2. **DOCX mechanical proof** (my own script: `run/430/f5_check.py`, comparing HEAD~1 with HEAD):
   - ZIP entry lists are identical in both files. Every entry except `word/document.xml` is byte-identical.
   - Token sequences: 06 has 22/22 tokens with exactly 2 changed; 10 has 35/35 tokens with exactly 8 changed. **Total: 10.**
   - Each new token occurs exactly once.
   - After mapping the new tokens back to the old ones, the new `word/document.xml` is **byte-equal** to the old one in both files. So the 10 renames are the only text changes.
   - No bare `{{ДАТА}}`, `{{ИНН}}`, `{{ОГРН}}` or `{{АДРЕС}}` remains in 06 or 10.
3. **Distinct-party/date replace-all check**: `python3 -m pytest -q tools/test_s1_unique_fields.py` gave `2 passed`. The test fills each token through replace-all and confirms that claimant and respondent details, and the payment, registry, pretension and signature dates, land in their own positions.

## Coverage of the original independent415 F5 defect

- The payment deadline and registry date that shared one token are now separate fields.
- The claimant and respondent no longer share INN/OGRN/address tokens.
- The pretension date and claim signature date are now separate fields.

## Residuals / not in scope

- F2, F3, F4, F6 and F7 remain open and were not reviewed.
- I did not rerun the full buyer flow, Calc or legal audit (per contract).
- Tokens shared on purpose across the claim (`{{СУММА_ДОЛГА}}`, `{{ФИО}}`, `{{ТЕЛЕФОН}}`, `{{EMAIL}}`, `{{НОМЕР}}`) were not judged; that is outside F5.
