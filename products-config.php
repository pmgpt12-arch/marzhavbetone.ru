<?php
/**
 * Каталог продуктов: серверная валидация цен и автовыдача после оплаты.
 *
 * PRODUCTS_DIR — папка с исходными файлами продуктов. По умолчанию
 * products-storage/ рядом с сайтом; на боевом сервере рекомендуется
 * вынести её за пределы webroot и переопределить константу в config.php.
 */
declare(strict_types=1);

// Файл подключается из payment.php / webhook.php / download.php и не должен
// открываться напрямую: без config.php он падал бы с ошибкой, раскрывающей
// путь на сервере.
if (!defined('ORDERS_DIR')) {
    http_response_code(404);
    exit;
}

if (!defined('PRODUCTS_DIR')) {
    define('PRODUCTS_DIR', __DIR__ . '/products-storage');
}
if (!defined('DELIVERY_DIR')) {
    define('DELIVERY_DIR', ORDERS_DIR . '/delivery');
}
// Срок жизни ссылки на скачивание (обещание из письма покупателю — 30 дней)
if (!defined('DELIVERY_TTL_DAYS')) {
    define('DELIVERY_TTL_DAYS', 30);
}
if (!defined('DELIVERY_MAX_DOWNLOADS')) {
    define('DELIVERY_MAX_DOWNLOADS', 30);
}

// Папки заказов и выдачи не должны читаться напрямую через веб.
// Для Apache кладём deny-файлы; для nginx нужен location-запрет (см. README).
foreach ([ORDERS_DIR, DELIVERY_DIR] as $dir) {
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $ht = $dir . '/.htaccess';
    if (!file_exists($ht)) {
        @file_put_contents($ht, "Deny from all\n");
    }
}

/**
 * Каталог: sku → название (точно как в data-product на кнопках),
 * цена в копейках, папка с файлами внутри PRODUCTS_DIR,
 * имя выдаваемого архива (по SERVER-MANIFEST.txt).
 */
function mvb_products(): array
{
    return [
        'p1' => [
            'name'  => 'Комплект «Закрытие работ: КС-2, КС-3 и акты»',
            'price' => 249000,
            'dir'   => '01-zakrytie-rabot',
            'zip'   => '01-ks-podpisany-deneg-net.zip',
        ],
        'p2' => [
            'name'  => 'Комплект «Дополнительные работы: как получить оплату»',
            'price' => 249000,
            'dir'   => '02-dopraboty-bez-poter',
            'zip'   => '02-dopy-ne-v-podarok.zip',
        ],
        'p3' => [
            'name'  => 'Комплект «КС-2 без возврата: сдайте с первой попытки»',
            'price' => 199000,
            'dir'   => '05-ks-bez-vozvrata',
            'zip'   => '05-ks-bez-vozvrata.zip',
        ],
        'p4' => [
            'name'  => 'Комплект «ПТО без замечаний: полный комплект документов»',
            'price' => 299000,
            'dir'   => '08-pto-bez-zamechaniy',
            'zip'   => '06-id-blokiruet-oplatu.zip',
        ],
        'p5' => [
            'name'  => 'Комплект «Верните штрафы и удержания: методика оспаривания»',
            'price' => 299000,
            'dir'   => '07-uderzhaniya-shtrafy-zachety',
            'zip'   => '07-uderzhaniya-shtrafy-zachety.zip',
        ],
        'p6' => [
            'name'  => 'Полный комплект «Защита маржи объекта»',
            'price' => 699000,
            'dir'   => '04-polnyy-komplekt-pto',
            'zip'   => '04-zashchita-marzhi-obekta.zip',
        ],
        // Цены приведены к решению владельца 29.07.2026: комплекты
        // 1 990–2 990 ₽, полный пакет 6 990 ₽. Обоснование от альтернатив —
        // устная консультация юриста по стройспорам 2 000–5 000 ₽,
        // библиотека шаблонов ИД у конкурента 1 800 ₽. Разбор:
        // ai-business-os/projects/marzha_v_betone/product/Market_Pricing_2026-07-29.md

        // Единственный комплект до подписания договора. P6 «Защита маржи
        // объекта» его не включает: он собран из P1–P5 и остаётся прежним.
        'p7' => [
            'name'  => 'Комплект «Договор субподряда: условия, по которым платят»',
            'price' => 249000,
            'dir'   => '03-dogovor-podryada',
            'zip'   => '03-dogovor-podryada.zip',
        ],
        // Служебная позиция за 1 ₽ для проверки всей цепочки на боевых
        // ключах: оплата → вебхук → сборка архива → письмо → скачивание.
        // В каталоге сайта не показывается, покупается только со скрытой
        // страницы /test-pokupka.html. Выдаёт бесплатный лид-магнит, так
        // что случайная покупка ничего не раскрывает.
        'test1' => [
            'name'  => 'Тестовая покупка (проверка выдачи)',
            'price' => 100,
            'dir'   => '00-free-ks-podpisany-deneg-net',
            'zip'   => 'test-pokupka.zip',
        ],
    ];
}

