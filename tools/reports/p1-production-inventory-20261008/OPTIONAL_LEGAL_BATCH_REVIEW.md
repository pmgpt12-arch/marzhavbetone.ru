# Separate disabled proposal: one official-source batch from established hosting

**Not pushed or executed.** `RUN_LEGAL_SOURCE_BATCH: 'false'` is the default. Root may enable it once before the exact feature branch is first created, after reviewing this committed diff. No dispatch, later push retry, schedule, model call, fallback URL or crawler is provided. This optional step is separate from the production order inventory and must not be treated as evidence of historical order/archive authority.

The hypothesis is whether the already authorized hosting network can retrieve five known official URLs where the prior home network returned errors/partial evidence. Existing `curl` CLI is required; absence yields `CURL_CLI_UNAVAILABLE`, without install. Reviewed Python source arrives over the same established SSH stdin; host temporary files and bytecode caches are disabled. Curl writes body stdout and headers `/dev/stderr` into SSH process pipes. Only runner artifacts are written. No body, headers, credential, host path or raw SSH diagnostic is logged.

| Fixed source | Known exact URL | Body cap |
|---|---|---|
| GK II | http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102039276 | 8MiB |
| NK II | http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102067058 | 8MiB |
| 127-FZ | http://pravo.gov.ru/proxy/ips/?docview&page=1&print=1&nd=102078527 | 8MiB |
| PPVS 7 registered card | https://vsrf.ru/documents/own/8478/ | 2MiB |
| PPVS 54 known card | https://vsrf.ru/documents/all/8524/ | 2MiB |

Provenance: legal peer's exact previously used official `nd` IDs and registered/known court cards, selected by root from `P1_bounded_host_legal_fetch_proposal_2026-10-08.json`; no route guessed. The already captured PPVS7 PDF is deliberately excluded because it does not establish current consolidation by itself. Prior home network observations: GK II and NK II HTTP500, 127-FZ timeout; current-consolidated PPVS7/54 authority remained unverified. No result is promised.

At most three concurrent requests; one invocation per fixed URL. `--max-time 12`, `--retry 0`, `--max-redirs 0`, no `-L`, `--proto =http,https`; 3xx stays an unverified captured response. `-q` disables curlrc; proxy/credential/SSL-key-log environment is not inherited. Hosts are fixed to `pravo.gov.ru` and `vsrf.ru` (allowlist also permits known `www.vsrf.ru` but no redirect is followed). Total body budget 28MiB, headers cap256KiB per response, SSH batch timeout60s, parent workflow five minutes. Process pipes enforce caps and terminate an overflowing process. No raw CLI stderr survives into source artifacts; only complete HTTP header blocks are retained.

Runner validates exact five identities, types, byte limits and SHA256 before saving `.body`, `.headers` and receipt JSON under `legal-source-output/` for seven days. Nonfinite/oversized times, forged URLs, unexpected fields, invalid hashes and redirected-count values reject the entire batch with a fixed sanitized receipt. Capture receipt preserves HTTP status, curl exit code, timing, caps and body/header SHA. Every source remains `NOT_VERIFIED`, including HTTP200: textual completeness, consolidated edition/date and legal applicability require independent review. Errors/partial content do not establish normative freshness or SALE_READY.

Targeted tests: `python3 -m unittest discover -s tools/tests -p 'test_p1_production_inventory*.py' -q` — 33 pass in scratch, no external request. The legal worker test replaces curl with a local fixture subprocess and exercises actual OS pipes; transport tests mock SSH, so no production host is contacted by tests.
