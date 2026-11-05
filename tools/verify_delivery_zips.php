<?php
/**
 * Delivery ZIP integrity, two explicit sources of truth.
 *
 * Dynamic legacy SKUs: compare generated ZIP entries with unpacked masters.
 * Paid pinned SKUs: verify approved master ZIP SHA-256, CRC and buyer entry.
 *
 * Public CI cannot access private paid masters. With BOTH GITHUB_ACTIONS=true
 * and explicit NSP_PINNED_QA_SYNTHETIC=1, run the separate exact-code synthetic
 * 11-SKU contract (same builder, disposable SHA-patched PHP). This is NOT real
 * archive acceptance. On hosting, no such bypass is permitted.
 */
declare(strict_types=1);
define('ORDERS_DIR', __DIR__ . '/orders');
require __DIR__ . '/products-config.php';

$service = ['.htaccess', '00-PISMO-POSLE-POKUPKI.txt', 'MANIFEST.md'];
$dynamic = ['t1','t2','t3','t4','t5','t6','p12'];
$pinned = ['p1','p2','p3','p4','p5','p7','p8','p9','p10','p11','p13'];
$bad = 0;
$checkedDynamic = 0;
foreach ($dynamic as $sku) {
    $catalog = mvb_products();
    if (!isset($catalog[$sku])) {
        printf("%-4s ПРОВАЛ  SKU отсутствует\n", $sku); $bad++; continue;
    }
    $dir = PRODUCTS_DIR . '/' . $catalog[$sku]['dir'];
    if (!is_dir($dir)) {
        printf("%-4s ПРОВАЛ  папка мастеров отсутствует\n", $sku); $bad++; continue;
    }
    $want = [];
    foreach (scandir($dir) ?: [] as $entry) {
        if ($entry === '.' || $entry === '..' || in_array($entry, $service, true)) continue;
        if (is_file("$dir/$entry")) $want[] = $entry;
    }
    sort($want);
    $zipPath = mvb_build_product_zip($sku);
    $problems = [];
    if (!$zipPath || !is_file($zipPath)) {
        $problems[] = 'архив не собрался';
    } else {
        $zip = new ZipArchive();
        if ($zip->open($zipPath) !== true) {
            $problems[] = 'архив не открывается';
        } else {
            $got = []; $empty = [];
            for ($i=0; $i<$zip->numFiles; $i++) {
                $st = $zip->statIndex($i);
                $got[] = $st['name'];
                if ((int)$st['size'] === 0) $empty[] = $st['name'];
                if ($zip->getFromIndex($i) === false) $problems[] = 'CRC/чтение повреждено';
            }
            sort($got);
            if ($got !== $want) $problems[] = 'состав разошёлся';
            if (!array_intersect(['00-START-HERE.pdf','00-START-HERE.txt','00-INSTRUKCIYA.pdf'], $got)) {
                $problems[] = 'нет покупательской инструкции';
            }
            foreach ($service as $s) if (in_array($s, $got, true)) $problems[] = "служебный $s попал в архив";
            if ($empty) $problems[] = 'пустые файлы';
            if (filesize($zipPath) < 1024) $problems[] = 'архив меньше килобайта';
            $zip->close();
        }
    }
    if ($problems) {
        $bad++; printf("%-4s ПРОВАЛ  %s\n", $sku, implode('; ', array_unique($problems)));
    } else {
        $checkedDynamic++;
        printf("%-4s ok  динамический архив, файлов %d\n", $sku, count($want));
    }
}

$synthetic = getenv('GITHUB_ACTIONS') === 'true'
    && getenv('NSP_PINNED_QA_SYNTHETIC') === '1';
