# Проба первичных источников

Дата: 2026-08-14. Прогон: source-probe.yml.

Каждая строка — код ответа на один запрос. Проба
отвечает на вопрос «пустит ли», а не собирает данные.

## С раннера GitHub (зарубежный адрес)

```
--- окружение ---
python3: Python 3.12.3
curl:    curl 8.5.0
адрес:   68.220.58.242

--- первичные источники ---
код     источник / адрес
405     pravo.gov.ru (SOURCE_A)
            http://publication.pravo.gov.ru/
000     ЕИС закупки (SOURCE_A)
            https://zakupki.gov.ru/epz/main/public/home.html
200     kad.arbitr.ru (SOURCE_B)
            https://kad.arbitr.ru/
200     ras.arbitr.ru (SOURCE_B)
            https://ras.arbitr.ru/
200     ЕФРСБ (SOURCE_B)
            https://bankrot.fedresurs.ru/
000     Федресурс (SOURCE_B)
            https://fedresurs.ru/
200     sudact.ru (SOURCE_C)
            https://sudact.ru/
200     consultant.ru (SOURCE_C)
            https://www.consultant.ru/

--- один поисковый запрос ---
код     что запрошено
200     ras.arbitr.ru GET главной, тело 137999 байт
451     kad.arbitr.ru поиск, тело 1715 байт
403     ras.arbitr.ru ПОИСК (POST), тело 1985 байт
200     sudact.ru поиск по тексту, тело 82373 байт
200     publication.pravo.gov.ru GET (на HEAD было 405)
```

## С хостинга reg.ru (российский адрес)

```
--- окружение ---
python3: Python 3.6.8
curl:    curl 7.61.1
адрес:   37.140.192.133

--- первичные источники ---
код     источник / адрес
405     pravo.gov.ru (SOURCE_A)
            http://publication.pravo.gov.ru/
200     ЕИС закупки (SOURCE_A)
            https://zakupki.gov.ru/epz/main/public/home.html
200     kad.arbitr.ru (SOURCE_B)
            https://kad.arbitr.ru/
200     ras.arbitr.ru (SOURCE_B)
            https://ras.arbitr.ru/
200     ЕФРСБ (SOURCE_B)
            https://bankrot.fedresurs.ru/
200     Федресурс (SOURCE_B)
            https://fedresurs.ru/
200     sudact.ru (SOURCE_C)
            https://sudact.ru/
200     consultant.ru (SOURCE_C)
            https://www.consultant.ru/

--- один поисковый запрос ---
код     что запрошено
200     ras.arbitr.ru GET главной, тело 137999 байт
451     kad.arbitr.ru поиск, тело 1715 байт
403     ras.arbitr.ru ПОИСК (POST), тело 1985 байт
200     sudact.ru поиск по тексту, тело 82373 байт
200     publication.pravo.gov.ru GET (на HEAD было 405)
```

## Замер запросом: окончательно

| запрос | код | тело |
|---|---|---|
| `kad.arbitr.ru` поиск | 451 | 1 715 байт |
| `ras.arbitr.ru` ПОИСК (POST) | 403 | 1 985 байт |
| `ras.arbitr.ru` главная (GET) | 200 | 137 999 байт |
| `sudact.ru` поиск по тексту | 200 | 82 373 байт |
| `publication.pravo.gov.ru` (GET) | 200 | — |

Коды одинаковы с раннера GitHub и с хостинга reg.ru.

**Оба официальных банка судебных актов закрыты для программных
запросов.** Картотека отвечает 451, банк решений — 403 на поиск при 200
на главной. Одинаковость кодов с двух адресов снимает версию про
географию: дело не в том, откуда запрос, а в том, что он программный.

Отсюда прямое следствие для пилота: **выборку нельзя построить на
SOURCE_B автоматически**. Тексты актов доступны через `sudact.ru` —
класс C по нашей же иерархии, — и это ограничение исследования, а не
деталь реализации.

Что остаётся возможным:
- сбор выборки с `sudact.ru` (класс C), с сохранением номеров дел;
- выборочная сверка номеров с официальным источником руками, браузером —
  автоматически она закрыта тем же 451/403;
- нормы (`publication.pravo.gov.ru`, класс A) доступны GET-запросом.

Что закрыто: ЕИС и Федресурс доступны только с российского адреса, то
есть с хостинга сайта. К пилоту про дополнительные работы они отношения
не имеют.
