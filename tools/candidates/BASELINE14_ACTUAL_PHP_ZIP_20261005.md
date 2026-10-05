# Фактические PHP ZIP для 14 базовых позиций

Для 14 ранее исследованных позиций не было доказательства фактических байтов PHP-архива на cached baseline. Исходная mvb_build_product_zip() вызвана по одному разу для каждого SKU в 4 независимых thread lanes. Получены 14 ZIP и 135 member bindings; точные серверные пути, размеры, SHA256 и членство сохранены в author-summary.json и independent/actual-archive-facts.json.

Источник 264d75a06d59de82602dc1bcef347913c44cc648; frozen membership 7ef66ed269183a671269c033d80b4c85f06eff53a452b4e4cd3a3a15b8b4e08e; sealed registry/function config 7f7cca1e7344a3ad69041049b926e2a9766de1ba93d9de3de70641875261f7fb. Задаётся отдельная lane для каждого набора временных PRODUCTS/ORDERS/DELIVERY paths. Live-функции заказа, оплаты, письма и HTTP не вызывались.

Независимая приёмка: 1074 проверки, 0 ошибок. Подтверждены уникальные безопасные имена, точное membership, CRC, raw member SHA256/размер/Gitblob, 150 исходных копий до/после, 4 config copies и 229 исходных frozen execution files. Повторных PHP-сборок, OOXML/цитатных parser checks, render/calc, моделей/API не было. Native runner 1980739/parent 1980738 завершились exit 0; 4 workers были threads. PHP 8.3.6/ZipArchive 1.22.3 captured; SHA бинарника PHP не записан и не заявлен.

Evidence: tools/candidates/evidence/BASELINE14_ACTUAL_PHP_ZIP_20261005/. 71 файлу соответствует compact SHA256SUMS.json; сам manifest — 72-й файл. Отдельно расположен этот отчёт. Все 14 ZIP bytes и 150 source copies исключены из Git и остаются на сервере; их точные paths/hashes сохранены. server-full-run-SHA256SUMS.json — исторический серверный manifest 229 файлов, а не утверждение о Git-копировании всех 229. Исторические PENDING snapshots сохранены неизменными; final-scoped-acceptance.json отмечает независимое ACCEPT без новой продуктовой приёмки.

Это доказательство только cached baseline архивов, а не утверждённой текущей переупаковки или клиентской выдачи. Формулы, читаемость/печать/ручной Excel, юридическая семантика/текущесть/человек, owner и release/SaleReady остаются отдельными гейтами. Исходные продукты не менялись; изменяются только отчёт и компактные доказательства. Четыре ранее принятых модуля и 14 baseline источников не исправлялись.

Numbered source snippet хранится в Git как lossless actual-config-source-snippet.txt.gz; roundtrip восстановил exact SHA256 6ecee2d5a0b0cfff74a7be798f4794cda7a52ffac8a19f3f2bb39c1385fcb992. Raw server snippet, root approval pins и исходные пробелы не менялись. Это только представление доказательства.
