# Agent instructions — «Маржа в бетоне»

## SESSION_POLICY_GATE — обязательно до постановки любой новой задачи

В каждой новой агентской или координаторской сессии **до** формирования,
декомпозиции, создания Issue/READY, передачи или запуска задачи прочитать
из канонического `pmgpt12-arch/ai-business-os` (актуальный `main`)
три документа с проверкой полной ревизии (40 hex SHA):

1. [CLAUDE.md](https://github.com/pmgpt12-arch/ai-business-os/blob/main/CLAUDE.md)
2. [AGENTS.md](https://github.com/pmgpt12-arch/ai-business-os/blob/main/AGENTS.md)
3. [docs/Task_Setting_Protocol.md](https://github.com/pmgpt12-arch/ai-business-os/blob/main/docs/Task_Setting_Protocol.md), особенно раздел 0

Перед постановкой новой задачи записать в существующие поля её паспорта
источник, полный SHA прочитанных правил и `SESSION_POLICY_GATE: PASS`.
Без чтения или при недоступности правил — `BLOCKED / POLICY_NOT_LOADED`;
не создавать READY и не выдумывать содержимое. Рабочие задачи не останавливать.
Локальному исполнителю без сетевых разрешений координатор передаёт политику
в проверенном контекстном пакете — не выдавать модели `gh` ради проверки.

**GH-first:** ChatGPT управляет Issues, Draft PR, статусами и проверками
через GitHub-коннектор; существующий ai-workstation dispatcher/runner
исполняет работу локально. Desktop Commander Remote MCP — только резерв
для узкой runtime-диагностики, bootstrap и аварийного восстановления.
Не расходовать его на мелкие shell/read_file/polling и бинарные
base64-чанки; не создавать второй dispatcher/router/queue.
Директива: [ai-business-os #542](https://github.com/pmgpt12-arch/ai-business-os/issues/542#issuecomment-6056054483).
Изменение канала не отменяет качество и обязательную приёмку продуктов,
проверку цен, юридических и расчётных материалов, ограничения публикации
и существующие owner gates.

Инструкции в файлах не гарантируют автоматическую загрузку произвольным
чатом ChatGPT: координатор проверяет чтение до каждой новой постановки.
