#!/bin/bash
# ============================================================
# АВТОМАТИЧЕСКИЙ СКРИПТ НАСТРОЙКИ СЕРВЕРА ДЛЯ marzhavbetone.ru
# Запуск: sudo bash setup-server.sh
# ============================================================

set -e
DOMAIN="marzhavbetone.ru"
WWW_DOMAIN="www.marzhavbetone.ru"
WEB_ROOT="/var/www/marzhavbetone.ru"

echo "=========================================="
echo "  Настройка сервера для $DOMAIN"
echo "=========================================="

# --- ОПРЕДЕЛЯЕМ ВЕБ-СЕРВЕР ---
if command -v nginx &> /dev/null; then
    SERVER="nginx"
    echo "[✓] Обнаружен: nginx"
elif command -v apache2 &> /dev/null || command -v httpd &> /dev/null; then
    SERVER="apache"
    echo "[✓] Обнаружен: Apache"
else
    echo "[✗] Не найден ни nginx, ни Apache. Скрипт прерван."
    exit 1
fi

# --- СОЗДАЁМ ДИРЕКТОРИЮ САЙТА (если нет) ---
if [ ! -d "$WEB_ROOT" ]; then
    echo "[i] Создаю директорию $WEB_ROOT..."
    mkdir -p "$WEB_ROOT"
fi

# ============================================================
# НАСТРОЙКА NGINX
# ============================================================
if [ "$SERVER" = "nginx" ]; then

    NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"
    NGINX_ENABLED="/etc/nginx/sites-enabled/$DOMAIN"
    NGINX_DEFAULT="/etc/nginx/sites-enabled/default"

    # Бэкап текущего конфига
    if [ -f "$NGINX_CONF" ]; then
        echo "[i] Бэкап текущего конфига..."
        cp "$NGINX_CONF" "$NGINX_CONF.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    echo "[i] Создаю nginx-конфиг..."
    cat > "$NGINX_CONF" << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name marzhavbetone.ru www.marzhavbetone.ru;

    # Редирект HTTP → HTTPS
    return 301 https://marzhavbetone.ru$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name marzhavbetone.ru;

    # SSL (пути Let's Encrypt — измените если у вас другие)
    ssl_certificate     /etc/letsencrypt/live/marzhavbetone.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/marzhavbetone.ru/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers         'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Корень сайта
    root /var/www/marzhavbetone.ru;
    index index.html;
    charset utf-8;

    # Оптимизация
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;
    server_tokens   off;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # Кеширование: HTML (1 час)
    location ~* \.(html|htm)$ {
        add_header Cache-Control "public, max-age=3600, must-revalidate";
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        try_files $uri $uri/ =404;
    }

    # Кеширование: CSS, JS (1 неделя)
    location ~* \.(css|js)$ {
        add_header Cache-Control "public, max-age=604800, immutable";
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        access_log off;
        log_not_found off;
    }

    # Кеширование: изображения, шрифты (1 месяц)
    location ~* \.(jpg|jpeg|png|gif|ico|svg|webp|woff|woff2|ttf|eot)$ {
        add_header Cache-Control "public, max-age=2592000, immutable";
        access_log off;
        log_not_found off;
    }

    # Кеширование: PDF, ZIP (1 неделя)
    location ~* \.(pdf|zip|doc|docx|xls|xlsx)$ {
        add_header Cache-Control "public, max-age=604800";
        access_log off;
        log_not_found off;
    }

    # Скрытые файлы — запрет
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Основной location
    location / {
        try_files $uri $uri/ =404;
    }

    # Обработка 404
    error_page 404 /404.html;
}

# Блок для www — редирект на без www
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.marzhavbetone.ru;

    ssl_certificate     /etc/letsencrypt/live/marzhavbetone.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/marzhavbetone.ru/privkey.pem;

    return 301 https://marzhavbetone.ru$request_uri;
}
EOF

    # Активируем конфиг
    if [ ! -L "$NGINX_ENABLED" ]; then
        ln -s "$NGINX_CONF" "$NGINX_ENABLED"
    fi

    # Убираем дефолтный конфиг (если мешает)
    if [ -L "$NGINX_DEFAULT" ]; then
        rm "$NGINX_DEFAULT"
        echo "[i] Удалён дефолтный конфиг nginx"
    fi

    # Проверяем синтаксис
    echo "[i] Проверка синтаксиса nginx..."
    nginx -t

    # Перезапускаем
    echo "[i] Перезапуск nginx..."
    systemctl reload nginx || systemctl restart nginx

    echo "[✓] NGINX настроен и перезапущен"

# ============================================================
# НАСТРОЙКА APACHE
# ============================================================
else

    APACHE_DIR="/etc/apache2"
    if [ ! -d "$APACHE_DIR" ]; then
        APACHE_DIR="/etc/httpd"
    fi

    SITES_AVAIL="$APACHE_DIR/sites-available"
    SITES_ENABLED="$APACHE_DIR/sites-enabled"
    CONF_FILE="$SITES_AVAIL/$DOMAIN.conf"

    # Включаем нужные модули
    echo "[i] Включаем модули Apache..."
    a2enmod rewrite headers expires deflate ssl &> /dev/null || true

    # Бэкап
    if [ -f "$CONF_FILE" ]; then
        echo "[i] Бэкап текущего конфига..."
        cp "$CONF_FILE" "$CONF_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    echo "[i] Создаю Apache-конфиг..."
    cat > "$CONF_FILE" << 'EOF'
