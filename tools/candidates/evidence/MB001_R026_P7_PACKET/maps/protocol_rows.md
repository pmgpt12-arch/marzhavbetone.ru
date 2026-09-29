# Карта протокола разногласий (10-protokol-raznoglasiy.docx)

Таблица `B0009 T2`: строка R1 — шапка «Редакция Заказчика / Редакция Подрядчика». Левая колонка строится `customer_edition()` из текста пункта договора (`CLAUSES`), правая — `contractor_edition()` из списка `PROTOCOL` генератора. Столбцы «совпал» сравнивают извлечённый из DOCX текст с тем, что генератор выдаёт для этой позиции сейчас.

| Строка | Пункт | Вид позиции | Генератор (правая колонка) | Левая колонка совпала | Правая колонка совпала | Пункт в 01 |
|---|---|---|---|---|---|---|
| R2 | 2.2 | новая редакция | `products-storage/build_paid_03.py:1136-1142` | да | да | B0017 |
| R3 | 2.4 | новая редакция | `products-storage/build_paid_03.py:1143-1149` | да | да | B0019 |
| R4 | 2.6 | новая редакция | `products-storage/build_paid_03.py:1150-1152` | да | да | B0034 |
| R5 | 2.7 | новая редакция | `products-storage/build_paid_03.py:1153-1162` | да | да | B0035 |
| R6 | 2.9 | редакция: пункт без последнего абзаца (without_last) | `products-storage/build_paid_03.py:1163-1163` | да | да | B0037 |
| R7 | 2.10 | новая редакция | `products-storage/build_paid_03.py:1164-1176` | да | да | B0050 |
| R8 | 2.11 | Исключить | `products-storage/build_paid_03.py:1177-1177` | да | да | B0053 |
| R9 | 2.13 | Исключить | `products-storage/build_paid_03.py:1178-1178` | да | да | B0055 |
| R10 | 3.2 | новая редакция | `products-storage/build_paid_03.py:1179-1182` | да | да | B0061 |
| R11 | 3.3 | новая редакция | `products-storage/build_paid_03.py:1183-1189` | да | да | B0062 |
| R12 | 3.4 | новая редакция | `products-storage/build_paid_03.py:1190-1196` | да | да | B0063 |
| R13 | 3.5 | новый пункт (в договоре нет) | `products-storage/build_paid_03.py:1197-1201` | да | да | в 01 нет |
| R14 | 4.1.1 | Исключить | `products-storage/build_paid_03.py:1202-1202` | да | да | B0066 |
| R15 | 4.1.7 | Исключить | `products-storage/build_paid_03.py:1203-1203` | да | да | B0072 |
| R16 | 4.1.8 | новый пункт (в договоре нет) | `products-storage/build_paid_03.py:1204-1214` | да | да | в 01 нет |
| R17 | 4.1.9 | новый пункт (в договоре нет) | `products-storage/build_paid_03.py:1215-1219` | да | да | в 01 нет |
| R18 | 4.5 | новая редакция, производная от текста пункта (CLAUSES[…]) | `products-storage/build_paid_03.py:1220-1229` | да | да | B0075 |
| R19 | 4.5.1 | Исключить | `products-storage/build_paid_03.py:1230-1230` | да | да | B0078 |
| R20 | 4.6 | новая редакция, производная от текста пункта (CLAUSES[…]) | `products-storage/build_paid_03.py:1231-1232` | да | да | B0079 |
| R21 | 4.7 | новая редакция | `products-storage/build_paid_03.py:1233-1243` | да | да | B0080 |
| R22 | 4.8 | Исключить | `products-storage/build_paid_03.py:1244-1244` | да | да | B0081 |
| R23 | 5.5 | Исключить | `products-storage/build_paid_03.py:1245-1245` | да | да | B0090 |
| R24 | 6.1 | новая редакция | `products-storage/build_paid_03.py:1246-1253` | да | да | B0094 |
| R25 | 6.2 | Исключить | `products-storage/build_paid_03.py:1254-1254` | да | да | B0095 |
| R26 | 6.3 | Исключить | `products-storage/build_paid_03.py:1255-1255` | да | да | B0096 |
| R27 | 6.4 | Исключить | `products-storage/build_paid_03.py:1256-1256` | да | да | B0100 |
| R28 | 6.8 | новая редакция | `products-storage/build_paid_03.py:1257-1266` | да | да | B0104 |
| R29 | 6.10 | Исключить | `products-storage/build_paid_03.py:1267-1267` | да | да | B0106 |
| R30 | 7.9 | новая редакция, производная от текста пункта (CLAUSES[…]) | `products-storage/build_paid_03.py:1268-1273` | да | да | B0128 |
| R31 | 7.13 | Исключить | `products-storage/build_paid_03.py:1274-1274` | да | да | B0132 |
| R32 | 8.1 | новая редакция, производная от текста пункта (CLAUSES[…]) | `products-storage/build_paid_03.py:1275-1281` | да | да | B0134 |
| R33 | 8.2 | Исключить | `products-storage/build_paid_03.py:1282-1282` | да | да | B0138 |
| R34 | 8.4 | Исключить | `products-storage/build_paid_03.py:1283-1283` | да | да | B0140 |
| R35 | 8.7 | Исключить | `products-storage/build_paid_03.py:1284-1284` | да | да | B0145 |
| R36 | 9.1 | Исключить | `products-storage/build_paid_03.py:1285-1285` | да | да | B0148 |
| R37 | 9.1.1 | Исключить | `products-storage/build_paid_03.py:1286-1286` | да | да | B0149 |
| R38 | 9.1.2 | Исключить | `products-storage/build_paid_03.py:1287-1287` | да | да | B0150 |
| R39 | 9.2 | Исключить | `products-storage/build_paid_03.py:1288-1288` | да | да | B0152 |
| R40 | 9.2.1 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0153 |
| R41 | 9.2.2 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0155 |
| R42 | 9.2.3 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0156 |
| R43 | 9.2.4 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0157 |
| R44 | 9.2.5 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0158 |
| R45 | 9.2.6 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0159 |
| R46 | 9.2.7 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0160 |
| R47 | 9.2.8 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0161 |
| R48 | 9.2.9 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0162 |
| R49 | 9.2.10 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0163 |
| R50 | 9.2.11 | Исключить | `products-storage/build_paid_03.py:1289-1289` | да | да | B0164 |
| R51 | 9.4 | Исключить | `products-storage/build_paid_03.py:1290-1290` | да | да | B0166 |
| R52 | 9.6 | новая редакция | `products-storage/build_paid_03.py:1291-1297` | да | да | B0168 |
| R53 | 9.8 | Исключить | `products-storage/build_paid_03.py:1298-1298` | да | да | B0170 |
| R54 | 10.2 | новая редакция | `products-storage/build_paid_03.py:1299-1303` | да | да | B0174 |
| R55 | 11.3 | новая редакция, производная от текста пункта (CLAUSES[…]) | `products-storage/build_paid_03.py:1304-1305` | да | да | B0178 |
| R56 | 11.6 | новая редакция | `products-storage/build_paid_03.py:1306-1311` | да | да | B0192 |
| R57 | 11.7 | Исключить | `products-storage/build_paid_03.py:1312-1312` | да | да | B0193 |