/** Ищет продукт по sku, затем по точному названию (для старых корзин). */
function mvb_resolve_product(array $item): ?array
{
    $catalog = mvb_products();
    $sku = (string)($item['sku'] ?? '');
    if ($sku !== '' && isset($catalog[$sku])) {
        return ['sku' => $sku] + $catalog[$sku];
    }
    $name = (string)($item['name'] ?? '');
    foreach ($catalog as $key => $product) {
        if ($product['name'] === $name) {
            return ['sku' => $key] + $product;
        }
    }
    return null;
}

/**
 * Собирает (и кэширует) архив продукта в DELIVERY_DIR.
 * Возвращает абсолютный путь к zip либо null при ошибке.
 */
function mvb_build_product_zip(string $sku): ?string
{
    $catalog = mvb_products();
    if (!isset($catalog[$sku])) {
        return null;
    }
    $sourceDir = PRODUCTS_DIR . '/' . $catalog[$sku]['dir'];
    $zipPath = DELIVERY_DIR . '/' . $catalog[$sku]['zip'];

    if (is_file($zipPath) && filesize($zipPath) > 0) {
        return $zipPath;
    }
    if (!is_dir($sourceDir)) {
        @file_put_contents(ORDERS_DIR . '/delivery-errors.log',
            date('c') . " нет папки продукта: {$sourceDir}\n", FILE_APPEND);
        return null;
    }

    $zip = new ZipArchive();
    if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
        return null;
    }
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($sourceDir, FilesystemIterator::SKIP_DOTS)
    );
    foreach ($iterator as $file) {
        if (!$file->isFile()) {
            continue;
        }
        $local = substr($file->getPathname(), strlen($sourceDir) + 1);
        // Служебные файлы не отдаём покупателю. MANIFEST.md внутренний:
        // в нём состав, ценовые гипотезы и связь с бесплатными материалами —
        // это рабочая карточка продукта, а не документ для стройки. Число
        // файлов на страницах товаров считается по этому же списку исключений.
        $skip = ['.htaccess', '00-PISMO-POSLE-POKUPKI.txt', 'MANIFEST.md'];
        if (in_array(basename($local), $skip, true)) {
            continue;
        }
        $zip->addFile($file->getPathname(), $local);
    }
    $zip->close();
    return is_file($zipPath) ? $zipPath : null;
}

/**
 * Готовит выдачу для оплаченного заказа: собирает архивы, генерирует токен,
 * дописывает блок delivery в массив заказа. Возвращает список ссылок.
 */
