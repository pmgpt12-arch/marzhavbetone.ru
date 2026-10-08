# Root pre-run review, 2026-10-08

ROOT_APPROVAL_STATUS: APPROVED_ONCE
ROOT_APPROVAL_BRANCH: codex/p1-production-inventory-reviewed-20261008
ROOT_APPROVAL_IMPLEMENTATION: 4c787439170e211d967920a2517c758b4d1a8c81
ROOT_APPROVAL_MAX_PRODUCTION_ATTEMPTS: 1
ROOT_APPROVAL_LEGAL_BATCH: EXACT_FIVE_KNOWN_URLS_ONCE

Root read the complete inventory worker, SSH transport/schema validator, optional source worker, workflow and two safety reports at 4c787439170e211d967920a2517c758b4d1a8c81, recorded original approval in 23fdfd7cb02bb70b44b4b086cfb1e9c717fd4665, and explicitly authorized the new exact reviewed branch after the pre-access test failure (see FAILED_PRE_ACCESS_RUN.md).

Accepted scoped read-only implementation: no host writes, Python -B, FD-anchored known scope, PII/secret-free strict report, no PHP execution, preserved unknown/historical status. Accepted exact five official GETs once, three workers, twelve seconds/request, no redirects/retry/fallback, bounded pipe capture and runner-only artifacts. Worker/transport source is unchanged from the reviewed implementation.

The optional source batch is enabled solely on initial creation of this new exact branch after root independently reviews the correction. No main merge, deploy, payment/email, migration or recovery is authorized. A test verifies these exact approval assertions before host access and rejects missing/altered approval; a disabled fixture remains valid without approval.

Root interprets facts independently; generic unknowns are not evidence of actual missing purchases, and HTTP200 is not legal PASS. The old failed branch/run is not re-dispatched or retried.
