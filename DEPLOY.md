# Автодеплой на сервер

Каждый push в ветку `main` автоматически выкладывает сайт на сервер
(workflow `.github/workflows/deploy.yml`). Пока секреты не настроены,
workflow ничего не делает и завершается успешно.

## Разовая настройка (10 минут)

### 1. Создайте SSH-ключ для деплоя (на своём ПК)

```bash
ssh-keygen -t ed25519 -f deploy_key -N "" -C "github-deploy-marzhavbetone"
```

Появятся два файла: `deploy_key` (секретный) и `deploy_key.pub` (публичный).

### 2. Разрешите этому ключу вход на сервер

Подключитесь к серверу как обычно и добавьте содержимое `deploy_key.pub`
в файл `~/.ssh/authorized_keys` того пользователя, от имени которого
будет идти деплой (пользователь должен иметь право записи в
`/var/www/marzhavbetone.ru` и `/var/www/marzhavbetone-products`):

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys   # вставьте строку из deploy_key.pub, Ctrl+D
chmod 600 ~/.ssh/authorized_keys
```

### 3. Добавьте секреты в GitHub

Репозиторий → **Settings → Secrets and variables → Actions → New repository secret**:

| Секрет | Значение |
|---|---|
| `DEPLOY_HOST` | IP или домен сервера, например `marzhavbetone.ru` |
| `DEPLOY_USER` | SSH-пользователь, например `root` или `deploy` |
| `DEPLOY_SSH_KEY` | Полное содержимое файла `deploy_key` (секретного, начинается с `-----BEGIN OPENSSH PRIVATE KEY-----`) |
| `DEPLOY_PORT` | Порт SSH — только если не 22 |

После этого удалите файл `deploy_key` со своего ПК — он больше не нужен.

### 4. Однократно поправьте `config.php` на сервере

Файлы продуктов деплоятся в `/var/www/marzhavbetone-products/` — вне
webroot, чтобы их нельзя было скачать напрямую. Добавьте в серверный
`config.php` (он деплоем не перезаписывается) строку:

```php
define('PRODUCTS_DIR', '/var/www/marzhavbetone-products');
```

### 5. Проверьте

Запустите workflow вручную: **Actions → Deploy to server → Run workflow** —
или сделайте любой push в `main`. В логе будет проверка: сайт должен
ответить `HTTP 200`.

## Что деплой никогда не трогает на сервере

- `config.php` — боевые ключи ЮКассы остаются на сервере;
- `orders/` — данные заказов и ссылки выдачи;
- серверные конфиги (`nginx-marzhavbetone.conf`, скрипты установки).

## Как это связано с контент-фабрикой

Когда автодеплой работает, публикация статьи — это просто коммит в `main`:
фабрика генерирует HTML статьи, добавляет её в `articles/`, обновляет
`sitemap.xml` — и через минуту она на сайте. Ручных действий нет.
