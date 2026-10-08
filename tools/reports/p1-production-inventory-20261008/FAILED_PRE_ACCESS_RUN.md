# Preserved failed pre-access attempt, 2026-10-08

Root-reported GitHub run: 37760344157, branch `codex/p1-production-inventory-20261008`, enabled tree `23fdfd7cb02bb70b44b4b086cfb1e9c717fd4665`.

The scratch safety suite asserted the proposal's disabled-by-default value even though root's explicit pre-run approval had enabled the optional batch. The run failed at tests before SSH key establishment/keyscan, inventory execution or official-source requests. Root explicitly confirmed no hosting or legal request occurred. This record relies on root's inspected run evidence; the author has not independently fetched CI logs.

The correction creates a separately reviewed exact branch `codex/p1-production-inventory-reviewed-20261008`, preserves branch-creation-only gating and allows an enabled tree only with exact root approval assertions. Tests still verify a disabled proposal fixture. Reviewed inventory and source workers are unchanged. No blind re-dispatch, retry or runtime recovery is added. Maximum actual production read remains one, after root's independent review and initial push of the new branch. Author has not pushed or executed it.
