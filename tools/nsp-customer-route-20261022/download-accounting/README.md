# Download accounting — draft PR #676 only

Owner authorization on 2026-10-23 applies exclusively to download accounting in this draft PR. No merge, deployment, publication, real payment, production edit, or live YooKassa credential change is authorized or performed.

Runtime patch source: `edf9007ca32908cfec83966dcb2129f6236c0ffe`.
Parent reviewed staging HEAD: `d636352c844f2d2e9904b21109912feab55224a5`.
Endpoint SHA-256: `da9106dc24fd255c9523e352fab8a14e04f3d6fda86d8a03972a4d85861e7b2e`.
The earlier followup2 proposal remains historical; this applied patch implements the owner's additional outcome/privacy/idempotency conditions.

## Behavior

- Existing access checks, token comparison, expiry, reservation/limit, archive rebuild and readfile download remain in place. Existing response bodies/statuses are unchanged.
- GET of an existing order produces a private `download.link_opened` observation. It is never delivery confirmation. HEAD is excluded; fabricated/malformed nonexistent orders do not create receipt files.
- `download.file_served` requires readfile to return the full archive byte count and no observed disconnected connection. This confirms the server-side write, not storage on the buyer's device.
- `download.failed` records an enumerated outcome (access denied, expired, missing file, limit, server/read error). A read failure after headers keeps the original HTTP behavior and records failure rather than delivery.
- Private observations live under the existing protected outbox's `download-receipts/` directory. Only successful delivery enters the existing canonical queue as `funnel.product_delivered`; no new event types are sent to the existing consumer.
- Receipt keys deduplicate order/trusted SKU/outcome/reason. Repeated lawful downloads still serve the same bytes and use the existing download counter/limit. Refresh, retries and concurrent requests do not generate a new delivery identity.
- Receipt initialization and updates share the existing strict file lock and atomic writer. Failed queue writes remain retryable with the same UUID. If append succeeds but the receipt rename fails, the transport can contain a replay with the same UUID; the consumer's actual unique index prevents a second analytics row.
- Privacy whitelist: event type, stable opaque UUID, UTC time, server-known SKU or null, outcome status/reason, and private queue flag. No token, raw order ID, query string, buyer name/email/phone, IP, path, secret, or archive bytes are serialized.
- Telemetry failures do not deny or alter a download. Consequently a storage/process failure can lose an observation; there is no claim of guaranteed exactly-once capture across arbitrary crashes.

## Verification

Native isolated PHP receipt: [NATIVE_ACCEPTANCE.json](NATIVE_ACCEPTANCE.json).
Consumer proof: [CONSUMER_REPLAY.json](CONSUMER_REPLAY.json).

Native run UTC 2026-10-23 01:01:33 (08:01:33 Asia/Krasnoyarsk); all seven command groups exited 0:

1. 13 real HTTP download tests: valid/repeated GET, expired link, wrong token then valid retry, missing file/reservation rollback, malformed order/server failure, HEAD, twelve concurrent GETs, failed queue append/recovery, unavailable analytics library, actual builtin readfile failure, untrusted SKU privacy, receipt write failure/replay, initial receipt readiness.
2. Actual consumer `events.record()` and its actual unique UUID index in SQLite `:memory:`: two same-UUID attempts create one row; another UUID creates a second. Connector source forwards UUID. No live receiver/database call.
3. Download limit: 30 successful responses, 10 HTTP 429; no lost counter updates. Existing `chattr +i` end-to-end fault subcase unavailable on this host; function-level temporary-write/rename/strict-lock failures pass.
4. Eight-process order-lock regression passes.
5. One-hour expiry: future 200, boundary/expired 410.
6. Archive cache freshness: four checks pass.
7. Synthetic P3 checkout/mock API/duplicate webhook/email body/HTTP ZIP: 11/11 current member hashes pass. Provider is loopback-only, real provider calls/payment creations 0, mail disabled.

The first native attempt exposed a test readiness race at the initialized empty receipt. The receipt now starts as a JSON object; the test waits for durable observations and explicitly covers the initial empty state. The final native run tests the exact endpoint hash above.

Local: the same 13 HTTP tests and seven real-Git scope mutation tests pass; exact source gate passes for all 694 relevant tracked paths. The local historical snapshot test cannot initialize because old Git blobs are absent; full-history CI is the acceptance source for that suite.

The additional blocking public check is `test_download_events`; existing workflows/checks remain enabled. The source gate preserves the exact earlier contacts patch, authorizes only this endpoint blob and rejects subsequent dirty or committed endpoint drift. Historical reports are unchanged.

No test Shop ID is required for these synthetic checks. They do not establish the real YooKassa payment chain. Existing unrelated legacy Metrika test limitations remain as recorded in followup2; no claim that every ad hoc historical test passes.

## Files changed by this authorization

- `download.php` — the sole runtime change.
- `tools/test_download_events.py` — isolated HTTP/privacy/fault/concurrency regression tests.
- `tools/check_download_consumer_replay.py` — actual consumer in-memory UUID replay check.
- `tools/ci_checks.yaml` — additional blocking test.
- `tools/check_p3_current_site_delta.py` — exact approved endpoint exception.
- `tools/test_staging_source_scope.py` — reject later dirty/committed endpoint changes.
- `tools/nsp-customer-route-20261022/download-accounting/README.md`
- `tools/nsp-customer-route-20261022/download-accounting/NATIVE_ACCEPTANCE.json`
- `tools/nsp-customer-route-20261022/download-accounting/CONSUMER_REPLAY.json`

Final branch SHA and CI run results are recorded in the PR description after the commit is pushed; this avoids a new commit solely to embed its own SHA. Draft/release/publication holds remain in effect.
