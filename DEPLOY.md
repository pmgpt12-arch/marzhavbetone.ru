# Автодеплой на хостинг reg.ru

Каждый push в ветку `main` автоматически выкладывает сайт на хостинг
(workflow `.github/workflows/deploy.yml`). Пока секреты не настроены,
workflow ничего не делает и завершается успешно.

Хостинг: виртуальный хостинг reg.ru с ISPmanager.

- Сервер: `server116.hosting.reg.ru`
- Пользователь: `u3581543`
- Сайт: `~/www/marzhavbetone.ru` (= `/var/www/u3581543/data/www/marzhavbetone.ru`)
- Файлы продуктов: `~/products-marzhavbetone` — вне webroot, напрямую из
  браузера недоступны; выдачу покупателям делает `download.php`

## Разовая настройка

### 1. Ключ для деплоя (на своём ПК, PowerShell)

```powershell
cd $HOME
ssh-keygen -t ed25519 -f deploy_key
```

На вопросы о passphrase — просто Enter (дважды). Появятся файлы
`deploy_key` (секретный) и `deploy_key.pub` (публичный).

### 2. Разрешить ключу вход на хостинг

Откройте `deploy_key.pub` (PowerShell: `notepad $HOME\deploy_key.pub`) и
скопируйте всю строку `ssh-ed25519 AAAA...`.

В ISPmanager откройте **Shell-клиент** (левое меню) и выполните одну
команду, подставив свою строку внутрь кавычек:

```bash
mkdir -p ~/.ssh && echo 'ssh-ed25519 AAAA...ваша_строка...' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

Проверка с ПК (PowerShell):

```powershell
ssh -i $HOME\deploy_key u3581543@server116.hosting.reg.ru "echo OK"
```

Ответ `OK` без запроса пароля = ключ работает. Если SSH-доступ выключен —
включите его в кабинете reg.ru: карточка хостинга → вкладка «Доступы».

### 3. Секреты в GitHub

Репозиторий → Settings → Secrets and variables → Actions → New repository secret:

| Секрет | Значение |
|---|---|
| `DEPLOY_HOST` | `server116.hosting.reg.ru` |
| `DEPLOY_USER` | `u3581543` |
| `DEPLOY_SSH_KEY` | Полное содержимое файла `deploy_key` (`notepad $HOME\deploy_key`, скопировать всё) |

Необязательные (нужны только если пути отличаются): `DEPLOY_PORT`,
`DEPLOY_PATH` (по умолчанию `www/marzhavbetone.ru`),
`DEPLOY_PRODUCTS_PATH` (по умолчанию `products-marzhavbetone`).

После добавления секретов удалите `deploy_key` с ПК:
`del $HOME\deploy_key; del $HOME\deploy_key.pub`

### 4. Однократно поправьте config.php на хостинге

ISPmanager → Менеджер файлов → `www/marzhavbetone.ru/config.php` →
Изменить. Добавьте в конец файла строку:

```php
define('PRODUCTS_DIR', '/var/www/u3581543/data/products-marzhavbetone');
```

Там же проверьте боевые `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` и
`YOOKASSA_MODE` = `live`. Деплой этот файл никогда не перезаписывает.

### 5. Проверка

GitHub → Actions → «Deploy to server» → Run workflow. Все шаги должны
стать зелёными; последний шаг проверяет, что сайт отвечает `HTTP 200`.

## Что деплой никогда не трогает на хостинге

- `config.php` — боевые ключи ЮКассы;
- `orders/` — данные заказов и ссылки выдачи;
- всё вне папок `www/marzhavbetone.ru` и `products-marzhavbetone`.

## Как это связано с контент-фабрикой

Когда автодеплой работает, публикация статьи — это просто коммит в `main`:
фабрика генерирует HTML статьи, добавляет её в `articles/`, обновляет
`sitemap.xml` — и через минуту она на сайте. Ручных действий нет.
