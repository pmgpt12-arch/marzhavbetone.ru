# НСП — QA-09. Чек-лист закрытия выполненных работ

**FULL_QA_PASS для отдельного PDF-кандидата. Публикация запрещена.**

## Проверка PDF
Публичный исходник: 65ec8f7880adc4bf9d611888bf16f332415bc7b6da97fcf577fd29e38dba42c4
Git-исходник: 5802003496faac7ecbbf2c359829f8a542e4f71f4d6c9a731460dd6b29b13f74
Конечный кандидат: bd50ad14084fbf91f2c575718e9d5f66c533ee5d1fd5dfc34eeaae2c34455394

Microsoft Word 2016 PASS; 2 страницы; обе визуально проверены. Кириллица и отметки «Д/Н/НП» читаемы; поля для основания, ответственного и срока имеются.

20 исходных контрольных пунктов преобразованы в 18 более предметных проверок; сохранены четыре блока: договор, фактическое выполнение/ИД, приёмка, оплата.

Фиксация отправки, доставки, приёмки и срока оплаты отделена; универсальный запрет на оплату при отсутствии подписи исключён. Добавлен пример и журнал из четырёх строк.

Нормативные основания: ст. 309, 314, 720, 746, 753 ГК РФ, ст. 52–53 ГрК РФ, приказ Минстроя № 344/пр в действующей редакции (в том числе изменения № 369/пр с 01.03.2026).

Ссылка PDF на каталог проверена; пустых страниц и обрезаний нет.

## Матрица 11 бесплатных выдач — read-only

| Материал | QA статус | Публичный SHA-256 | Принятый кандидат SHA-256 | Git отличается |
|---|---|---|---|---|
| checklist | FULL_QA_PASS | 65ec8f7880adc4bf9d611888bf16f332415bc7b6da97fcf577fd29e38dba42c4 | bd50ad14084fbf91f2c575718e9d5f66c533ee5d1fd5dfc34eeaae2c34455394 | да |
| dengi | FULL_QA_PASS | f8166b4c029df501d53ea3b3b7d57b17e15a1ffbbc8d20f315b3333a19e9cc33 | 024fe485d70bf2e55775ad3d1aae45bccc2ebd94502a26f4f938366e551d9ff1 | да |
| dop-raboty | READY_CANDIDATE | 66544cb03c67218a988db0413de339ca48abf36af93f02d9a842d014b8991157 | 6149e4409c7a1c8033dd08ce8bbc91a76c6ed3ca958a375e24178b6604e7d8ec | да |
| vozvrat-ks | READY_CANDIDATE | c1cb90e49e4bca59d236782da15ff2d92b6738c2fcb5c5702509d835a3fa3ad4 | d9585b46988ef4320ddf455e3ea6418f8dfd502e991cf4291b196ffceff5f67a | да |
| uderzhaniya | FULL_QA_PASS | 07f372b8cd43b3a6a31f20834290e99ac25a2012ed91472ec01cd12004281122 | 77ef9381b960176e152bee757e3d497e9c8bcaecc20bbeb96ed6b1f5de99e1e0 | да |
| dogovor | FULL_QA_PASS | be4df3d43d23361ac9c8c200ffce5839c862cb078a91d949aae5da46735efa9a | b9a3fd2bb0e9477aef799c0a44e555a77aac281a6176d422a2f38bcc1d181f30 | да |
| bankrotstvo | FULL_QA_PASS | 0de62a32042330fba008dfcd7ac61dbbe43eba9ab7b9dff24f752c498a47edfa | 68a1d82c16fb3c141dfa4778fc96ac03f2a058eafea5fd287103c0103903b393 | да |
| avans | READY_CANDIDATE | 7e87570bbd42da3326823261a842e6544c5b7588bc3487633e70e3d5c9b6999b | 5430fc6ea7781fadf586e7c601436ff6f10bd3a927b263358069b3c66cd35c16 | да |
| raschet-metrami | FULL_QA_PASS | d89df86e44fb5cac1cbc2b2b5b9ae1cf483c635eb95b78d65d56bdf423c9d52a | bacf5f6cfacbfaa5c16a90814fdc7e1ab59b1b0fa5d404c875bf44cb0dd74e74 | да |
| ispolnitelnaya-dokumentaciya | FULL_QA_PASS | 3a7f0ef027b946c06e5f8c038ef31894c39184f9b7ad3db53ee8aa67f6825e72 | 10c811a26bf0d45f3bd22fa338c03844a61d3f5495642e990421525020ecadac | да |
| akt-skrytyh-rabot | FULL_QA_PASS | ff75bfd6bbb989317747bbd1ad1b36592e30dcf2f2db00189a75a05f789c1e0b | 85836ca18e58c34e5008bd55e297ff98cbb710b67ffb2728820e434d08caab60 | да |

**Итого: 8 FULL_QA_PASS, 3 READY_CANDIDATE.** READY_CANDIDATE для avans, dop-raboty и vozvrat-ks — не выпускной FULL PASS; отдельную приёмку в QA-09 не повторяли.

Публикация 11 материалов заблокирована до решения руководящей сессии. Main, PR #676, production, платные файлы и QA-01–QA-08 не изменены. К платным продуктам не переходить.