<VirtualHost *:80>
    ServerName marzhavbetone.ru
    ServerAlias www.marzhavbetone.ru
    DocumentRoot /var/www/marzhavbetone.ru

    # Редирект HTTP → HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://marzhavbetone.ru/$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName marzhavbetone.ru
    DocumentRoot /var/www/marzhavbetone.ru
    DirectoryIndex index.html

    # SSL
    SSLEngine on
    SSLCertificateFile     /etc/letsencrypt/live/marzhavbetone.ru/fullchain.pem
    SSLCertificateKeyFile  /etc/letsencrypt/live/marzhavbetone.ru/privkey.pem
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256

    # HSTS
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"

    # Security headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"

    # Кеширование
    <IfModule mod_expires.c>
        ExpiresActive On
        ExpiresByType text/html                "access plus 1 hour"
        ExpiresByType text/css                 "access plus 1 week"
        ExpiresByType application/javascript   "access plus 1 week"
        ExpiresByType image/jpeg               "access plus 1 month"
        ExpiresByType image/png                "access plus 1 month"
        ExpiresByType image/gif                "access plus 1 month"
        ExpiresByType image/svg+xml            "access plus 1 month"
        ExpiresByType image/webp               "access plus 1 month"
        ExpiresByType application/pdf          "access plus 1 week"
        ExpiresByType font/woff2               "access plus 1 month"
    </IfModule>

    <IfModule mod_headers.c>
        <FilesMatch "\.(html|htm)$">
            Header set Cache-Control "public, max-age=3600, must-revalidate"
        </FilesMatch>
        <FilesMatch "\.(css|js)$">
            Header set Cache-Control "public, max-age=604800, immutable"
        </FilesMatch>
        <FilesMatch "\.(jpg|jpeg|png|gif|ico|svg|webp|woff|woff2|ttf|eot)$">
            Header set Cache-Control "public, max-age=2592000, immutable"
        </FilesMatch>
        <FilesMatch "\.(pdf|zip|doc|docx|xls|xlsx)$">
            Header set Cache-Control "public, max-age=604800"
        </FilesMatch>
    </IfModule>

    # Gzip
    <IfModule mod_deflate.c>
        AddOutputFilterByType DEFLATE text/html text/plain text/css application/javascript application/json image/svg+xml
    </IfModule>

    # Rewrite
    <Directory /var/www/marzhavbetone.ru>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # www → без www
    RewriteEngine On
    RewriteCond %{HTTP_HOST} ^www\.marzhavbetone\.ru$ [NC]
    RewriteRule ^(.*)$ https://marzhavbetone.ru/$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName www.marzhavbetone.ru
    SSLEngine on
    SSLCertificateFile     /etc/letsencrypt/live/marzhavbetone.ru/fullchain.pem
    SSLCertificateKeyFile  /etc/letsencrypt/live/marzhavbetone.ru/privkey.pem
    RewriteEngine On
    RewriteRule ^(.*)$ https://marzhavbetone.ru/$1 [R=301,L]
</VirtualHost>
EOF

    # Активируем сайт
    a2ensite "$DOMAIN.conf" &> /dev/null || true

    # Убираем дефолтный
    a2dissite 000-default.conf &> /dev/null || true
    a2dissite default-ssl.conf &> /dev/null || true

    # Проверка синтаксиса
    echo "[i] Проверка синтаксиса Apache..."
    apache2ctl configtest || httpd -t

    # Перезапуск
    echo "[i] Перезапуск Apache..."
    systemctl reload apache2 || systemctl restart apache2 || systemctl restart httpd

    echo "[✓] Apache настроен и перезапущен"
fi

# ============================================================
# ПРОВЕРКА РЕЗУЛЬТАТОВ
# ============================================================
echo ""
echo "=========================================="
echo "  ПРОВЕРКА РЕЗУЛЬТАТОВ"
echo "=========================================="

# Проверяем, что сервер слушает
if command -v ss &> /dev/null; then
    ss -tlnp | grep -E ':80|:443' || echo "[i] Порты 80/443 не видны локально (нормально, если за прокси)"
fi

# Проверяем заголовки (если curl доступен)
if command -v curl &> /dev/null; then
    echo ""
    echo "[i] Проверка заголовков (localhost)..."
    curl -s -I -k https://localhost/ 2>/dev/null | grep -E "HTTP|Location|Strict-Transport-Security|Cache-Control" || echo "[i] Локальная проверка недоступна (нужен SSL на localhost)"
fi

echo ""
echo "=========================================="
echo "  НАСТРОЙКА ЗАВЕРШЕНА!"
echo "=========================================="
echo ""
echo "Проверьте в браузере/через curl:"
echo "  curl -I http://$DOMAIN"
echo "  curl -I https://www.$DOMAIN"
echo ""
echo "Ожидаемый результат: 301 → https://$DOMAIN"
echo ""
echo "Проверьте заголовки:"
echo "  curl -I https://$DOMAIN"
echo "  Должны быть: Strict-Transport-Security, Cache-Control"
echo ""
echo "Если SSL-сертификаты по другому пути — отредактируйте:"
if [ "$SERVER" = "nginx" ]; then
    echo "  $NGINX_CONF"
else
    echo "  $CONF_FILE"
fi
