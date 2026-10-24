# НСП — QA-13: P1 Закрытие работ и получение оплаты

**Итог: BLOCKED, FULL_QA_PASS не присвоен.**

Диагностический ZIP QA01 SHA: c50e647720eb8315daac355e8d3bd7b3b92167ec232e5fc05ac98e0b47bb298e
20-файловый QA-кандидат SHA: 143c4c111422899eefed73a8cd8995480d666ef1325b52b3e91412fed7402c46

## Матрица

| Имя | Статус | SHA-256 |
|---|---|---|
| 09-checklist-peredachi.pdf | UNCHANGED_ACCEPTED | 6576b0be65d30bbd9100008c40852cc7efe97d1280adfecafce7181f5ca8196c |
| 06-zhurnal-ucheta-rabot-ks-6a.xls | BLOCKED | 053c5f1603478ca08fbab8f522ed4448546941d4009c79a76bdc8af13248aa29 |
| 15-algoritm-pri-zaderzhke-oplaty.docx | PASS | 631f7188a431ddafe97fb93f1f3536d0339cb36a9b3caa14e93b4113e59354f0 |
| 16-iskovoe-zayavlenie-o-vzyskanii.docx | PASS | 2bafc0a6f3bb76cbb7147dbb03b67968e48aa3318a2b0f692fa4d37857d384de |
| 06A-rabochiy-reestr-obemov.xlsx | UNCHANGED_ACCEPTED | a2cafa2bddf6304ac3d0153756ca6da1e1d1cd6711949d2c704654bb506c18e4 |
| 11-slovar-poley.docx | PASS | fed6ac374269f86cad3d1a19cbf8262aa7250ec60082328dc889138cb60c20d3 |
| 07-reestr-zamechaniy.xlsx | UNCHANGED_ACCEPTED | fdd9d8d8015f348086fabaa2bd7dfd136febb6eb2ab6408630b0bda611a41a56 |
| 12-pretenziya-na-neoplatu-po-ks-2.docx | PASS | 4c8d8faed3faec5fbdd9e3e585c00d8093009bb1aeb7efe1a8dbf8a3949f2bd4 |
| 10-sroki-hraneniya.pdf | UNCHANGED_ACCEPTED | a066b06560ba8edad1df48b38332133d9b7946a0ebdb1d5e8dcebf321e01f1ee |
| 03-akt-vypolnennyh-rabot.docx | UNCHANGED_ACCEPTED | bf3d055ccc050d5f0e1c1b1f09963d436aed7fc81647d63a1d0285e3f3e8cbfe |
| 08-reestr-peredachi.xlsx | UNCHANGED_ACCEPTED | 06225667155164df3323f8d1ab995a806fcdf17d4ebfb387f45375de5e626495 |
| 14-raschet-procentov-395-gk.xlsx | BLOCKED | a72d10f958b3b6e303683bcd0c2c58693f43216b53714fec2da953f7855a07ba |
| 04-akt-priemki.docx | UNCHANGED_ACCEPTED | bc7e68833b07223558e0cae648bf9f82c65cb590c48f104b935d1537cf15637e |
| 05-peredatochnyy-akt.docx | UNCHANGED_ACCEPTED | 226a92dc69184f169ef1bc8897c53ab30e6b2eeca4a6aa11f44fc76d8a884be1 |
| 01-ks-2.xls | BLOCKED | b09296147561df5afd9a38bbb196860a1a3a3268a8b26d9751c88d4c5bca6281 |
| 13-uvedomlenie-o-prosrochke-oplaty.docx | PASS | fc95ef591711ebc59283bb1688e68c1e01cbc305e1aac23883464ab589c5d44d |
| 00-START-HERE.txt | PASS | 7bd902738a0652b314f224e1597dc972e7c842d951afacdf7759b371e3e919f7 |
| 00-INSTRUKCIYA.docx | PASS | cd6e8ed22ed32e734152b350fca9782bf15684379a9883618ac8ade0c18207c2 |
| 00-INSTRUKCIYA.pdf | PASS | 39ac37a8f7607cb5a1dbb12951ba2ef2698df5affff4b7b220d6e8ac8d17524d |
| 02-ks-3.xls | BLOCKED | d6922089bffcde2a00a30d62d8d7ea1d87676fe4de9ae44a3d0e9af4d821ed0a |

## Исправления и проверки

Кейс: предъявлено 32 млн ₽, подтверждено поступлений 26,9 млн ₽, арифметическая разница 5,1 млн ₽. Реальность долга, срок оплаты, приёмка и зачёты должны подтверждаться отдельно.
Изменённые документы отражают различие основного долга, ст. 395 ГК РФ, договорной неустойки, убытков, судебного приказа и искового производства, неподписанные акты.
В калькуляторе проверены изменения ставки, частичные оплаты, годовой переход и високосные годы, недопустимый ввод и оплаты за пределами периода. Нативные квитанции со статусом PASS/FAIL указаны в evidence.

## Невыполненные условия

1. Активная функция сборки HEAD выдаёт 19 файлов с DOCX формами КС, а проверенный диагностический ZIP QA01 — 20 файлов с исходными XLS формами. Выпускной состав не соответствует конфигурации.
2. Три подлинных XLS не получили достаточного подтверждения нативного открытия через существующий агент, который принимает только XLSX.
3. Нет единой подтверждённой приёмки именно штатной P1 выдачи из 20 файлов; визуальный контроль полного пакета не завершён.

Нет merge, deploy, изменений main, production, сайта, публичных ZIP, секретов или других утверждённых продуктов. QA14 не запускать.