if (getenv('NSP_PINNED_QA_SYNTHETIC') === '1' && !$synthetic) {
    fwrite(STDERR, "PINNED_SYNTHETIC_MODE_FORBIDDEN_OUTSIDE_GITHUB_ACTIONS\n");
    exit(2);
}
$checkedPinned = 0;
if ($synthetic) {
    $script = __DIR__ . '/tools/test_pinned_delivery_zips.php';
    if (!is_file($script)) {
        fwrite(STDERR, "PINNED_SYNTHETIC_SCRIPT_MISSING\n"); exit(2);
    }
    $proc = proc_open([PHP_BINARY, $script], [
        0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w'],
    ], $pipes, __DIR__);
    if (!is_resource($proc)) {
        fwrite(STDERR, "PINNED_SYNTHETIC_PROCESS_FAILED\n"); exit(2);
    }
    fclose($pipes[0]);
    $raw = stream_get_contents($pipes[1], 100000);
    $error = stream_get_contents($pipes[2], 5000);
    fclose($pipes[1]); fclose($pipes[2]);
    $exit = proc_close($proc);
    $report = json_decode($raw, true);
    if ($exit !== 0 || !is_array($report) || ($report['status'] ?? '') !== 'PASS_SYNTHETIC_ONLY'
        || ($report['paid_sku_covered'] ?? 0) !== count($pinned)
        || ($report['corrupt_master_rejected'] ?? 0) !== count($pinned)
        || ($report['missing_master_rejected'] ?? 0) !== count($pinned)
        || ($report['exact_cache_repaired'] ?? 0) !== count($pinned)
        || ($report['real_paid_archives_read'] ?? -1) !== 0) {
        $bad++;
        fwrite(STDERR, "PINNED_SYNTHETIC_FAILED " . substr((string)$error, 0, 1000) . "\n");
    } else {
        $checkedPinned = count($pinned);
        echo "PAID PINNED CONTRACT: 11/11 SYNTHETIC PASS (NOT real paid ZIP acceptance)\n";
    }
} else {
    // Protected hosting mode: only exact SHA-approved master ZIPs, never
    // substitute a synthetic fixture or reconstruct from unpacked folders.
    $source = file_get_contents(__DIR__ . '/products-config.php');
    if (!is_string($source)) { fwrite(STDERR, "PINNED_SOURCE_READ_FAILED\n"); exit(2); }
    $actual = [];
    $p1Pattern = <<<'REGEX'
~\$sha\s*=\s*'([0-9a-f]{64})';~
REGEX;
    $p1MasterPattern = <<<'REGEX'
~\$master\s*=\s*PRODUCTS_DIR\s*\.\s*'/([^']+\.zip)'~
REGEX;
    if (preg_match($p1Pattern, $source, $m) !== 1
        || preg_match($p1MasterPattern, $source, $p) !== 1) {
        fwrite(STDERR, "P1_PINNED_CONTRACT_NOT_RECOGNIZED\n"); exit(2);
    }
    $actual['p1'] = ['sha'=>$m[1], 'master'=>$p[1]];
    $pinPattern = <<<'REGEX'
~'(p[0-9]+)'\s*=>\s*\['([0-9a-f]{64})',\s*'/([^']+\.zip)'\]~
REGEX;
    preg_match_all($pinPattern, $source, $matches, PREG_SET_ORDER);
    foreach ($matches as $match) {
        if (isset($actual[$match[1]])) { fwrite(STDERR, "DUPLICATE_PIN\n"); exit(2); }
        $actual[$match[1]] = ['sha'=>$match[2], 'master'=>$match[3]];
    }
    $names = array_keys($actual); sort($names);
    $expectedNames = $pinned; sort($expectedNames);
    if ($names !== $expectedNames) { fwrite(STDERR, "PINNED_SKU_COVERAGE_DRIFT\n"); exit(2); }
    $siteRoot = realpath(__DIR__);
    $productRoot = realpath(PRODUCTS_DIR);
    if ($productRoot === false || str_starts_with($productRoot.'/', $siteRoot.'/')) {
        fwrite(STDERR, "PINNED_MASTERS_NOT_PROTECTED_OUTSIDE_WEBROOT\n"); exit(2);
    }
    foreach ($pinned as $sku) {
        $spec = $actual[$sku]; $master = PRODUCTS_DIR . '/' . $spec['master'];
        $problems = [];
        if (!is_file($master) || is_link($master)) {
            $problems[] = 'нет защищённого master ZIP';
        } elseif (hash_file('sha256', $master) !== $spec['sha']) {
            $problems[] = 'SHA-256 мастера не совпадает';
        } else {
            $zip = new ZipArchive();
            if ($zip->open($master) !== true) {
                $problems[] = 'ZIP не открывается';
            } else {
                $names = []; $empty = false; $crcBad = false;
                for ($i=0; $i<$zip->numFiles; $i++) {
                    $entry = $zip->statIndex($i);
                    $names[] = $entry['name'];
                    if ((int)$entry['size'] === 0) $empty = true;
                    if ($zip->getFromIndex($i) === false) $crcBad = true;
                }
                if (!$names || $empty || $crcBad) $problems[] = 'состав, пустые файлы или CRC';
                if (!array_intersect(['00-INSTRUKCIYA.pdf','00-START-HERE.pdf','00-START-HERE.txt'], $names)) {
                    $problems[] = 'нет покупательской инструкции';
                }
                foreach ($service as $svc) if (in_array($svc, $names, true)) $problems[] = 'служебный файл';
                $zip->close();
            }
        }
        if ($problems) {
            $bad++; printf("%-4s ПРОВАЛ  %s\n", $sku, implode('; ', array_unique($problems)));
        } else {
            $checkedPinned++; printf("%-4s ok  защищённый SHA-пинованный master, CRC/ввод\n", $sku);
        }
    }
}
printf(
    "РЕЗУЛЬТАТ: dynamic=%d/%d; paid pinned=%d/%d (%s); ошибок=%d\n",
    $checkedDynamic, count($dynamic), $checkedPinned, count($pinned),
    $synthetic ? 'SYNTHETIC CONTRACT ONLY' : 'REAL PROTECTED MASTER', $bad
);
exit($bad ? 1 : 0);
