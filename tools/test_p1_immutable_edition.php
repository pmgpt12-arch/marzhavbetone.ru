<?php
/**
 * P1 SHA-pinned edition: synthetic master, isolated HTTP, local payment stub.
 * Only the ONE hardcoded P1 master SHA in a TEMPORARY PHP COPY is replaced.
 * Live files, orders, buyer data, payment provider and paid ZIPs are untouched.
 */
declare(strict_types=1);
require __DIR__ . '/_test_http.php';

$root = dirname(__DIR__);
$tmp = sys_get_temp_dir() . '/mvb-p1-pinned-' . bin2hex(random_bytes(6));
$web = $tmp . '/web';
$masters = $tmp . '/masters';
$orders = $tmp . '/orders';
foreach ([$web, $masters, $orders . '/delivery', $tmp . '/kassa'] as $dir) {
    if (!is_dir($dir) && !mkdir($dir, 0755, true)) throw new RuntimeException('TEMP_DIRECTORY_FAILED');
}
$провалов = 0;
$servers = [];
try {
    foreach (['payment.php', 'products-config.php', 'download.php'] as $name) {
        if (!copy($root . '/' . $name, $web . '/' . $name)) throw new RuntimeException('COPY_FAILED_' . $name);
    }
    $sourceSha = '12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934';
    mvb_true(hash_file('sha256', $root . '/products-config.php') === $sourceSha,
        'Test requires exact production-aligned PHP source; no unreviewed variant');

    // Create a non-commercial test ZIP. Replace ONLY the pinned P1 SHA in the
    // disposable runtime copy; all delivery logic remains exactly as written.
    $master = $masters . '/P1-v1-current.zip';
    $zip = new ZipArchive();
    mvb_true($zip->open($master, ZipArchive::CREATE | ZipArchive::OVERWRITE) === true, 'ZIP_CREATE');
    mvb_true($zip->addFromString('buyer.txt', 'SYNTHETIC_PINNED_V1'), 'ZIP_ENTRY');
    mvb_true($zip->addFromString('00-INSTRUKCIYA.pdf', 'SYNTHETIC_FIXTURE_NOT_FOR_DISTRIBUTION'), 'ZIP_ENTRY_INSTRUCTION');
    mvb_true($zip->close(), 'ZIP_CLOSE');
    $masterBytes = file_get_contents($master);
    $fixtureSha = hash('sha256', $masterBytes);
    $realSha = '99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada';
    $copied = file_get_contents($web . '/products-config.php');
    mvb_true(substr_count($copied, $realSha) === 1, 'P1_SHA_SOURCE_MUST_BE_UNIQUE');
    mvb_true(substr_count($copied, '/P1-v1-current.zip') === 1, 'P1_MASTER_PATH_UNIQUE');
    $copied = str_replace($realSha, $fixtureSha, $copied);
    mvb_true(file_put_contents($web . '/products-config.php', $copied) === strlen($copied), 'TEMP_PHP_WRITE');
    mvb_true(substr_count($copied, $fixtureSha) === 1, 'ONLY_PINNED_SHA_INJECTED');

    $apiPort = mvb_free_port();
    $router = $tmp . '/kassa/router.php';
    $apiScript = '<?php
$input = json_decode(file_get_contents("php://input"), true);
$id = $input["metadata"]["order_id"] ?? "";
$order = json_decode(file_get_contents(' . var_export($orders . '/', true) . ' . $id . ".json"), true);
$edition = $order["items"][0]["edition"] ?? [];
$path = ' . var_export($orders . '/delivery/', true) . ' . ($edition["zip"] ?? "");
$ok = ($edition["sha256"] ?? "") === @hash_file("sha256", $path);
file_put_contents(' . var_export($tmp . '/api-audit.json', true) . ', json_encode(["pinned_before_api" => $ok, "price" => $order["total"] ?? 0]));
if (!$ok) { http_response_code(500); echo "{}"; return true; }
echo json_encode(["id" => "mock_" . $id, "status" => "pending",
    "confirmation" => ["confirmation_url" => "https://example.invalid/pay"]]);
return true;
';
    mvb_true(file_put_contents($router, $apiScript) === strlen($apiScript), 'MOCK_API_ROUTER');
    $servers[] = mvb_serve($tmp . '/kassa', $apiPort, $router);

    $config = [
        'ORDERS_DIR' => $orders, 'PRODUCTS_DIR' => $masters,
        'SITE_URL' => 'http://127.0.0.1', 'ADMIN_EMAIL' => 'a@example.invalid',
        'YOOKASSA_SHOP_ID' => 'test', 'YOOKASSA_SECRET_KEY' => 'test',
        'YOOKASSA_MODE' => 'test', 'YOOKASSA_API_URL' => 'http://127.0.0.1:' . $apiPort,
        'DELIVERY_TTL_SECONDS' => 3600,
    ];
    $php = "<?php\n";
    foreach ($config as $name => $value) {
        $php .= 'define(' . var_export($name, true) . ',' . var_export($value, true) . ");\n";
        define($name, $value);
    }
    file_put_contents($web . '/config.php', $php);
    require $web . '/products-config.php';

    $expected = ['zip' => 'p1-' . $fixtureSha . '.zip', 'sha256' => $fixtureSha];
    $source = $masters . '/' . mvb_products()['p1']['dir'];
    mkdir($source, 0755, true);
    file_put_contents($source . '/buyer.txt', 'UNPACKED_OLD_CONTENT');
    $sitePort = mvb_free_port();
    $servers[] = mvb_serve($web, $sitePort);

    // 1. No owner-approved pinned master: payment stops before any order/API call.
    rename($master, $tmp . '/saved-master.zip');
    $badPayment = mvb_post_json($sitePort, '/payment.php', ['items' => [['sku' => 'p1']], 'phone' => 'test']);
    mvb_check('missing pinned master denies payment without order/API', function () use ($badPayment, $orders, $tmp) {
        mvb_equal($badPayment['code'], 503, 'missing-master HTTP');
        mvb_equal(glob($orders . '/order_*.json'), [], 'created order with no master');
        mvb_true(!is_file($tmp . '/api-audit.json'), 'called API without master');
    });
    rename($tmp . '/saved-master.zip', $master);

    // 2. Exact master is pinned before the mocked payment API is called.
    $response = mvb_post_json($sitePort, '/payment.php', [
        'items' => [['sku' => 'p1', 'price' => 1,
            'edition' => ['zip' => 'forged.zip', 'sha256' => str_repeat('0', 64)]]],
        'phone' => 'test',
    ]);
    $created = json_decode($response['body'], true);
    mvb_check('server-created P1 pin precedes payment and client forgery is ignored',
        function () use ($response, $created, $orders, $tmp, $expected) {
            mvb_equal($response['code'], 200, 'mock payment HTTP');
            mvb_true(!empty($created['order_id']), 'order id');
            $order = json_decode(file_get_contents($orders . '/' . $created['order_id'] . '.json'), true);
            mvb_equal($order['items'][0]['edition'], $expected, 'server edition');
            mvb_equal($order['items'][0]['price'], 2990000, 'server price');
            mvb_equal(json_decode(file_get_contents($tmp . '/api-audit.json'), true),
                ['pinned_before_api' => true, 'price' => 2990000], 'API audit');
            mvb_true(mvb_p1_edition_path($expected) !== null, 'valid delivered edition');
        });
    mvb_true(!empty($created['order_id']), 'PAYMENT_FIXTURE_STOP');
    $orderFile = $orders . '/' . $created['order_id'] . '.json';
    $order = json_decode(file_get_contents($orderFile), true);
    $snapshot = mvb_p1_edition_path($expected);
    mvb_true(is_string($snapshot), 'SNAPSHOT_PATH');
    $previousBytes = file_get_contents($snapshot);

    // 3. Unpacked sources may change, but the published immutable edition cannot.
    file_put_contents($source . '/buyer.txt', 'UNPACKED_REVISED_CONTENT');
    file_put_contents($source . '/removed.txt', 'ARBITRARY_NEW_FILE');
    mvb_check('unpacked source changes do not change the pinned SHA', function () use ($expected, $snapshot, $previousBytes) {
        mvb_equal(mvb_capture_p1_edition(), $expected, 'pin changed after unpacked edit');
        mvb_equal(file_get_contents($snapshot), $previousBytes, 'pinned bytes changed');
    });

    // 4. Paid order delivery and replay must not change token, edition or counters.
    $order['status'] = 'paid';
    $delivery = mvb_prepare_delivery($order);
    mvb_check('paid P1 receives pinned edition and exactly one complete link', function () use ($delivery, $order, $expected) {
        mvb_equal($delivery['missing'], [], 'delivery missing');
        mvb_equal(count($delivery['links']), 1, 'link count');
        mvb_equal($order['delivery']['items']['p1'], $expected['zip'], 'selected ZIP');
        mvb_equal($order['delivery']['editions']['p1'], $expected, 'delivery pin');
        mvb_true(!empty($order['delivery']['token']), 'delivery token absent');
    });
    $before = $order['delivery'];
    $order['delivery']['downloads'] = 2;
    $order['delivery']['email_sent_at'] = 'previously_sent';
    mvb_prepare_delivery($order);
    mvb_check('callback replay retains edition, token, expiration and counter', function () use ($order, $before) {
        foreach (['token', 'items', 'editions', 'created_at', 'expires_at'] as $key) {
            mvb_equal($order['delivery'][$key], $before[$key], $key);
        }
        mvb_equal($order['delivery']['downloads'], 2, 'download counter');
        mvb_equal($order['delivery']['email_sent_at'], 'previously_sent', 'mail de-dup marker');
    });
    file_put_contents($orderFile, json_encode($order));

    $get = static function () use ($sitePort, $order): array {
        $ch = curl_init("http://127.0.0.1:{$sitePort}/download.php?o=" . $order['id']
            . '&t=' . $order['delivery']['token'] . '&f=p1');
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 4]);
        $bytes = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        return [$code, (string)$bytes];
    };
    mvb_check('authenticated HTTP download returns exact pinned ZIP bytes', function () use ($get, $previousBytes) {
        [$code, $bytes] = $get();
        mvb_equal($code, 200, 'HTTP status');
        mvb_equal($bytes, $previousBytes, 'ZIP bytes');
    });
    $counter = json_decode(file_get_contents($orderFile), true)['delivery']['downloads'];

    // 5. Missing/corrupt snapshot denies issued buyer and does not consume a download.
    rename($snapshot, $tmp . '/saved-edition.zip');
    mvb_check('missing issued snapshot denies without consuming download', function () use ($get, $orderFile, $counter, $snapshot) {
        mvb_equal($get()[0], 500, 'missing snapshot HTTP');
        mvb_equal(json_decode(file_get_contents($orderFile), true)['delivery']['downloads'], $counter, 'missing counter');
        mvb_true(!is_file($snapshot), 'unexpected implicit rebuild');
    });
    file_put_contents($snapshot, 'CORRUPT');
    mvb_check('corrupt issued snapshot denies and leaves order unchanged', function () use ($get, $orderFile, $counter, $snapshot, $order) {
        mvb_equal($get()[0], 500, 'corrupt snapshot HTTP');
        mvb_equal(json_decode(file_get_contents($orderFile), true)['delivery']['downloads'], $counter, 'corrupt counter');
        $copy = $order;
        mvb_true(mvb_prepare_delivery($copy)['missing'] !== [], 'corrupt replay permitted');
        mvb_equal($copy, $order, 'corrupt replay mutated paid order');
        mvb_equal(file_get_contents($snapshot), 'CORRUPT', 'replay overwrote corrupt snapshot');
    });
    unlink($snapshot);
    rename($tmp . '/saved-edition.zip', $snapshot);

    // 6. A corrupt master prevents all NEW payments. Existing issued ZIP still works.
    file_put_contents($master, 'WRONG_SHA');
    $countBefore = count(glob($orders . '/order_*.json'));
    $auditBefore = file_get_contents($tmp . '/api-audit.json');
    $blocked = mvb_post_json($sitePort, '/payment.php', ['items' => [['sku' => 'p1']], 'phone' => 'test']);
    mvb_check('corrupt master fails closed before creating any new order', function () use ($blocked, $orders, $countBefore, $tmp, $auditBefore, $get, $previousBytes) {
        mvb_equal($blocked['code'], 503, 'wrong SHA payment HTTP');
        mvb_equal(count(glob($orders . '/order_*.json')), $countBefore, 'new order created');
        mvb_equal(file_get_contents($tmp . '/api-audit.json'), $auditBefore, 'API contacted');
        mvb_equal($get()[1], $previousBytes, 'historical issued ZIP lost');
    });
    file_put_contents($master, $masterBytes);

    // 7. No partial delivery when another pinned paid SKU's master is absent.
    $mixed = ['id' => 'order_20261008_000001_mixed','status' => 'paid',
        'items' => [['sku' => 'p1', 'edition' => $expected], ['sku' => 'p2']]];
    $mixedBefore = $mixed;
    $mixedResult = mvb_prepare_delivery($mixed);
    mvb_check('mixed order is atomic when P2 master is missing', function () use ($mixedResult, $mixed, $mixedBefore) {
        mvb_true(count($mixedResult['missing']) === 1, 'missing P2 not detected');
        mvb_equal($mixedResult['links'], [], 'partial delivery was issued');
        mvb_equal($mixed, $mixedBefore, 'partial delivery mutated order');
    });

    // 8. Already-issued legacy link survives without inventing an edition.
    $legacyName = mvb_products()['p1']['zip'];
    file_put_contents(DELIVERY_DIR . '/' . $legacyName, $previousBytes);
    $legacy = ['id'=>'order_20261008_000002_legacy','status'=>'paid',
        'items'=>[['sku'=>'p1']], 'delivery'=>[
            'token'=>'legacy-token','downloads'=>4,
            'expires_at'=>date('c',time()+3600),'items'=>['p1'=>$legacyName]]];
    $legacyResult = mvb_prepare_delivery($legacy);
    mvb_check('existing legacy buyer delivery preserved', function () use ($legacyResult, $legacy, $legacyName) {
        mvb_equal($legacyResult['missing'], [], 'legacy delivery denied');
        mvb_equal($legacy['delivery']['items']['p1'], $legacyName, 'legacy ZIP name');
        mvb_equal($legacy['delivery']['token'], 'legacy-token', 'legacy token');
        mvb_equal($legacy['delivery']['downloads'], 4, 'legacy counter');
        mvb_true(empty($legacy['delivery']['editions']), 'historical pin invented');
    });
    $unissued = ['id'=>'order_20261008_000003_unissued','status'=>'paid','items'=>[['sku'=>'p1']]];
    $unchanged = $unissued;
    mvb_check('unissued legacy order without original edition fails closed', function () use (&$unissued, $unchanged) {
        mvb_true(mvb_prepare_delivery($unissued)['missing'] !== [], 'unissued legacy allowed');
        mvb_equal($unissued, $unchanged, 'unissued legacy mutated');
    });

    // A valid master may safely reconstruct a damaged cache; its SHA must match.
    file_put_contents($snapshot, 'CORRUPT_CACHED');
    mvb_check('valid master repairs only exact SHA-addressed cached ZIP', function () use ($expected, $snapshot, $previousBytes) {
        mvb_equal(mvb_capture_p1_edition(), $expected, 'cache not repaired');
        mvb_equal(file_get_contents($snapshot), $previousBytes, 'repair byte mismatch');
    });
} finally {
    foreach ($servers as $server) mvb_kill($server);
    $clean = static function (string $dir) use (&$clean): void {
        if (!is_dir($dir)) return;
        foreach (new DirectoryIterator($dir) as $f) {
            if ($f->isDot()) continue;
            $path = $f->getPathname();
            $f->isDir() && !$f->isLink() ? $clean($path) : unlink($path);
        }
        rmdir($dir);
    };
    $clean($tmp);
}
mvb_finish();
