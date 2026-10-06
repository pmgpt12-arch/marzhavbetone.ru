# Actual PHP ZIP — только изолированный baseline

На cached 264d75a06d59de82602dc1bcef347913c44cc648 один раз вызвана исходная mvb_build_product_zip для 14 выбранных SKU в 4 независимых Python thread lanes. Созданы 14 архивов, 135 member bindings. Фактические имена, байты, SHA256 и CRC каждого члена совпали с frozen source membership 7ef66ed; конфигурация 7f7cca неизменна. Это новое доказательство работы существующего PHP-сборщика на cached baseline, а не утверждённая выдача переупакованных продуктов.

Результаты сохраняются по SKU в actual/lane-N/*-receipt.json; native process/exitlog — process-start.json, execution-receipt.json, execution.log. Архивы и копии исходников остаются только на сервере. В последующее Git-доказательство входят компактные receipts/hash manifests, код запуска и независимая приёмка; полный server manifest содержит также исключённые байтовые файлы и не должен представляться Git-копией всех 229 файлов.

Source copies и sealed config сохранены точно до/после; в live products/orders/delivery нет записи. Функции заказа, оплаты, письма и HTTP не вызваны. Модели/API USD 0; render/calc, структурные и цитатные проверки не повторялись. Источник четырёх принятых модулей не менялся.

Текущий gate: independent archive-only QA pending. После её ACCEPT — root review компактного evidence scope перед documentary Git commit. Formula/layout/currentness/human legal/owner/release/SaleReady гейты этим доказательством не закрываются.
