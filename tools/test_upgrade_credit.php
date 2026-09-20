<?php
/**
 * Регресс: зачёт стоимости ступени считает сервер по оплаченным заказам.
 * Запуск: php tools/test_upgrade_credit.php
 *
 * Почему это отдельный тест. Страница ступени обещает покупателю, что её
 * стоимость зачтётся при переходе на ядро. Обещание исполняется кодом, и
 * ошибиться здесь можно двумя способами, каждый из которых стоит денег.
 *
 *   Не дать зачёт тому, кто его заслужил — вернуть обещание в состояние,
 *   которое аудит MB004 назвал неисполнимым.
 *   Дать зачёт тому, кто ступень не покупал, — раздать ядро дешевле
 *   каталога любому, кто подобрал параметр в консоли браузера.
 *
 * Проверяется поведение, а не намерение: в `mvb_apply_upgrade_credit()`
 * подаются корзины и заказы во временной папке, и сверяется итоговая цена.
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-upgrade-' . bin2hex(random_bytes(4));
mkdir($tmp, 0755, true);

foreach ([
    'ORDERS_DIR' => $tmp,
    'DELIVERY_DIR' => $tmp . '/delivery',
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

$map = mvb_upgrade_steps();
if (!$map) {
    echo "Тест не запускался: карта зачёта пуста\n";
    exit(2);
}
$coreSku = array_key_first($map);
$stepSku = $map[$coreSku];
foreach ([$coreSku, $stepSku] as $sku) {
    if (!isset($catalog[$sku])) {
        echo "Тест не запускался: в каталоге нет {$sku}\n";
        exit(2);
    }
}
$corePrice = (int)$catalog[$coreSku]['price'];
$stepPrice = (int)$catalog[$stepSku]['price'];

// Корзина строится каталогом — ровно так, как её собирает payment.php
// после mvb_resolve_product(): цена уже серверная.
function корзина(string $sku): array
{
    $p = mvb_resolve_product(['sku' => $sku]);
    return [['sku' => $p['sku'], 'name' => $p['name'], 'price' => $p['price']]];
}

function заказ(string $file, array $data): void
{
    file_put_contents($file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function итог(array $items): int
{
    $t = 0;
    foreach ($items as $i) {
        $t += (int)$i['price'];
    }
    return $t;
}

$почта = 'buyer@example.invalid';
$шаг = function (string $id, array $over = []) use ($tmp, $stepSku, $stepPrice, $почта, $catalog) {
    заказ($tmp . '/' . $id . '.json', $over + [
        'id' => $id,
        'status' => 'paid',
        'email' => $почта,
        'phone' => '',
        'items' => [['sku' => $stepSku, 'name' => $catalog[$stepSku]['name'], 'price' => $stepPrice]],
        'total' => $stepPrice,
    ]);
};
$очистить = function () use ($tmp) {
    foreach (glob($tmp . '/order_*.json') ?: [] as $f) {
        unlink($f);
    }
};

// 1. Новый покупатель платит полную цену ядра.
$очистить();
$r = mvb_apply_upgrade_credit(корзина($coreSku), 'nobody@example.invalid', '');
if ($r['upgrade'] !== null || итог($r['items']) !== $corePrice) {
    $failures[] = 'новый покупатель получил зачёт: итог ' . итог($r['items']) . ' вместо ' . $corePrice;
}

// 2. Покупатель ступени платит цену ядра минус фактически уплаченное.
$очистить();
$шаг('order_20260101_000000_aaaaaa');
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
$ожидание = $corePrice - $stepPrice;
if ($r['upgrade'] === null || итог($r['items']) !== $ожидание) {
    $failures[] = 'зачёт не применён: итог ' . итог($r['items']) . ' вместо ' . $ожидание;
} elseif ((int)$r['upgrade']['credit'] !== $stepPrice) {
    $failures[] = 'зачтено ' . $r['upgrade']['credit'] . ' вместо уплаченного ' . $stepPrice;
}

// 3. Зачёт равен УПЛАЧЕННОМУ, а не текущей цене каталога. Цена ступени —
// решение владельца и меняется; зачесть надо то, что покупатель отдал.
$очистить();
$иная = (int)round($stepPrice / 2);
$шаг('order_20260101_000000_bbbbbb', ['items' => [['sku' => $stepSku, 'name' => $catalog[$stepSku]['name'], 'price' => $иная]]]);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if ($r['upgrade'] === null || (int)$r['upgrade']['credit'] !== $иная) {
    $failures[] = 'зачтена цена каталога, а не уплаченная сумма: '
        . var_export($r['upgrade']['credit'] ?? null, true) . ' вместо ' . $иная;
}

// 4. Подделанные поля браузера зачёта не дают — на всём пути.
//
// Проверяется дважды, и второй случай важнее первого. Первый повторяет
// боевой путь: payment.php пересобирает позицию из каталога, и лишние поля
// до расчёта зачёта не доходят. Второй подаёт подделку ПРЯМО в расчёт, как
// если бы будущая правка забыла её отфильтровать. Без него мутация «брать
// зачёт из поля запроса, когда своя покупка не нашлась» остаётся живой:
// первый случай её не видит, потому что поле до функции не долетает.
$подделка = [
    'sku' => $coreSku, 'name' => $catalog[$coreSku]['name'], 'price' => 100,
    'upgrade' => true, 'credit' => $corePrice - 100, 'discount' => 990,
    'full_price' => $corePrice * 10,
];

$очистить();
$p = mvb_resolve_product($подделка);
$r = mvb_apply_upgrade_credit([['sku' => $p['sku'], 'name' => $p['name'], 'price' => $p['price']]],
    'nobody@example.invalid', '');
if ($r['upgrade'] !== null || итог($r['items']) !== $corePrice) {
    $failures[] = 'подделанные поля корзины дали скидку: итог ' . итог($r['items']);
}

$очистить();
// Цена здесь каталожная намеренно: с заниженной ценой расчёт обрывается
// раньше — на защите «итог не уходит в ноль», — и подделка размера скидки
// осталась бы непроверенной.
$сПравильнойЦеной = $подделка;
$сПравильнойЦеной['price'] = $corePrice;
$r = mvb_apply_upgrade_credit([$сПравильнойЦеной], 'nobody@example.invalid', '');
if ($r['upgrade'] !== null || итог($r['items']) !== $corePrice) {
    $failures[] = 'зачёт взят из полей запроса, а не из оплаченных заказов: итог '
        . итог($r['items']) . ', зачёт ' . var_export($r['upgrade']['credit'] ?? null, true);
}

// 5. Неоплаченный заказ ступени права не даёт.
$очистить();
$шаг('order_20260101_000000_cccccc', ['status' => 'pending']);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if ($r['upgrade'] !== null) {
    $failures[] = 'зачёт дан по неоплаченному заказу';
}

// 6. Израсходованное право второй раз не даётся.
$очистить();
$шаг('order_20260101_000000_dddddd', ['upgrade_claim' => ['order_id' => 'order_x', 'at' => date('c'), 'status' => 'used']]);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if ($r['upgrade'] !== null) {
    $failures[] = 'израсходованное право дало второй зачёт';
}

// 7. Брошенная корзина право не съедает: просроченная заявка не мешает.
$очистить();
$шаг('order_20260101_000000_eeeeee', ['upgrade_claim' => [
    'order_id' => 'order_y',
    'at' => date('c', time() - MVB_UPGRADE_CLAIM_TTL - 60),
    'status' => 'pending',
]]);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if ($r['upgrade'] === null) {
    $failures[] = 'просроченная заявка навсегда съела право покупателя';
}

// 8. Свежая заявка право держит: два одновременных перехода не спишут одну
// ступень дважды.
$очистить();
$шаг('order_20260101_000000_ffffff', ['upgrade_claim' => ['order_id' => 'order_z', 'at' => date('c'), 'status' => 'pending']]);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if ($r['upgrade'] !== null) {
    $failures[] = 'свежая заявка не удержала право — ступень спишется дважды';
}

// 9. Чужая покупка зачёта не даёт.
$очистить();
$шаг('order_20260101_000000_gggggg', ['email' => 'someone.else@example.invalid']);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if ($r['upgrade'] !== null) {
    $failures[] = 'зачёт дан по чужой покупке';
}

// 10. Телефон опознаётся в любом написании: один покупатель — одно право.
$очистить();
$шаг('order_20260101_000000_hhhhhh', ['email' => '', 'phone' => '+7 (999) 123-45-67']);
$r = mvb_apply_upgrade_credit(корзина($coreSku), '', '89991234567');
if ($r['upgrade'] === null) {
    $failures[] = 'тот же номер в другом написании не опознан — покупатель потерял право';
}

// 11. Итог не уходит в ноль и не становится отрицательным, даже если
// уплачено за ступень больше, чем стоит ядро.
$очистить();
$шаг('order_20260101_000000_iiiiii', ['items' => [['sku' => $stepSku, 'name' => $catalog[$stepSku]['name'], 'price' => $corePrice * 10]]]);
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
if (итог($r['items']) <= 0) {
    $failures[] = 'итог ушёл в ноль или минус: ' . итог($r['items']);
}

// 12. Зачёт не более одного на заказ: два ядра не спишут одну ступень дважды.
$очистить();
$шаг('order_20260101_000000_jjjjjj');
$две = array_merge(корзина($coreSku), корзина($coreSku));
$r = mvb_apply_upgrade_credit($две, $почта, '');
if (итог($r['items']) !== $corePrice * 2 - $stepPrice) {
    $failures[] = 'зачёт применён дважды в одном заказе: итог ' . итог($r['items'])
        . ' вместо ' . ($corePrice * 2 - $stepPrice);
}

// 13. Позиция ядра не теряет sku и имя — иначе сломается выдача и чек.
$очистить();
$шаг('order_20260101_000000_kkkkkk');
$r = mvb_apply_upgrade_credit(корзина($coreSku), $почта, '');
$поз = $r['items'][0];
if (($поз['sku'] ?? '') !== $coreSku || ($поз['name'] ?? '') !== $catalog[$coreSku]['name']) {
    $failures[] = 'после зачёта позиция потеряла sku или имя — выдача и чек сломаются';
}
if ((int)($поз['full_price'] ?? 0) !== $corePrice) {
    $failures[] = 'полная цена не сохранена в позиции — зачёт неаудируем';
}

// 14. Покупка ступени сама по себе скидки не получает.
$очистить();
$шаг('order_20260101_000000_llllll');
$r = mvb_apply_upgrade_credit(корзина($stepSku), $почта, '');
if ($r['upgrade'] !== null || итог($r['items']) !== $stepPrice) {
    $failures[] = 'повторная покупка ступени получила скидку';
}

// 16. Цена перехода, названная на странице ступени, совпадает с расчётом.
//
// Число написано в HTML руками — как и все цены сайта, — и разойтись с
// каталогом может молча. Именно так появилось «27 процентов совпадения»,
// которое эта задача убирала: цифра в разметке пережила то, что её
// породило. Здесь проверяется не вёрстка, а обещание покупателю.
$страница = $root . '/products/t1-pervyy-shag-pri-neoplate.html';
if (is_file($страница)) {
    $html = (string)file_get_contents($страница);
    $переход = intdiv($corePrice - $stepPrice, 100);
    // Разряды на страницах разделены обычным пробелом — замер по цене ядра
    // на её же странице, а не по типографскому правилу.
    $ожидаемо = number_format($переход, 0, '', ' ') . ' ₽';
    if (mb_strpos($html, $ожидаемо) === false) {
        $failures[] = 'страница ступени не называет цену перехода ' . $ожидаемо
            . ' — обещание разошлось с каталогом';
    }
    // И наоборот: полной цены ядра как цены перехода на странице быть не должно.
    foreach (['27 процентов', '58 до 86', 'вычитку юристом'] as $снятое) {
        if (mb_strpos($html, $снятое) !== false) {
            $failures[] = 'на странице ступени вернулось снятое утверждение: ' . $снятое;
        }
    }
}

foreach (glob($tmp . '/*') ?: [] as $f) {
    is_dir($f) ? @rmdir($f) : @unlink($f);
}
@rmdir($tmp);

if ($failures) {
    echo "Зачёт стоимости ступени: ДЕФЕКТ\n";
    foreach ($failures as $f) {
        echo "  ✗ {$f}\n";
    }
    exit(1);
}
printf("Зачёт стоимости ступени: 16 проверок пройдено. %s -> %s, полная цена %d коп., "
    . "после зачёта %d коп.\n", $stepSku, $coreSku, $corePrice, $corePrice - $stepPrice);
exit(0);
