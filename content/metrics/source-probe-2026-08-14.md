# Проба первичных источников

Дата: 2026-08-14. Прогон: source-probe.yml.

Каждая строка — код ответа на один HEAD-запрос. Проба
отвечает на вопрос «пустит ли», а не собирает данные.

## С раннера GitHub (зарубежный адрес)

```
--- окружение ---
python3: Python 3.12.3
curl:    curl 8.5.0
адрес:   172.172.237.216

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
000     ЕФРСБ (SOURCE_B)
            https://bankrot.fedresurs.ru/
000     Федресурс (SOURCE_B)
            https://fedresurs.ru/
200     sudact.ru (SOURCE_C)
            https://sudact.ru/
200     consultant.ru (SOURCE_C)
            https://www.consultant.ru/
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
```
