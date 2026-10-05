# Независимая фактическая проверка текущего S1 citation inventory

Вердикт: **ACCEPT_FACTUAL_INVENTORY**. Проверен frozen inventory SHA-256 `5f2ac5ec7950ff21de17d8907fe2d6bd2973dc422f516426f76061d6b98f3c05` на exact source `a77422195c2c68281a7797ad99f9f6b70426d740`. Авторский checker не запускался. Python/CLI, модельных вызовов0, APIрасход$0.

Независимо прочитаны Git blobs всех11 покупательских файлов, включая00-START-HERE.txt. SHA-256, Gitblob, размеры и sourceSHA согласованы с новым inventory и inputmanifest.02/08 привязаны к исправленным версиям `5918714b4e4e95abc546e1fe7a43f515af50680ecf75352a2949a2ebecac47f0` / `e0ed0206c17f1b3638bba14dd472c3acad0da80c87dd640169e9c094dec266b4`;04 сохраняет native `f735e85286952a2780d413aea7debbe7a7ceda24edf717d79b631a4aad8945d9`.

47 literal occurrences и23 unresolved markers проверены против собственных4478 native visible fragments: полные координаты, границы literal/quote span и дословные shortquote совпадают. Для DOCX дополнительно независимо разрешён каждый XMLXPath в actual word/document.xml и согласованы физический/непустой ordinals; для XLSX — native sheet/cell/stored string type, для TXT — physical/nonempty line. Наблюдаемое codebinding и article numbers as written проверены как грамматика, без толкования применимости закона.

Альтернативный broadscan использует ст./статья/ГК/АПК/Пленум/Федеральный закон/№+число. Все42 найденных source passages по11файлам представлены фактическими47occurrences/23markers; каждый broadtoken пересекается с соответствующим записанным span. В дополнительно просмотренных header/footer/footnote/endnote/comments/drawings и formula-text не найдено дополнительных broad-law-token hits. Это не доказательство полноты всех правовых механизмов без явной ссылки.

24 dedupgroups сохраняют все47 IDs ровно один раз; groupkey соответствует literal/code/articles as written. Это24 группы цитат, не24 нормы.23 markers — не23 юридических дефекта. Неоднозначные наблюдаемые привязки ref-0027/ref-0028/ref-0047 оставлены с code=null/UNRESOLVED; в том числе полное название кодекса/ФЗ не превращено догадкой в registry norm ID. Все registry_norm_id=null.

4 required old input hashes подтверждены: literal-reference-map, buyer-claims-index, Normative_Contract и Task_Setting_Protocol.58 old rows явно перепривязаны без наследования старого нормативного вердикта. Отдельно проверены exact-literal occurrence IDs и все substring text locations в текущих native fragments. Эти два поля описывают разные множества; включение «ст.395» внутрь «п.4ст.395» не требует идентичности их списка IDs. Initial review содержал6 ложных mismatches из-за ошибочного требования равенства этих множеств; первичный receipt сохранён, checker assumption и правило исправления зафиксированы отдельно. Авторские artifacts не менялись.

В frozen sourceGit отсутствуют4 data/legal YAML из нормативного контракта. Inventory не создаёт их и не назначает фиктивных registry IDs. currentness=NOT_VERIFIED, normative_verdict=NOT_VERIFIED, human_legal=NOT_PERFORMED. Эта приёмка подтверждает факты карты/цитат/адресов и покрытие заданного literal scan; не подтверждает применимость, действующую официальную редакцию, юридическую приёмку человеком или SALE_READY.

## Доказательства

- `author-artifact-pins-before-review.json`:6 frozen author artifacts, после проверки все hash неизменны.
- `independent-input-hashes.json`:11 actual sourceGit buyer hashes.
- `independent-required-old-input-hashes.json`:4 required old-map/contract input hashes.
- `independent-visible-fragments.json`, `independent-broad-token-hits.json`, `independent-extra-part-hits.json`:собственная extraction, не авторские42134 units.
- `review_inventory.py`:независимый проверочный script.
- `independent-check-details.json`, `independent-broad-coverage.json`, `independent-review-receipt.json`:actual checks иcoverage; ошибок0.
- `initial-review-superseded-checker-assumption.json`, `checker-assumption-root-cause.json`:сохранённая история неверного checker предположения.

Исходные buyer/source файлы, авторская карта/скрипт не изменялись; тесты продуктов, рендеры, новые модели или merge reviewer не запускались.
