#!/bin/sh
# Что отвечает первичным источникам с этой машины.
#
# Запускается дважды одним прогоном: с раннера GitHub (зарубежный адрес) и
# по SSH с хостинга reg.ru (российский адрес). Смысл в сравнении: источник,
# закрытый на раннере и открытый на хостинге, закрыт географией, а не
# вообще. Без второй колонки «недоступен» — предположение, а не замер.
#
# Только заголовки: один HEAD на источник, ничего не скачивается и не
# разбирается. Проба отвечает на вопрос «пустит ли», а не собирает данные.

probe() {
    name=$1
    url=$2
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 -I \
        -A 'Mozilla/5.0 (compatible; marzhavbetone-probe/1.0)' \
        "$url" 2>/dev/null)
    [ -z "$code" ] && code="---"
    # Код первым: printf считает байты, и на кириллице колонки съезжают.
    # Ширина держится там, где значение фиксировано, — на коде.
    printf '%-6s  %s\n            %s\n' "$code" "$name" "$url"
}

echo "--- окружение ---"
echo "python3: $(python3 -V 2>&1 | head -1 || echo 'нет')"
echo "curl:    $(curl --version 2>/dev/null | head -1 | cut -d' ' -f1-2 || echo 'нет')"
echo "адрес:   $(curl -s -m 10 https://api.ipify.org 2>/dev/null || echo 'не определён')"

echo
echo "--- первичные источники ---"
echo "код     источник / адрес"
probe "pravo.gov.ru (SOURCE_A)"   "http://publication.pravo.gov.ru/"
probe "ЕИС закупки (SOURCE_A)"    "https://zakupki.gov.ru/epz/main/public/home.html"
probe "kad.arbitr.ru (SOURCE_B)"  "https://kad.arbitr.ru/"
probe "ras.arbitr.ru (SOURCE_B)"  "https://ras.arbitr.ru/"
probe "ЕФРСБ (SOURCE_B)"          "https://bankrot.fedresurs.ru/"
probe "Федресурс (SOURCE_B)"      "https://fedresurs.ru/"
probe "sudact.ru (SOURCE_C)"      "https://sudact.ru/"
probe "consultant.ru (SOURCE_C)"  "https://www.consultant.ru/"
