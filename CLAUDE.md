# «Маржа в бетоне» — обязательный session preflight

## SESSION_POLICY_GATE

В начале **каждой новой сессии, до формирования или делегирования задач**
применить корневой [AGENTS.md](AGENTS.md) этого репозитория и прочитать
по актуальному `main` канонического `pmgpt12-arch/ai-business-os`
`CLAUDE.md`, `AGENTS.md`, `docs/Task_Setting_Protocol.md` (раздел 0).
Координатор подтверждает проверенный SHA и
`SESSION_POLICY_GATE: PASS` в существующем паспорте задачи до Issue/READY.
Если политика недоступна — `BLOCKED / POLICY_NOT_LOADED`, без новых задач.

**GH-first:** GitHub-коннектор — основной транспорт управления, локальный
ai-workstation dispatcher/runner — исполнитель; Desktop Commander —
аварийный резерв, а не shell-пул или канал бинарных файлов. Не создавать
вторую очередь и не затрагивать выполняемые продуктовые задачи.
Подробности: [решение #542](https://github.com/pmgpt12-arch/ai-business-os/issues/542#issuecomment-6056054483).

Этот указатель не подменяет полный протокол и не даёт права менять
цены, SKU, оплату, публикации, deploy или принимать продукт без проверки.
