#!/bin/bash
# ============================================================
# СКРИПТ ПРОВЕРКИ НАСТРОЕК СЕРВЕРА marzhavbetone.ru
# Запуск: bash check-server.sh
# ============================================================

DOMAIN="marzhavbetone.ru"
WWW="www.marzhavbetone.ru"
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

echo "=========================================="
echo "  Проверка настроек $DOMAIN"
echo "=========================================="
echo ""

# Проверяем, есть ли curl
if ! command -v curl &> /dev/null; then
    echo "Установите curl: sudo apt install curl"
    exit 1
fi

check_redirect() {
    local url=$1
    local expected=$2
    local desc=$3

    echo -n "[$desc] $url → "
    RESULT=$(curl -s -I -L --max-redirs 1 "$url" 2>/dev/null | head -20)
    HTTP_CODE=$(echo "$RESULT" | grep -i "^HTTP" | tail -1 | awk '{print $2}')
    FINAL_URL=$(echo "$RESULT" | grep -i "^Location:" | tail -1 | sed 's/Location: //i' | tr -d '\r')

    if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "308" ]; then
        if echo "$FINAL_URL" | grep -q "$expected"; then
            echo -e "${GREEN}OK${NC} (301 → $FINAL_URL)"
            return 0
        else
            echo -e "${RED}ОШИБКА${NC} (301 → $FINAL_URL, ожидалось $expected)"
            return 1
        fi
    elif [ "$HTTP_CODE" = "200" ]; then
        if echo "$FINAL_URL" | grep -q "$expected" || [ "$url" = "https://$expected/" ]; then
            echo -e "${GREEN}OK${NC} (200, корректная версия)"
            return 0
        else
            echo -e "${YELLOW}ВНИМАНИЕ${NC} (200 без редиректа — возможно дубль)"
            return 1
        fi
    else
        echo -e "${RED}ОШИБКА${NC} (HTTP $HTTP_CODE)"
        return 1
    fi
}

check_header() {
    local url=$1
    local header=$2
    local desc=$3

    echo -n "[$desc] $header → "
    RESULT=$(curl -s -I -k "$url" 2>/dev/null)
    VALUE=$(echo "$RESULT" | grep -i "^$header:" | sed "s/$header: //i" | tr -d '\r')

    if [ -n "$VALUE" ]; then
        echo -e "${GREEN}OK${NC} ($VALUE)"
        return 0
    else
        echo -e "${RED}ОТСУТСТВУЕТ${NC}"
        return 1
    fi
}

# --- ПРОВЕРКА 1: Редиректы ---
echo "--- 1. ПРОВЕРКА РЕДИРЕКТОВ ---"
ERRORS=0
check_redirect "http://$DOMAIN/" "marzhavbetone.ru" "http→https" || ((ERRORS++))
check_redirect "http://$WWW/" "marzhavbetone.ru" "www.http→https" || ((ERRORS++))
check_redirect "https://$WWW/" "marzhavbetone.ru" "www→без www" || ((ERRORS++))

# Проверяем финальную версию
FINAL=$(curl -s -I -k "https://$DOMAIN/" 2>/dev/null | head -1 | awk '{print $2}')
if [ "$FINAL" = "200" ]; then
    echo -e "[https без www] → ${GREEN}OK${NC} (200)"
else
    echo -e "[https без www] → ${RED}ОШИБКА${NC} (HTTP $FINAL)"
    ((ERRORS++))
fi

# --- ПРОВЕРКА 2: Заголовки ---
echo ""
echo "--- 2. ПРОВЕРКА ЗАГОЛОВКОВ ---"
check_header "https://$DOMAIN/" "Strict-Transport-Security" "HSTS" || ((ERRORS++))
check_header "https://$DOMAIN/" "X-Content-Type-Options" "X-Content-Type-Options" || ((ERRORS++))
check_header "https://$DOMAIN/" "X-Frame-Options" "X-Frame-Options" || ((ERRORS++))

# Проверяем Cache-Control для разных типов файлов
echo ""
echo "--- 3. ПРОВЕРКА КЕШИРОВАНИЯ ---"
check_header "https://$DOMAIN/" "Cache-Control" "HTML Cache-Control"
check_header "https://$DOMAIN/styles.css" "Cache-Control" "CSS Cache-Control"

# --- ПРОВЕРКА 3: TTFB ---
echo ""
echo "--- 4. ПРОВЕРКА TTFB (время ответа) ---"
TTFB=$(curl -s -o /dev/null -w "%{time_starttransfer}" -k "https://$DOMAIN/" 2>/dev/null)
TTFB_MS=$(echo "$TTFB * 1000" | bc -l 2>/dev/null || echo "0")
TTFB_INT=$(printf "%.0f" "$TTFB_MS" 2>/dev/null || echo "0")

if [ "$TTFB_INT" -lt 200 ] && [ "$TTFB_INT" -gt 0 ]; then
    echo -e "TTFB: ${GREEN}${TTFB_INT} мс${NC} (отлично)"
elif [ "$TTFB_INT" -lt 500 ] && [ "$TTFB_INT" -gt 0 ]; then
    echo -e "TTFB: ${YELLOW}${TTFB_INT} мс${NC} (нормально)"
elif [ "$TTFB_INT" -gt 0 ]; then
    echo -e "TTFB: ${RED}${TTFB_INT} мс${NC} (медленно, должно быть <200 мс)"
else
    echo "TTFB: не удалось измерить (возможно, нужен bc: sudo apt install bc)"
fi

# --- ИТОГ ---
echo ""
echo "=========================================="
if [ "$ERRORS" -eq 0 ]; then
    echo -e "  ${GREEN}ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!${NC}"
else
    echo -e "  ${RED}НАЙДЕНО ПРОБЛЕМ: $ERRORS${NC}"
fi
echo "=========================================="
echo ""
echo "Дополнительная проверка онлайн:"
echo "  https://www.redirect-checker.org/"
echo "  https://httpstatus.io/"
echo "  https://pagespeed.web.dev/"
