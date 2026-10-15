# SSL-мониторинг — обязательный gate запуска

**Owner approval:** 2026-10-15 · **Main project:** #653 · **Scope:** только мониторинг, никакого изменения сайта, DNS, сертификатов или оплаты.

## Что контролируем
Ежедневно примерно в 08:17 Asia/Krasnoyarsk (cron 01:17 UTC) GitHub Actions проверяет:
- `https://nastoronepodryadchika.ru/` и `https://www.nastoronepodryadchika.ru/` (SSL-chain+SNI/SAN, срок действия, HTTP status и конечный HTTPS-хост);
- доверенный origin TLS для обоих имён напрямую по `37.140.192.133` (после переноса origin IP в workflow обновить);
- остаток до истечения TLS: <=21 суток WARNING, <=14 суток CRITICAL, неверный/просроченный сертификат или ошибка DNS/HTTPS — CRITICAL.

## Оповещения
При WARNING/CRITICAL workflow сохраняет JSON-artifact, завершает проверку с ошибкой и создаёт один GitHub Issue `[SSL-WATCH] HTTPS/сертификат — nastoronepodryadchika.ru`. Эскалация WARNING→CRITICAL создаёт комментарий; повтор того же уровня не создаёт спам; после восстановления Issue закрывается с отметкой. История проверок хранится в GitHub Actions (90 дней для artifacts).

Отдельно включён ежедневный ChatGPT condition watch. **Telegram-бот для публикаций не используется как канал личных аварийных уведомлений**, чтобы не рассылать сведения о неисправностях покупателям.

## Проверки и доказательства
- No-network: `python3 -m unittest discover -s tools -p 'test_ssl_*.py' -v`. 21/21 PASS на изолированной среде и 21/21 PASS с исходниками GitHub на ai-workstation 2026-10-15.
- Negative cases: истечение, пороги 22/21/14 дней, CA-trust failure, SAN mismatch, DNS failure, timeout, устаревший origin certificate, open/escalate/dedupe/close alert.
- **Live real-network check** тем же скриптом из GitHub branch на ai-workstation: 2026-10-15T15:52:33Z, apex+www HTTP 200, публичный+origin TLS PASS, SAN верный, срок `2027-01-13T14:32:06Z`, статус OK, `89.94` дня осталось. Artifact: `docs/brand/ssl-watch-live-20261015.json` в этой ветке.

## Acceptance / VERIFIED DONE
- [x] Monitoring code and workflow in separate branch.
- [x] Unit/regression tests 21/21 PASS; artificial errors **detected**.
- [x] Live check both domains / both origin SNI PASS from ai-workstation.
- [ ] PR merged to default branch **after reviewing production deploy trigger**. Scheduled workflow lives only on default branch; PR is not enough.
- [ ] First manual GitHub workflow_dispatch: artifact uploaded, job status recorded.
- [ ] GitHub Issue creation/recovery notification E2E tested in controlled scenario, no false public customer message.
- [ ] First actual scheduled GitHub Actions run observed.
- [ ] User notification delivery confirmed for the selected channel; GitHub Issue existence alone does NOT guarantee the owner received a push/email.

**No green DONE until all acceptance points checked.** This is a release gate, not grounds for deleting products or changing production credentials.
