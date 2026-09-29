<?php
// Собирает покупательский ZIP p7 штатной функцией выдачи
// mvb_build_product_zip() из products-config.php.
//
//   php build_p7.php <корень репозитория> <каталог вывода>
//
// Отличие от боевой выдачи только в путях: ORDERS_DIR/DELIVERY_DIR ведут в
// каталог вывода, PRODUCTS_DIR — в products-storage/ репозитория. Список
// исключений, порядок обхода и имена записей — те же, что у покупателя.
$root = $argv[1] ?? '';
$out = $argv[2] ?? '';
if ($root === '' || $out === '') {
    fwrite(STDERR, "usage: php build_p7.php <repo> <out>\n");
    exit(2);
}
@mkdir($out . '/orders/delivery', 0755, true);
foreach ([
    'ORDERS_DIR' => $out . '/orders',
    'DELIVERY_DIR' => $out . '/orders/delivery',
    'PRODUCTS_DIR' => $root . '/products-storage',
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
$path = mvb_build_product_zip('p7');
if ($path === null) {
    fwrite(STDERR, "mvb_build_product_zip('p7') вернула null\n");
    exit(1);
}
echo $path, "\n";
