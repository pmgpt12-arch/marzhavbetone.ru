<?php
/**
 * Регресс Д-1: частичной выдачи заказа не бывает.
 * Запуск: php tools/test_delivery_all_or_nothing.php
 *
 * Дефект, ради которого написан тест. `mvb_prepare_delivery()` пропускала
 * позицию, для которой не собрался архив, через `continue` без единой
 * записи в лог, а `mvb_deliver_and_notify()` логировала только полный
 * отказ. Заказ на два комплекта, у которого папка мастеров одного из них
 * отсутствует, проходил так: письмо уходило с одной ссылкой из двух,
 * `delivery.email_sent_at` проставлялся, повторная доставка вебхука
 * блокировалась этим полем, а недостающего sku не было в `delivery.items`,
 * поэтому и самовосстановление `download.php` до него не дотягивалось.
 * Деньги за две позиции, выдана одна, в логах пусто.
 *
 * Проверяется боевая функция, а не её пересказ. Ломается не каталог, а
 * раскладка на диске: PRODUCTS_DIR указывает на временную папку, где лежат
 * мастера одного sku и нет мастеров второго. Это ровно та боевая поломка,
 * ради которой в deploy.yml заведён гейт автовыдачи.
 *
 * Письмо не отправляется ни в одном случае: у заказа нет поля `email`, и
 * ветка `mail()` недостижима. Сеть, касса и секреты не нужны.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-all-or-nothing-' . getmypid();
$products = $tmp . '/products';
@mkdir($products, 0777, true);

// Два настоящих sku боевого каталога. Мастера первого кладём, второго — нет.
const ЦЕЛЫЙ = 'p1';
const БИТЫЙ = 'p3';

foreach ([
    'ORDERS_DIR' => $tmp,
    'PRODUCTS_DIR' => $products,
    'SITE_URL' => 'https://example.invalid',
    'ADMIN_EMAIL' => 'admin@example.invalid',
    'DELIVERY_TTL_DAYS' => 7,
    'YOOKASSA_SHOP_ID' => 'test',
    'YOOKASSA_SECRET_KEY' => 'test',
    'YOOKASSA_API_URL' => 'https://example.invalid',
    'YOOKASSA_MODE' => 'test',
] as $name => $value) {
    if (!defined($name)) {
        define($name, $value);
    }
}
require $root . '/products-config.php';

$каталог = mvb_products();
$папкаЦелого = $каталог[ЦЕЛЫЙ]['dir'];
$папкаБитого = $каталог[БИТЫЙ]['dir'];

// Мастера целого sku — минимальные: сборщику важно, что папка не пуста.
@mkdir($products . '/' . $папкаЦелого, 0777, true);
file_put_contents($products . '/' . $папкаЦелого . '/01-doc.txt', "содержимое\n");
file_put_contents($products . '/' . $папкаЦелого . '/MANIFEST.md', "служебный\n");

$провалов = 0;
function проверка(string $имя, bool $ок, string $чем = ''): void
{
    global $провалов;
    if ($ок) { echo "  ок   {$имя}\n"; return; }
    $провалов++;
    echo "  ПРОВАЛ {$имя}" . ($чем !== '' ? ": {$чем}" : '') . "\n";
}

function заказ(array $skus, string $id): array
{
    $каталог = mvb_products();
    $items = [];
    foreach ($skus as $sku) {
        $items[] = ['sku' => $sku, 'name' => $каталог[$sku]['name'], 'price' => $каталог[$sku]['price']];
    }
    return ['id' => $id, 'status' => 'paid', 'items' => $items,
            'total' => array_sum(array_column($items, 'price'))];
}

$лог = ORDERS_DIR . '/delivery-errors.log';
@unlink($лог);

echo "Д-1: частичная выдача запрещена\n";

// --- Случай 1: одна из двух позиций не собирается -------------------------
$битый = заказ([ЦЕЛЫЙ, БИТЫЙ], 'order_20260917_101010_aaa111');
$ссылки = mvb_deliver_and_notify($битый);

проверка('битый заказ: ссылок не выдано', $ссылки === [], json_encode($ссылки));
проверка('битый заказ: delivery в заказ не записан', !isset($битый['delivery']));
проверка('битый заказ: отметки отправки письма нет', empty($битый['delivery']['email_sent_at']));

$строка = (string)@file_get_contents($лог);
проверка('в логе назван номер заказа', strpos($строка, 'order_20260917_101010_aaa111') !== false, $строка);
проверка('в логе назван недостающий sku', strpos($строка, БИТЫЙ) !== false, $строка);
проверка('в логе нет почты покупателя', strpos($строка, '@') === false || strpos($строка, 'example.invalid') === false);
проверка('в логе нет токена выдачи', !preg_match('/[0-9a-f]{32}/', $строка), $строка);

// --- Случай 2: причина устранена, тот же заказ выдаётся целиком -----------
@mkdir($products . '/' . $папкаБитого, 0777, true);
file_put_contents($products . '/' . $папкаБитого . '/01-doc.txt', "второй\n");

$починенный = заказ([ЦЕЛЫЙ, БИТЫЙ], 'order_20260917_101010_aaa111');
$ссылки2 = mvb_deliver_and_notify($починенный);
проверка('после починки: выданы обе позиции', count($ссылки2) === 2, 'ссылок ' . count($ссылки2));
проверка('после починки: delivery.items содержит оба sku',
    isset($починенный['delivery']['items'][ЦЕЛЫЙ], $починенный['delivery']['items'][БИТЫЙ]),
    json_encode($починенный['delivery']['items'] ?? null));
проверка('после починки: токен выдан', !empty($починенный['delivery']['token']));
проверка('после починки: срок ссылки проставлен', !empty($починенный['delivery']['expires_at']));

// --- Случай 3: служебные файлы в архив не попали --------------------------
$архив = new ZipArchive();
$архив->open(DELIVERY_DIR . '/' . $каталог[ЦЕЛЫЙ]['zip']);
$внутри = [];
for ($i = 0; $i < $архив->numFiles; $i++) { $внутри[] = $архив->getNameIndex($i); }
$архив->close();
проверка('MANIFEST.md в архив не попал', !in_array('MANIFEST.md', $внутри, true), implode(', ', $внутри));

// --- Случай 4: заказ без позиций тоже не выдаётся -------------------------
$пустой = ['id' => 'order_20260917_101010_bbb222', 'status' => 'paid', 'items' => [], 'total' => 0];
$ссылки4 = mvb_deliver_and_notify($пустой);
проверка('пустой заказ: выдача отменена', $ссылки4 === []);
проверка('пустой заказ: delivery не создан', !isset($пустой['delivery']));

// Уборка
foreach (glob($tmp . '/delivery/*') ?: [] as $f) { @unlink($f); }
@rmdir($tmp . '/delivery');
foreach (glob($products . '/*/*') ?: [] as $f) { @unlink($f); }
foreach (glob($products . '/*') ?: [] as $d) { @rmdir($d); }
@rmdir($products);
foreach (glob($tmp . '/*') ?: [] as $f) { if (is_file($f)) { @unlink($f); } }
@rmdir($tmp);

if ($провалов) { echo "\nпровалов: {$провалов}\n"; exit(1); }
echo "\nчастичная выдача невозможна: недостача отменяет заказ целиком, письма и отметки нет, после починки выдаётся полностью\n";
exit(0);
