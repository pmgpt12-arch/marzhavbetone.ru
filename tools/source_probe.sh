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

# --- Запрос, а не главная -------------------------------------------------
#
# Код 200 на главной не означает, что работает поиск по делам: защита от
# автоматических запросов срабатывает на запросе, а не на входе. Режим
# включается аргументом, чтобы обычная проба оставалась одним HEAD.
#
# Запрос ровно один и без разбора ответа: меряется пригодность источника,
# а не собираются данные. Вопрос выборки объявлен в
# research/dopolnitelnye-raboty.yaml и здесь не решается.
if [ "$1" = "--query" ]; then
    echo
    echo "--- один поисковый запрос ---"
    echo "код     что запрошено"

    # Банк решений арбитражных судов: поиск по тексту.
    code=$(curl -s -o /tmp/ras.out -w '%{http_code}' -m 30 \
        -A 'Mozilla/5.0 (compatible; marzhavbetone-probe/1.0)' \
        'https://ras.arbitr.ru/' 2>/dev/null)
    size=$([ -f /tmp/ras.out ] && wc -c < /tmp/ras.out || echo 0)
    printf '%-6s  ras.arbitr.ru GET главной, тело %s байт\n' "$code" "$size"

    # Картотека: карточка поиска. Ответ не разбирается, важен код и размер.
    code=$(curl -s -o /tmp/kad.out -w '%{http_code}' -m 30 \
        -A 'Mozilla/5.0 (compatible; marzhavbetone-probe/1.0)' \
        -H 'Accept: text/html' \
        'https://kad.arbitr.ru/Kad/SearchInstances' 2>/dev/null)
    size=$([ -f /tmp/kad.out ] && wc -c < /tmp/kad.out || echo 0)
    printf '%-6s  kad.arbitr.ru поиск, тело %s байт\n' "$code" "$size"

    # Вторичный источник с открытым поиском — запасной путь, класс C.
    code=$(curl -s -o /tmp/sud.out -w '%{http_code}' -m 30 \
        -A 'Mozilla/5.0 (compatible; marzhavbetone-probe/1.0)' \
        'https://sudact.ru/arbitral/?arbitral-txt=дополнительные+работы+подряд' \
        2>/dev/null)
    size=$([ -f /tmp/sud.out ] && wc -c < /tmp/sud.out || echo 0)
    printf '%-6s  sudact.ru поиск по тексту, тело %s байт\n' "$code" "$size"

    # Официальное опубликование: тот же адрес, но GET вместо HEAD — 405
    # на HEAD означает метод, а не блокировку, и это надо показать.
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 30 \
        -A 'Mozilla/5.0 (compatible; marzhavbetone-probe/1.0)' \
        'http://publication.pravo.gov.ru/' 2>/dev/null)
    printf '%-6s  publication.pravo.gov.ru GET (на HEAD было 405)\n' "$code"
fi
