<?php
/** P1 immutable editions: isolated HTTP/order fixtures, local payment stub only. */
declare(strict_types=1);
require __DIR__ . '/_test_http.php';
$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-p1-editions-' . getmypid();
$web = $tmp . '/web'; $masters = $tmp . '/masters'; $orders = $tmp . '/orders';
foreach ([$web, $masters, $orders . '/delivery', $tmp . '/kassa'] as $dir) mkdir($dir, 0755, true);
$провалов = 0; $servers = [];
try {
    foreach (['payment.php', 'products-config.php', 'download.php'] as $name) copy($root . '/' . $name, $web . '/' . $name);
    $apiPort = mvb_free_port();
    $router = $tmp . '/kassa/router.php';
    file_put_contents($router, '<?php
$input=json_decode(file_get_contents("php://input"),true);
$id=$input["metadata"]["order_id"] ?? "";
$order=json_decode(file_get_contents(' . var_export($orders . '/', true) . '.$id.".json"),true);
$edition=$order["items"][0]["edition"] ?? [];
$path=' . var_export($orders . '/delivery/', true) . '.($edition["zip"] ?? "");
$ok=($edition["sha256"] ?? "") === @hash_file("sha256",$path);
file_put_contents(' . var_export($tmp . '/api-audit.json', true) . ',json_encode(["pinned_before_api"=>$ok]));
echo json_encode(["id"=>"mock_".$id,"status"=>"pending","confirmation"=>["confirmation_url"=>"https://example.invalid/pay"]]);
');
    $servers[] = mvb_serve($tmp . '/kassa', $apiPort, $router);
    $config = [
        'ORDERS_DIR' => $orders, 'PRODUCTS_DIR' => $masters,
        'SITE_URL' => 'http://127.0.0.1', 'ADMIN_EMAIL' => 'a@example.invalid',
        'YOOKASSA_SHOP_ID' => 'test', 'YOOKASSA_SECRET_KEY' => 'test',
        'YOOKASSA_MODE' => 'test', 'YOOKASSA_API_URL' => 'http://127.0.0.1:' . $apiPort,
    ];
    $php = "<?php\n";
    foreach ($config as $name => $value) { $php .= 'define(' . var_export($name, true) . ',' . var_export($value, true) . ");\n"; define($name, $value); }
    file_put_contents($web . '/config.php', $php);
    require $root . '/products-config.php';
    $source = $masters . '/' . mvb_products()['p1']['dir'];
    mkdir($source, 0755, true);
    file_put_contents($source . '/buyer.txt', 'OLD_EDITION');
    file_put_contents($source . '/removed.txt', 'REMOVE_ME');
    file_put_contents($source . '/MANIFEST.md', 'internal');
    $stamp = time(); touch($source . '/buyer.txt', $stamp);
    $sitePort = mvb_free_port();
    $servers[] = mvb_serve($web, $sitePort);
    $response = mvb_post_json($sitePort, '/payment.php', [
        'items' => [['sku' => 'p1', 'price' => 1, 'edition' => ['zip' => 'forged.zip', 'sha256' => str_repeat('0', 64)]]],
        'phone' => 'test',
    ]);
    $created = json_decode($response['body'], true);
    mvb_check('P1 pinned before order reaches mock payment API; client pin ignored', function () use ($response, $created, $orders, $tmp) {
        mvb_equal($response['code'], 200, $response['body']);
        mvb_true(!empty($created['order_id']), 'missing order');
        $order = json_decode(file_get_contents($orders . '/' . $created['order_id'] . '.json'), true);
        mvb_true(mvb_p1_edition_path($order['items'][0]['edition'] ?? null) !== null, 'invalid server pin');
        mvb_equal($order['items'][0]['price'], mvb_products()['p1']['price'], 'server price');
        mvb_equal(json_decode(file_get_contents($tmp . '/api-audit.json'), true)['pinned_before_api'], true, 'pin absent before API');
    });
    $old = json_decode(file_get_contents($orders . '/' . $created['order_id'] . '.json'), true);
    $oldEdition = $old['items'][0]['edition'];
    $oldPath = mvb_p1_edition_path($oldEdition);
    $oldBytes = file_get_contents($oldPath);
    mvb_check('unchanged content gives the same edition despite mtime change', function () use ($source, $stamp, $oldEdition) {
        touch($source . '/buyer.txt', $stamp - 100);
        mvb_equal(mvb_capture_p1_edition(), $oldEdition, 'unstable content address');
    });
    file_put_contents($source . '/buyer.txt', 'NEW_EDITION'); touch($source . '/buyer.txt', $stamp);
    unlink($source . '/removed.txt');
    $newEdition = mvb_capture_p1_edition();
    mvb_check('same-second edit and removal create new edition; old remains OLD', function () use ($oldEdition, $oldPath, $oldBytes, $newEdition) {
        mvb_true($newEdition !== null && $newEdition['sha256'] !== $oldEdition['sha256'], 'same-second edit missed');
        mvb_equal(file_get_contents($oldPath), $oldBytes, 'old bytes changed');
        $zip = new ZipArchive(); $zip->open(mvb_p1_edition_path($newEdition));
        mvb_equal($zip->getFromName('buyer.txt'), 'NEW_EDITION', 'new content');
        mvb_equal($zip->locateName('removed.txt'), false, 'removed file retained');
        mvb_equal($zip->locateName('MANIFEST.md'), false, 'internal file leaked');
        $zip->close();
        $zip->open($oldPath);
        mvb_equal($zip->getFromName('buyer.txt'), 'OLD_EDITION', 'old content');
        $zip->close();
    });
    $old['status'] = 'paid';
    $result = mvb_prepare_delivery($old);
    mvb_check('pending old order paid after master update still receives OLD', function () use ($old, $result, $oldEdition) {
        mvb_equal($result['missing'], [], 'old delivery denied');
        mvb_equal($old['delivery']['items']['p1'], $oldEdition['zip'], 'old pin changed');
        mvb_equal($old['delivery']['editions']['p1'], $oldEdition, 'delivery SHA missing');
    });
    $issued = $old['delivery'];
    $old['delivery']['downloads'] = 2; $old['delivery']['email_sent_at'] = 'existing';
    mvb_prepare_delivery($old);
    mvb_check('callback replay preserves token, edition, expiry and counter', function () use ($old, $issued) {
        foreach (['token', 'items', 'editions', 'created_at', 'expires_at'] as $key) mvb_equal($old['delivery'][$key], $issued[$key], $key);
        mvb_equal($old['delivery']['downloads'], 2, 'counter');
        mvb_equal($old['delivery']['email_sent_at'], 'existing', 'email flag');
    });
    $oldFile = $orders . '/' . $old['id'] . '.json';
    file_put_contents($oldFile, json_encode($old));
    $get = static function () use ($sitePort, $old): array {
        $ch = curl_init("http://127.0.0.1:{$sitePort}/download.php?o=" . $old['id'] . '&t=' . $old['delivery']['token'] . '&f=p1');
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 3]);
        $body = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
        return [$code, $body];
    };
    mvb_check('HTTP download returns exact pinned ZIP', function () use ($get, $oldBytes) {
        [$code, $body] = $get(); mvb_equal($code, 200, 'download HTTP'); mvb_equal($body, $oldBytes, 'download bytes');
    });
    $counter = json_decode(file_get_contents($oldFile), true)['delivery']['downloads'];
    rename($oldPath, $tmp . '/saved.zip');
    mvb_check('missing pinned ZIP denies; no rebuild, no counter consumption', function () use ($get, $oldFile, $counter, $oldPath) {
        [$code] = $get(); mvb_equal($code, 500, 'missing HTTP');
        mvb_equal(json_decode(file_get_contents($oldFile), true)['delivery']['downloads'], $counter, 'missing consumed');
        mvb_true(!is_file($oldPath), 'rebuilt from current');
    });
    file_put_contents($oldPath, 'CORRUPT');
    mvb_check('corrupt pinned ZIP denies; replay leaves delivery unchanged', function () use ($get, $oldFile, $counter, $oldPath, $old) {
        [$code] = $get(); mvb_equal($code, 500, 'corrupt HTTP');
        mvb_equal(json_decode(file_get_contents($oldFile), true)['delivery']['downloads'], $counter, 'corrupt consumed');
        $copy = $old; $before = $copy; $r = mvb_prepare_delivery($copy);
        mvb_true($r['missing'] !== [], 'corrupt replay accepted');
        mvb_equal($copy, $before, 'corrupt replay altered order');
        mvb_equal(file_get_contents($oldPath), 'CORRUPT', 'corrupt snapshot overwritten');
    });
    unlink($oldPath); rename($tmp . '/saved.zip', $oldPath);
    $legacyZip = mvb_products()['p1']['zip'];
    file_put_contents(DELIVERY_DIR . '/' . $legacyZip, $oldBytes);
    $legacy = ['id' => 'order_20261008_000001_legacy', 'status' => 'paid', 'items' => [['sku' => 'p1']],
        'delivery' => ['token' => 'legacy-token', 'expires_at' => date('c', time()+86400), 'downloads' => 4, 'items' => ['p1' => $legacyZip]]];
    $r = mvb_prepare_delivery($legacy);
    mvb_check('issued legacy delivery preserved without inventing historical pin', function () use ($r, $legacy, $legacyZip, $oldBytes) {
        mvb_equal($r['missing'], [], 'legacy rejected');
        mvb_equal($legacy['delivery']['items']['p1'], $legacyZip, 'legacy name changed');
        mvb_equal($legacy['delivery']['token'], 'legacy-token', 'legacy token changed');
        mvb_equal($legacy['delivery']['downloads'], 4, 'legacy counter changed');
        mvb_true(!isset($legacy['items'][0]['edition']), 'invented legacy item pin');
        mvb_true(empty($legacy['delivery']['editions']), 'invented legacy delivery pin');
        mvb_equal(file_get_contents(DELIVERY_DIR . '/' . $legacyZip), $oldBytes, 'legacy ZIP replaced');
    });
    mvb_check('non-P1 issued cache still rebuilds after master update; unrelated edition metadata ignored', function () use ($masters, $orders, $sitePort) {
        $dir = $masters . '/' . mvb_products()['p3']['dir'];
        mkdir($dir, 0755, true);
        file_put_contents($dir . '/buyer.txt', 'P3_OLD');
        $path = mvb_build_product_zip('p3');
        $order = ['id' => 'order_20261008_000003_other', 'status' => 'paid',
            'items' => [['sku' => 'p3', 'edition' => ['zip' => 'unrelated', 'sha256' => 'unrelated']]],
            'delivery' => ['token' => 'p3-token', 'items' => ['p3' => basename($path)],
                'editions' => ['p3' => ['zip' => 'unrelated', 'sha256' => 'unrelated']]]];
        $past = time() - 3600;
        touch($path, $past);
        file_put_contents($dir . '/buyer.txt', 'P3_NEW');
        touch($dir . '/buyer.txt', $past + 60);
        clearstatcache();
        $result = mvb_prepare_delivery($order);
        mvb_equal($result['missing'], [], 'non-P1 metadata denied callback');
        $zip = new ZipArchive();
        $zip->open($path);
        mvb_equal($zip->getFromName('buyer.txt'), 'P3_NEW', 'non-P1 rebuild behavior changed');
        $zip->close();
        mvb_equal($order['delivery']['token'], 'p3-token', 'non-P1 token changed');
        file_put_contents($orders . '/' . $order['id'] . '.json', json_encode($order));
        $ch = curl_init("http://127.0.0.1:{$sitePort}/download.php?o=" . $order['id'] . '&t=p3-token&f=p3');
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 3]);
        $body = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
        mvb_equal($code, 200, 'non-P1 metadata denied download');
        mvb_equal($body, file_get_contents($path), 'non-P1 download bytes');
    });
    $unissued = ['id' => 'order_20261008_000002_legacy', 'status' => 'paid', 'items' => [['sku' => 'p1']]];
    $before = $unissued; $r = mvb_prepare_delivery($unissued);
    mvb_check('unissued legacy without original edition fails closed', function () use ($r, $unissued, $before) {
        mvb_true($r['missing'] !== [], 'unissued legacy accepted'); mvb_equal($unissued, $before, 'legacy changed');
    });
    $lock = fopen(DELIVERY_DIR . '/.p1-edition.lock', 'c'); flock($lock, LOCK_EX);
    mvb_check('concurrent writer fails promptly without partial edition', function () {
        mvb_equal(mvb_capture_p1_edition(), null, 'writer bypassed lock');
        mvb_equal(glob(DELIVERY_DIR . '/.p1-stage-*'), [], 'partial stage leaked');
    });
    mvb_check('busy snapshot denies payment before creating order or calling API', function () use ($sitePort, $orders, $tmp) {
        $ordersBefore = glob($orders . '/order_*.json');
        $auditBefore = file_get_contents($tmp . '/api-audit.json');
        $r = mvb_post_json($sitePort, '/payment.php', ['items' => [['sku' => 'p1']], 'phone' => 'test']);
        mvb_equal($r['code'], 503, 'busy payment HTTP');
        mvb_equal(glob($orders . '/order_*.json'), $ordersBefore, 'busy payment created order');
        mvb_equal(file_get_contents($tmp . '/api-audit.json'), $auditBefore, 'busy payment called API');
    });
    flock($lock, LOCK_UN); fclose($lock);
    $newPath = mvb_p1_edition_path($newEdition);
    $newBytes = file_get_contents($newPath);
    file_put_contents($newPath, 'CORRUPT_CURRENT_SNAPSHOT');
    mvb_check('capture fails closed when an existing content-addressed snapshot is corrupt', function () use ($newPath) {
        mvb_equal(mvb_capture_p1_edition(), null, 'corrupt existing snapshot replaced');
        mvb_equal(file_get_contents($newPath), 'CORRUPT_CURRENT_SNAPSHOT', 'corruption overwritten');
    });
    file_put_contents($newPath, $newBytes);
} finally {
    foreach ($servers as $server) mvb_kill($server);
    $clean = static function (string $dir) use (&$clean): void {
        foreach (new DirectoryIterator($dir) as $f) {
            if ($f->isDot()) continue; $p=$f->getPathname();
            $f->isDir() ? $clean($p) : unlink($p);
        }
        rmdir($dir);
    };
    $clean($tmp);
}
mvb_finish();