function mvb_prepare_delivery(array &$order): array
{
    if (empty($order['delivery']['token'])) {
        $order['delivery'] = [
            'token'      => bin2hex(random_bytes(16)),
            'created_at' => date('c'),
            'expires_at' => date('c', time() + DELIVERY_TTL_DAYS * 86400),
            'downloads'  => 0,
            'items'      => [],
        ];
    }

    $links = [];
    foreach ($order['items'] ?? [] as $item) {
        $product = mvb_resolve_product($item);
        if (!$product) {
            continue;
        }
        $zipPath = mvb_build_product_zip($product['sku']);
        if (!$zipPath) {
            continue;
        }
        $order['delivery']['items'][$product['sku']] = basename($zipPath);
        $links[] = [
            'sku'  => $product['sku'],
            'name' => $product['name'],
            'url'  => SITE_URL . '/download.php?o=' . rawurlencode($order['id'])
                . '&t=' . $order['delivery']['token']
                . '&f=' . $product['sku'],
        ];
    }
    return $links;
}

/**
 * Полный цикл выдачи для оплаченного заказа: архивы, ссылки, письмо покупателю.
 * Письмо уходит один раз (email_sent_at), повторные вызовы безопасны —
 * функцию зовут и webhook, и check-payment, кто успеет первым.
 * Возвращает список ссылок на скачивание.
 */
function mvb_deliver_and_notify(array &$order): array
{
    $links = mvb_prepare_delivery($order);
    $orderId = (string)($order['id'] ?? '');

    if (!$links) {
        @file_put_contents(ORDERS_DIR . '/delivery-errors.log',
            date('c') . " заказ {$orderId}: не удалось подготовить выдачу (нет файлов продуктов?)\n", FILE_APPEND);
        return [];
    }

    if (!empty($order['delivery']['email_sent_at'])) {
        return $links;
    }

    if (!empty($order['email'])) {
        $subject = 'Ваши материалы «Маржа в бетоне» — заказ оплачен';
        $headers = [
            'From: site@marzhavbetone.ru',
            'Reply-To: ' . ADMIN_EMAIL,
            'Content-Type: text/plain; charset=UTF-8',
        ];
        $sent = mail(
            (string)$order['email'],
            '=?UTF-8?B?' . base64_encode($subject) . '?=',
            mvb_delivery_email($order, $links),
            implode("\r\n", $headers)
        );
        if ($sent) {
            $order['delivery']['email_sent_at'] = date('c');
        } else {
            @file_put_contents(ORDERS_DIR . '/delivery-errors.log',
                date('c') . " не удалось отправить письмо покупателю, заказ {$orderId}\n", FILE_APPEND);
        }
    } else {
        // Покупатель без email (только телефон) — админ высылает ссылки вручную
        @file_put_contents(ORDERS_DIR . '/delivery-errors.log',
            date('c') . " заказ {$orderId} без email: ссылки выдачи в {$orderId}.json, телефон {$order['phone']}\n", FILE_APPEND);
    }
    return $links;
}

/** Текст письма покупателю со ссылками на скачивание. */
function mvb_delivery_email(array $order, array $links): string
{
    $body = "Здравствуйте!\n\n";
    $body .= "Спасибо за покупку. Ваши материалы готовы к скачиванию:\n\n";
    foreach ($links as $link) {
        $body .= '• ' . $link['name'] . "\n  " . $link['url'] . "\n\n";
    }
    $days = DELIVERY_TTL_DAYS;
    $body .= "Ссылки действуют {$days} дней. Сохраните файлы на свой компьютер.\n\n";
    $body .= "Что делать дальше:\n";
    $body .= "1. Скачайте архив и распакуйте его.\n";
    $body .= "2. Откройте файл «00-INSTRUKCIYA.pdf» — начните с него.\n";
    $body .= "3. Адаптируйте документы под свой договор и объект.\n\n";
    $body .= "Важно:\n";
    $body .= "- шаблоны редактируются в Microsoft Word и Excel;\n";
    $body .= "- PDF-файлы используются как чек-листы и алгоритмы;\n";
    $body .= "- для спорных ситуаций нужна проверка профильного специалиста.\n\n";
    $body .= "Вопросы: " . ADMIN_EMAIL . "\n\n";
    $body .= "Команда «Маржа в бетоне»\n";
    return $body;
}
