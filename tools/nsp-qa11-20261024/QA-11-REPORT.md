# НСП — QA-11. КС без возврата

**FULL_QA_PASS для отдельного QA ZIP. Публикация запрещена.**

## Исходники
Публичный SHA: c1cb90e49e4bca59d236782da15ff2d92b6738c2fcb5c5702509d835a3fa3ad4
Git SHA: 3b4def817cbe40392bf51c9699a3afbdddcd7b690f8def017ac80447e80838e1
Старый READY_CANDIDATE: d9585b46988ef4320ddf455e3ea6418f8dfd502e991cf4291b196ffceff5f67a

## Матрица

| Файл | Статус | SHA-256 |
|---|---|---|
| 01-proverochnyy-list-komplekta-ks.docx | PASS | 4a56a0006c74e638cba1da7ba8db615271b4701ec98542e7139e39534f747ce5 |
| 02-reestr-prilozheniy.xlsx | PASS | 0bb7ec884ba3df55b571be3c9806afce985f97ad1d01423d25413480bf8c4090 |
| 03-tipovye-prichiny-vozvrata.docx | PASS | 5d67dd62f064c23ebbcd2ebb9d93ca0c1d3634c02333b8a14025066b059e2d99 |
| 04-poryadok-vnutrenney-proverki.docx | PASS | 0052a9340e155e5864ca2a8e5bc040431dddf731202cdedb58e63bda5561f6ce |
| 99-chto-dalshe.pdf | UNCHANGED_ACCEPTED | bda7163b4c6af2897108b49a88c793b61c18d972827e4ae10e98d05e29e75032 |

## Закрытые дефекты

Разделены обязательные приложения, договорные требования и рекомендации. Универсальная обязанность подписи бухгалтера и печати исключена. Формы КС-2/КС-3/КС-6а и полномочия сверены по применимому основанию. Отправка, доставка и приёмка разделены.

Excel ограничен штатными строками 2–6, контроль отрицательного/текстового ввода и итога 11 листов прошёл. Excel 2016 PASS, сохранение/повторное открытие и одностраничная печать PASS.

Word 2016: 3 изменённых файла PASS, 3+2+2 страниц. Исходный PDF одна страница UNCHANGED_ACCEPTED. Итого 9 страниц визуально проверены.

Покупательский QA ZIP CRC/XML/SHA PASS: f0ffd8d55a4468f1542bd59d0a02cf87d49027f43d141f1c23197953fea9fcbe

QA-01–QA-10 и 13 утверждённых файлов сохранены без изменений. Main, production, публичный архив и PR #676 не менялись. Merge, deploy и публикации не было; контрольная точка QA-11.
