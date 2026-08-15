# Разбор страниц товаров — 15.08.2026

Собран `tools/product_page_audit.py`. Блоки ищутся по смыслу:
заголовком, служебным классом или характерной конструкцией —
дословного H2 не требуется, как и оговорено в задании.

**Чего этот разбор не делает:** он не оценивает качество текста.
Ответ на вопрос «есть ли на странице ответ покупателю» —
машинный; «хорош ли ответ» — работа человека, и подменять её
счётом блоков нельзя.

Итог: страниц 18 — GOOD 0, MINOR FIX 18, MAJOR FIX 0.

| страница | статус | чего не найдено |
|---|---|---|
| `p1-oplata-po-ks2.html` | **MINOR FIX** | WHEN |
| `p10-otvet-na-pretenziyu.html` | **MINOR FIX** | WHO, WHEN |
| `p11-raschet-metrami.html` | **MINOR FIX** | WHO, WHEN |
| `p12-spor-s-summoy.html` | **MINOR FIX** | WHO |
| `p13-chto-v-smete-ne-oplatyat.html` | **MINOR FIX** | RESULT, WHO, WHEN |
| `p2-dopolnitelnye-raboty.html` | **MINOR FIX** | WHO, WHEN |
| `p3-shablony-ks2-ks3.html` | **MINOR FIX** | RESULT, WHO, WHEN |
| `p4-ispolnitelnaya-dokumentaciya-pto.html` | **MINOR FIX** | WHO, WHEN |
| `p5-shtrafy-uderzhaniya.html` | **MINOR FIX** | WHO, WHEN |
| `p7-dogovor-podryada.html` | **MINOR FIX** | RESULT, WHO, WHEN, MECHANISM |
| `p8-avans-po-dogovoru-subpodryada.html` | **MINOR FIX** | WHO, WHEN |
| `p9-bankrotstvo-genpodryadchika.html` | **MINOR FIX** | WHO, WHEN |
| `t1-pervyy-shag-pri-neoplate.html` | **MINOR FIX** | WHO, WHEN |
| `t2-peredacha-ispolnitelnoy-dokumentacii.html` | **MINOR FIX** | RESULT, WHO, WHEN |
| `t3-odnostoronniy-akt-i-zachet.html` | **MINOR FIX** | RESULT, WHO, WHEN |
| `t4-genpodryadchik-bankrotitsya.html` | **MINOR FIX** | WHEN |
| `t5-trebuyut-vernut-avans.html` | **MINOR FIX** | WHO |
| `t6-kvartiry-vmesto-deneg.html` | **MINOR FIX** | WHO, WHEN |

## Как читать пропуски

`WHY DOCS`, `FREE ENTRY` и `RELATED ARTICLE` объявлены
необязательными: у входной ступени за 990 ₽ отдельный разбор
каждого файла избыточен, а бесплатный вход есть не у каждой
боли. Их отсутствие в таблице не показано.

`MAJOR FIX` ставится только когда нет цены, кнопки или
состава — то есть когда покупать буквально нечем.
