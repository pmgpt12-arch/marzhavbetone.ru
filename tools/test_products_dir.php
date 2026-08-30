<?php
/**
 * Регресс на молчаливую невыдачу. Запуск: php tools/test_products_dir.php
 *
 * Что проверяется. Архив покупателю собирается из мастеров продуктов, и
 * лежат они на боевом сервере не там, где в репозитории: deploy.yml
 * перечисляет `products-storage` в исключениях заливки сайта и кладёт
 * мастера отдельным шагом ВНЕ webroot. Пока PRODUCTS_DIR подставлялась
 * безусловно как `products-storage` рядом с сайтом, выдача на боевом
 * держалась на строке, которую владелец должен был дописать в config.php
 * руками — при том что этой строки не было ни в шаблоне config.php, ни в
 * DEPLOY.md (файла нет вовсе).
 *
 * Почему это не ловилось. verify_delivery_zips.php собирает все восемнадцать
 * архивов и проходит — в прогоне CI `products-storage/` лежит рядом с
 * сайтом, то есть проверка меряет раскладку репозитория, а не боевую. Отказ
 * же виден только после оплаты: покупатель платит, mvb_build_product_zip()
 * не находит папку, возвращает null, ссылок нет, письмо не уходит. Деньги
 * списаны, товар не выдан, в логе одна строка.
 *
 * Здесь проверяется сам поиск пути на поддельных раскладках. Ключевой
 * случай — третий: пустой `products-storage/`, оставшийся от прежней
 * заливки, не должен перебивать настоящие мастера за пределами webroot.
 *
 * Проверен мутацией: если вернуть в products-config.php безусловное
 * `$siteDir . '/products-storage'`, краснеют случаи «боевая раскладка» и
 * «пустой каталог рядом с сайтом».
 */
declare(strict_types=1);

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-products-dir-' . getmypid();

// Явный define старше поиска — проверяем это первым, потому что define
// одноразовый: объявленную здесь константу products-config.php обязан
// оставить в покое.
$explicit = $tmp . '/явный-путь-владельца';
@mkdir($explicit . '/01-товар', 0777, true);
file_put_contents($explicit . '/01-товар/файл.txt', 'x');

foreach ([
    'ORDERS_DIR'          => $tmp . '/orders',
    'PRODUCTS_DIR'        => $explicit,
    'SITE_URL'            => 'https://example.invalid',
    'ADMIN_EMAIL'         => 'admin@example.invalid',
    'YOOKASSA_SHOP_ID'    => 'test',
    'YOOKASSA_SECRET_KEY' => 'test',
    'YOOKASSA_API_URL'    => 'https://example.invalid',
    'YOOKASSA_MODE'       => 'test',
] as $имя => $значение) {
    if (!defined($имя)) {
        define($имя, $значение);
    }
}
require $root . '/products-config.php';

$провалы = [];
$проверить = static function (string $имя, $ожидалось, $получено) use (&$провалы): void {
    if ($ожидалось !== $получено) {
        $провалы[] = "{$имя}: ожидалось " . var_export($ожидалось, true)
                   . ", получено " . var_export($получено, true);
    }
};

$проверить('явный define в config.php не тронут', $explicit, PRODUCTS_DIR);

/** Раскладка: создаёт каталоги, помечая непустые товаром внутри. */
$раскладка = static function (string $корень, array $каталоги): string {
    foreach ($каталоги as $путь => $сТоваром) {
        @mkdir($корень . '/' . $путь, 0777, true);
        if ($сТоваром) {
            @mkdir($корень . '/' . $путь . '/09-товар', 0777, true);
            file_put_contents($корень . '/' . $путь . '/09-товар/00-START-HERE.txt', 'x');
        }
    }
    return $корень;
};

// Сайт всегда на два уровня ниже домашней папки — как на reg.ru:
// <корень>/www/marzhavbetone.ru, мастера в <корень>/products-marzhavbetone.
$случаи = [
    'репозиторий: мастера рядом с сайтом' => [
        ['www/marzhavbetone.ru/products-storage' => true],
        'www/marzhavbetone.ru/products-storage',
    ],
    'боевая раскладка: мастера вне webroot' => [
        ['products-marzhavbetone' => true],
        'products-marzhavbetone',
    ],
    'пустой products-storage не перебивает боевые мастера' => [
        ['www/marzhavbetone.ru/products-storage' => false, 'products-marzhavbetone' => true],
        'products-marzhavbetone',
    ],
    'сайт лежит в домашней папке' => [
        ['marzhavbetone.ru/products-storage' => false, 'products-marzhavbetone' => true],
        'products-marzhavbetone',
    ],
    'мастеров нет нигде: путь по умолчанию ради внятной ошибки' => [
        [],
        'www/marzhavbetone.ru/products-storage',
    ],
];

$н = 0;
foreach ($случаи as $имя => [$каталоги, $ждём]) {
    $корень = $tmp . '/случай-' . (++$н);
    // Сайт в домашней папке — это на уровень выше обычного.
    $сайт = $корень . (isset($каталоги['marzhavbetone.ru/products-storage'])
        ? '/marzhavbetone.ru' : '/www/marzhavbetone.ru');
    @mkdir($сайт, 0777, true);
    $раскладка($корень, $каталоги);

    $получено = mvb_resolve_products_dir($сайт);
    $норм = static fn (string $p): string => (realpath($p) ?: $p);
    $проверить($имя, $норм($корень . '/' . $ждём), $норм($получено));
}

// Каталог с пустой папкой товара внутри — это не мастера.
$пустой = $tmp . '/только-пустая-папка';
@mkdir($пустой . '/01-товар', 0777, true);
$проверить('пустая папка товара не считается мастерами', false,
    mvb_products_dir_has_masters($пустой));

$rmrf = static function (string $dir) use (&$rmrf): void {
    foreach (glob($dir . '/*') ?: [] as $p) {
        is_dir($p) ? $rmrf($p) : @unlink($p);
    }
    @rmdir($dir);
};
$rmrf($tmp);

if ($провалы) {
    echo "Поиск мастеров продуктов: СЛОМАН\n";
    foreach ($провалы as $f) {
        echo "  ✗ {$f}\n";
    }
    exit(1);
}
echo 'Поиск мастеров продуктов: раскладок проверено ' . count($случаи)
   . ", явный define старше поиска, пустой каталог не выдаётся за товар.\n";
exit(0);
