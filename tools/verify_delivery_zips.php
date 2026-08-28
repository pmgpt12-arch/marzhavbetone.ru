<?php
/**
 * Проверка собранных архивов выдачи против источника.
 *
 * ЗАЧЕМ. После чистки кэша архивы пересобираются, и убедиться надо не в том,
 * что файл появился, а в том, что он собран из того, что лежит на диске.
 * Проверка «в архиве есть 00-START-HERE.txt» этого не даёт: она пройдёт и на
 * архиве, потерявшем половину состава.
 *
 * ИСТОЧНИК ИСТИНЫ — та же папка и тот же перечень служебных файлов, которыми
 * пользуется сам сборщик `mvb_build_product_zip`. Второго списка состава здесь
 * не заводится: он разошёлся бы с первым, и проверка стала бы проверять себя.
 *
 * ГДЕ ЗАПУСКАТЬ. На сервере, из корня сайта, после выкладки и чистки кэша.
 * В репозитории файл лежит в `tools/`, а `tools/` на сервер не заливается —
 * скопировать, запустить, удалить (процедура в
 * ai-business-os/projects/marzha_v_betone/SALES_FUNNEL_RC1_DEPLOY_RUNBOOK.md,
 * шаг 6).
 *
 *     php verify_delivery_zips.php
 *
 * Код возврата 1 — хоть один архив разошёлся с источником.
 */
define('ORDERS_DIR', __DIR__ . '/orders');
require __DIR__ . '/products-config.php';

$service = ['.htaccess', '00-PISMO-POSLE-POKUPKI.txt', 'MANIFEST.md'];
$skus = ['t1','t2','t3','t4','t5','t6','p1','p2','p3','p4','p5','p7','p8','p9','p10','p11','p12','p13'];
$bad = 0;

foreach ($skus as $sku) {
    $catalog = mvb_products();
    $dir = PRODUCTS_DIR . '/' . $catalog[$sku]['dir'];
    $want = [];
    foreach (scandir($dir) as $f) {
        if ($f === '.' || $f === '..' || in_array($f, $service, true)) continue;
        if (is_file("$dir/$f")) $want[] = $f;
    }
    sort($want);

    $zipPath = mvb_build_product_zip($sku);
    $problems = [];
    if (!$zipPath || !is_file($zipPath)) { $problems[] = 'архив не собрался'; }
    else {
        $zip = new ZipArchive();
        if ($zip->open($zipPath) !== true) { $problems[] = 'архив не открывается'; }
        else {
            $got = [];
            $empty = [];
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $st = $zip->statIndex($i);
                $got[] = $st['name'];
                if ((int)$st['size'] === 0) $empty[] = $st['name'];
            }
            sort($got);
            if ($got !== $want) {
                $problems[] = 'состав разошёлся: лишние [' . implode(', ', array_diff($got, $want))
                            . '], отсутствуют [' . implode(', ', array_diff($want, $got)) . ']';
            }
            if (!in_array('00-START-HERE.txt', $got, true)) $problems[] = 'нет 00-START-HERE.txt';
            foreach ($service as $s) if (in_array($s, $got, true)) $problems[] = "служебный $s попал в архив";
            if ($empty) $problems[] = 'пустые файлы: ' . implode(', ', $empty);
            if (filesize($zipPath) < 1024) $problems[] = 'архив меньше килобайта';
            $zip->close();
        }
    }
    if ($problems) { $bad++; printf("%-4s ПРОВАЛ  %s\n", $sku, implode('; ', $problems)); }
    else printf("%-4s ok  файлов %d, %d КБ\n", $sku, count($want), (int)(filesize($zipPath)/1024));
}
printf("\nкомплектов %d, с бедой %d\n", count($skus), $bad);
exit($bad ? 1 : 0);
