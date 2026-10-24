# НСП — QA-12. Аванс и обеспечение

**FULL_QA_PASS для отдельного QA-кандидата, без публикации.**

## Исходники
Публичный ZIP: 7e87570bbd42da3326823261a842e6544c5b7588bc3487633e70e3d5c9b6999b
Git ZIP: d9c29eb2a01d6a5484eabc5eb588a826addc0f28e23a9de4d85e0b549bad573e
Прежний кандидат: 5430fc6ea7781fadf586e7c601436ff6f10bd3a927b263358069b3c66cd35c16

## Пять файлов

| Файл | Статус | SHA-256 |
|---|---|---|
| 01-proverochnyy-list-usloviy-avansa.docx | PASS | b463a813e9909919fe40b830ab5fae03279fa2b0457f0e8b9540672dbea895d1 |
| 02-reestr-izyatiy-po-obektu.xlsx | PASS | a0df16f013f7d1e9be514eec50bb0f91905a6838d1b0c72455616003703711b9 |
| 03-formulirovki-lovushki.docx | PASS | 387a666a599cd3e982d5f95ea1c2e5514bb1897f1f33ce39616f108a88a43164 |
| 04-zapros-ob-usloviyah-avansa.docx | PASS | 331c71d3a2ca0da055f6a2cd05b31c538dbb5636d28b08fde168af36f39f1e3e |
| 99-chto-dalshe.pdf | UNCHANGED_ACCEPTED | dbb806e80627e9c451baca2a50a18edfb454db7ea5aed572f0205c9c57e71c26 |

## Закрытые проблемы

- Разделены перечисленный аванс, погашение, удержание, расходы на гарантию, обеспечение и спорная дебиторская задолженность.
- Требование возврата неотработанного аванса обусловлено договором, встречным исполнением и установленными фактами; не возникает автоматически из расчётной строки.
- Реестр больше не суммирует семь экономически разных величин: D12 отражает исключительно независимые подтверждённые блокировки 90 000 ₽; 400 000 ₽ аванса, расходы 5 000 ₽ и дебиторская позиция 100 000 ₽ показаны отдельно.
- Формула отличает подтверждённый ноль от отсутствия подтверждения, выявляет текст и отрицательный ввод. Независимость обеспечительного платежа D8 и покрытия D7 проверяется по документам.
- Excel 2016: восемь сценариев PASS, сохранение и повторное открытие PASS; печать двух листов PASS. Word 2016: 3 DOCX PASS (6+4+4 страниц). PDF 1 страница без изменений. Визуально 17 страниц PASS.
- Нормативные ориентиры на 24.10.2026: ст. 381.1, 410, 711, 717, 720, 746, 753, 1102–1103 ГК РФ; применимость к сделке определяют отдельно.

## Итоговая бесплатная линейка

| Материал | Статус | Публичный SHA-256 | QA SHA-256 | Git отличается |
|---|---|---|---|---|
| checklist | FULL_QA_PASS | 65ec8f7880adc4bf9d611888bf16f332415bc7b6da97fcf577fd29e38dba42c4 | bd50ad14084fbf91f2c575718e9d5f66c533ee5d1fd5dfc34eeaae2c34455394 | да |
| dengi | FULL_QA_PASS | f8166b4c029df501d53ea3b3b7d57b17e15a1ffbbc8d20f315b3333a19e9cc33 | 024fe485d70bf2e55775ad3d1aae45bccc2ebd94502a26f4f938366e551d9ff1 | да |
| dop-raboty | FULL_QA_PASS | 66544cb03c67218a988db0413de339ca48abf36af93f02d9a842d014b8991157 | e09176633507ec8c148547c89bcb278525d0df1d26274a385c6fc6751fd7a43e | да |
| vozvrat-ks | FULL_QA_PASS | c1cb90e49e4bca59d236782da15ff2d92b6738c2fcb5c5702509d835a3fa3ad4 | f0ffd8d55a4468f1542bd59d0a02cf87d49027f43d141f1c23197953fea9fcbe | да |
| uderzhaniya | FULL_QA_PASS | 07f372b8cd43b3a6a31f20834290e99ac25a2012ed91472ec01cd12004281122 | 77ef9381b960176e152bee757e3d497e9c8bcaecc20bbeb96ed6b1f5de99e1e0 | да |
| dogovor | FULL_QA_PASS | be4df3d43d23361ac9c8c200ffce5839c862cb078a91d949aae5da46735efa9a | b9a3fd2bb0e9477aef799c0a44e555a77aac281a6176d422a2f38bcc1d181f30 | да |
| bankrotstvo | FULL_QA_PASS | 0de62a32042330fba008dfcd7ac61dbbe43eba9ab7b9dff24f752c498a47edfa | 68a1d82c16fb3c141dfa4778fc96ac03f2a058eafea5fd287103c0103903b393 | да |
| avans | FULL_QA_PASS | 7e87570bbd42da3326823261a842e6544c5b7588bc3487633e70e3d5c9b6999b | 06d8e851d8bc736fa56165dd73ef8cbd54bcc0702bd23525a6952575d3278a52 | да |
| raschet-metrami | FULL_QA_PASS | d89df86e44fb5cac1cbc2b2b5b9ae1cf483c635eb95b78d65d56bdf423c9d52a | bacf5f6cfacbfaa5c16a90814fdc7e1ab59b1b0fa5d404c875bf44cb0dd74e74 | да |
| ispolnitelnaya-dokumentaciya | FULL_QA_PASS | 3a7f0ef027b946c06e5f8c038ef31894c39184f9b7ad3db53ee8aa67f6825e72 | 10c811a26bf0d45f3bd22fa338c03844a61d3f5495642e990421525020ecadac | да |
| akt-skrytyh-rabot | FULL_QA_PASS | ff75bfd6bbb989317747bbd1ad1b36592e30dcf2f2db00189a75a05f789c1e0b | 85836ca18e58c34e5008bd55e297ff98cbb710b67ffb2728820e434d08caab60 | да |

**11/11 отдельных QA-кандидатов — FULL_QA_PASS.** Это не приёмка production и не разрешение на замену публичных файлов.

Новый QA ZIP SHA-256: 06d8e851d8bc736fa56165dd73ef8cbd54bcc0702bd23525a6952575d3278a52

Защищённые QA-01–QA-11, ранее принятые 13 файлов, main, сайт, production, платежи и секреты не изменены. Merge/deploy и публикация не выполнялись. Контрольная точка QA-12.
