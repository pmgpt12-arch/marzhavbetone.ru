<?php
/**
 * Регресс: цену назначает сервер, а не браузер.
 * Запуск: php tools/test_price_authority.php
 *
 * Почему это отдельный тест. Корзина живёт в localStorage, и товар уходит
 * на сервер вместе с полями `sku`, `name` и `price` — все три пришли из
 * браузера и все три подделываются в консоли за секунду. Если сервер
 * возьмёт `price` из запроса, покупатель оформит комплект за рубль, и
 * касса выставит счёт ровно на эту сумму: ЮKassa считает то, что ей
 * прислали.
 *
 * Проверяется не намерение кода, а его поведение: в `mvb_resolve_product()`
 * подаются подделанные позиции и требуется, чтобы вернулась цена каталога.
 *
 * Проверен мутацией 15.08.2026: если в `mvb_resolve_product()` поменять
 * порядок объединения на `$catalog[$sku] + $item` — то есть дать полям
 * запроса победить, — тест краснеет на всех четырёх случаях подделки.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
foreach ([
    'ORDERS_DIR' => sys_get_temp_dir(),
    'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'a@example.invalid',
    'DELIVERY_TTL_DAYS' => 7,
    'YOOKASSA_SHOP_ID' => 't',
    'YOOKASSA_SECRET_KEY' => 't',
    'YOOKASSA_API_URL' => 'https://example.invalid',
    'YOOKASSA_MODE' => 'test',
] as $name => $value) {
    if (!defined($name)) {
        define($name, $value);
    }
}
require $root . '/products-config.php';

$catalog = mvb_products();
$failures = [];

// Берём любой существующий платный товар — тест не должен зависеть от
// состава каталога, он меняется решением владельца.
$sku = null;
foreach ($catalog as $key => $product) {
    if (($product['price'] ?? 0) > 0) {
        $sku = $key;
        break;
    }
}
if ($sku === null) {
    echo "Тест не запускался: в каталоге нет платного товара\n";
    exit(2);
}
$realPrice = $catalog[$sku]['price'];
$realName = $catalog[$sku]['name'];

// 1. Подделка цены при верном sku.
$resolved = mvb_resolve_product(['sku' => $sku, 'name' => $realName, 'price' => 1]);
if (!$resolved || $resolved['price'] !== $realPrice) {
    $failures[] = 'подделанная цена при верном sku прошла: получено '
        . var_export($resolved['price'] ?? null, true) . ' вместо ' . $realPrice;
}

// 2. Подделка цены при опознании по названию (sku не передан).
$resolved = mvb_resolve_product(['name' => $realName, 'price' => 100]);
if (!$resolved || $resolved['price'] !== $realPrice) {
    $failures[] = 'подделанная цена при опознании по названию прошла: получено '
        . var_export($resolved['price'] ?? null, true) . ' вместо ' . $realPrice;
}

// 3. Отрицательная цена — попытка увести итог в минус.
$resolved = mvb_resolve_product(['sku' => $sku, 'price' => -500000]);
if (!$resolved || $resolved['price'] !== $realPrice) {
    $failures[] = 'отрицательная цена прошла: получено '
        . var_export($resolved['price'] ?? null, true) . ' вместо ' . $realPrice;
}

// 4. Несуществующий товар обязан быть отвергнут, а не создан на лету.
if (mvb_resolve_product(['sku' => 'no-such-sku-xyz', 'name' => 'Придуманный', 'price' => 10]) !== null) {
    $failures[] = 'несуществующий товар не отвергнут — заказ можно собрать из выдуманных позиций';
}

// 5. Имя тоже берётся из каталога: иначе в чек ЮKassa уедет чужой текст.
$resolved = mvb_resolve_product(['sku' => $sku, 'name' => 'Бесплатно, подарок']);
if (!$resolved || $resolved['name'] !== $realName) {
    $failures[] = 'название взято из запроса, а не из каталога — в кассовый чек уйдёт чужой текст';
}

if ($failures) {
    echo "Цену назначает браузер: ДЕФЕКТ\n";
    foreach ($failures as $f) {
        echo "  ✗ {$f}\n";
    }
    exit(1);
}
echo "Цену назначает сервер: {$sku} — подделка цены, имени и несуществующий "
   . "товар отвергнуты (эталон {$realPrice} коп.).\n";
exit(0);
