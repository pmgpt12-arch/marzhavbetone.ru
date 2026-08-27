<?php
/**
 * Сборщик событий на хостинге. Запуск: php tools/test_funnel_outbox.php
 *
 * ЗАЧЕМ СБОРЩИК. Прежде событие уходило из PHP прямо в Control Plane на
 * домашней машине. Домашняя машина спит, и тогда событие теряется навсегда:
 * повторить его некому, посетитель уже ушёл. Открывать домашнюю машину
 * наружу — цена, которой платить не за что. Поэтому событие ложится строкой
 * в файл рядом с сайтом, а домашняя сторона забирает файл сама, когда
 * проснётся.
 *
 * ГЛАВНОЕ, ЧТО ЗДЕСЬ ПРОВЕРЯЕТСЯ, И ПОЧЕМУ ИМЕННО ЭТО:
 *
 * 1. Поток событий недоступен из браузера. Это не «желательно»: в строках
 *    лежат анонимные идентификаторы посетителей, и открытый каталог сделал
 *    бы их общим достоянием. Проверка ходит по HTTP, а не рассуждает о
 *    правах.
 * 2. Отказ сборщика не меняет ответ человеку. Наблюдаемость не становится
 *    условием работы коммерческого контура — ни при отсутствии каталога, ни
 *    при отсутствии прав, ни при полном диске.
 * 3. Браузер не может подделать покупку и выдачу. Перечень типов закрытый, и
 *    сборщик его не ослабляет.
 */
declare(strict_types=1);

$ROOT = dirname(__DIR__);
$провалов = 0;

require_once __DIR__ . '/_test_http.php';

echo "сборщик событий на хостинге\n";

/** Свежий каталог сборщика под один сценарий. */
function outbox_tmp(string $метка): string
{
    $путь = sys_get_temp_dir() . '/mvb_outbox_' . getmypid() . '_' . $метка;
    if (is_dir($путь)) {
        foreach ((array)glob($путь . '/*') as $файл) { @unlink($файл); }
        @rmdir($путь);
    }
    return $путь;
}

/**
 * Дождаться, пока в сборщике окажется столько строк.
 *
 * Ожидание здесь не «на всякий случай»: запись в сборщик происходит ПОСЛЕ
 * ответа человеку — в этом весь порядок. Значит между кодом 204 и строкой в
 * файле есть промежуток, и проверка, читающая файл сразу, ловит гонку с
 * собственным требованием. Ждём до полусекунды и меряем, что дождались.
 */
function outbox_wait(string $каталог, int $сколько): array
{
    for ($i = 0; $i < 50; $i++) {
        $строки = outbox_lines($каталог);
        if (count($строки) >= $сколько) { return $строки; }
        usleep(10000);
    }
    return outbox_lines($каталог);
}

/** Прочитать все строки сборщика как массивы. */
function outbox_lines(string $каталог): array
{
    $строки = [];
    foreach ((array)glob($каталог . '/*.pending.jsonl') as $файл) {
        foreach (explode("\n", (string)file_get_contents($файл)) as $с) {
            if (trim($с) !== '') { $строки[] = json_decode($с, true); }
        }
    }
    return $строки;
}

/**
 * Прогнать сценарий на встроенном сервере сайта с заданным каталогом сборщика.
 * Возвращает [порт, каталог]. Сервер гасится вызывающим.
 */
function outbox_serve(string $ROOT, string $каталог): array
{
    putenv("MVB_FUNNEL_OUTBOX={$каталог}");
    $порт = mvb_free_port();
    $сервер = mvb_serve($ROOT, $порт);
    return [$порт, $сервер];
}

/* ── 1. Браузер → сборщик ────────────────────────────────────────────── */

mvb_check('браузерные события ложатся строками в сборщик', function () use ($ROOT) {
    $каталог = outbox_tmp('browser');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        $аноним = '11111111-2222-4333-8444-555555555555';
        $сессия = '99999999-8888-4777-8666-555555555555';
        mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.session_started',
            'anonymous_id' => $аноним, 'session_id' => $сессия,
            'source' => 'direct',
        ]);
        mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.content_viewed',
            'anonymous_id' => $аноним, 'session_id' => $сессия,
            'content_id' => 'articles/kс-2', 'source' => 'direct',
        ]);
        $строки = outbox_wait($каталог, 2);
        mvb_equal(count($строки), 2, 'строк в сборщике');
        mvb_equal($строки[0]['event_type'], 'funnel.session_started', 'первое событие');
        mvb_equal($строки[1]['event_type'], 'funnel.content_viewed', 'второе событие');
        // §32: один посетитель, одна сессия, но события — разные.
        mvb_equal($строки[0]['anonymous_id'], $аноним, 'аноним первого');
        mvb_equal($строки[1]['anonymous_id'], $аноним, 'аноним второго');
        mvb_equal($строки[0]['session_id'], $строки[1]['session_id'], 'сессия одна');
        mvb_true($строки[0]['event_uuid'] !== $строки[1]['event_uuid'],
                 'event_uuid обязан различаться, иначе приёмник схлопнет события');
    } finally { mvb_kill($сервер); }
});

mvb_check('строка сборщика — канонный конверт целиком', function () use ($ROOT) {
    $каталог = outbox_tmp('envelope');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.content_viewed',
            'anonymous_id' => '11111111-2222-4333-8444-555555555555',
            'content_id' => 'products/t1',
        ]);
        $строки = outbox_wait($каталог, 1);
        mvb_equal(count($строки), 1, 'строк');
        foreach (['event_uuid', 'event_type', 'occurred_at', 'anonymous_id',
                  'session_id', 'content_id', 'pain_id', 'stage_id', 'source',
                  'utm', 'sku', 'amount_kopeck'] as $поле) {
            mvb_true(array_key_exists($поле, $строки[0]),
                     "в конверте нет поля {$поле}");
        }
        // Незаполненное — null, а не отсутствие: «не знаем» и «нет» это разное.
        mvb_equal($строки[0]['sku'], null, 'sku на просмотре статьи');
        mvb_equal($строки[0]['amount_kopeck'], null, 'сумма на просмотре статьи');
    } finally { mvb_kill($сервер); }
});

mvb_check('одно событие — одна строка, файл не переписывается', function () use ($ROOT) {
    $каталог = outbox_tmp('append');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        for ($i = 0; $i < 12; $i++) {
            mvb_post_json($порт, '/event.php', [
                'event_type' => 'funnel.content_viewed',
                'anonymous_id' => '11111111-2222-4333-8444-555555555555',
                'content_id' => "articles/{$i}",
            ]);
        }
        outbox_wait($каталог, 12);
        $файлы = (array)glob($каталог . '/*.pending.jsonl');
        mvb_equal(count($файлы), 1, 'файл суток один');
        $сырое = (string)file_get_contents($файлы[0]);
        mvb_equal(substr_count($сырое, "\n"), 12, 'переводов строки');
        mvb_equal(count(outbox_lines($каталог)), 12, 'разобранных строк');
    } finally { mvb_kill($сервер); }
});

/* ── 2. Выдача материала → сборщик ───────────────────────────────────── */

mvb_check('после выдачи материала пишется magnet_delivered', function () use ($ROOT) {
    $каталог = outbox_tmp('lead');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        $ответ = mvb_post_raw($порт, '/lead.php',
            http_build_query(['key' => 'checklist', 'name' => 'Иван',
                              'contact' => 'a@b.ru', 'consent' => 'yes',
                              'source' => 'test',
                              'anonymous_id' => '11111111-2222-4333-8444-555555555555']),
            'application/x-www-form-urlencoded');
        mvb_equal($ответ['code'], 200, 'код ответа выдачи');
        $строки = outbox_wait($каталог, 1);
        mvb_equal(count($строки), 1, 'строк в сборщике');
        mvb_equal($строки[0]['event_type'], 'funnel.magnet_delivered', 'тип события');
        mvb_equal($строки[0]['magnet_id'], 'checklist', 'ключ материала');
    } finally { mvb_kill($сервер); }
});

mvb_check('в потоке нет ни почты, ни имени, ни телефона', function () use ($ROOT) {
    $каталог = outbox_tmp('pii');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        mvb_post_raw($порт, '/lead.php',
            http_build_query(['key' => 'checklist', 'contact' => 'petrov@example.com',
                              'name' => 'Пётр', 'phone' => '+79161234567',
                              'consent' => 'yes', 'source' => 'test']),
            'application/x-www-form-urlencoded');
        mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.content_viewed',
            'email' => 'petrov@example.com', 'phone' => '+79161234567',
            'content_id' => 'articles/x',
        ]);
        outbox_wait($каталог, 1);
        $сырое = '';
        foreach ((array)glob($каталог . '/*.jsonl') as $файл) {
            $сырое .= (string)file_get_contents($файл);
        }
        foreach (['petrov@example.com', '79161234567', 'Пётр', 'phone', 'email']
                 as $след) {
            mvb_true(mb_strpos($сырое, $след) === false,
                     "в потоке найден след персональных данных: {$след}");
        }
    } finally { mvb_kill($сервер); }
});

/* ── 3. Граница доверия ──────────────────────────────────────────────── */

mvb_check('браузер не может подделать покупку и выдачу', function () use ($ROOT) {
    $каталог = outbox_tmp('forge');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        foreach (['funnel.purchase_completed', 'funnel.product_delivered',
                  'funnel.magnet_delivered'] as $тип) {
            mvb_post_json($порт, '/event.php', [
                'event_type' => $тип, 'sku' => 't1', 'amount_kopeck' => 1,
                'anonymous_id' => '11111111-2222-4333-8444-555555555555',
            ]);
        }
        usleep(300000);   // дать сборщику время записать, если он согласится
        mvb_equal(count(outbox_lines($каталог)), 0,
                  'ни одно подделанное событие не должно доехать до сборщика');
    } finally { mvb_kill($сервер); }
});

mvb_check('поток недоступен по HTTP', function () use ($ROOT) {
    // §35, и проверка обязана уметь падать. Первая её редакция клала в файл
    // кириллическую метку и искала её в ответе — а json_encode без
    // JSON_UNESCAPED_UNICODE превращает кириллицу в \uXXXX, и метка не
    // нашлась бы никогда, даже когда сервер отдаёт файл целиком. Метка
    // теперь латинская и кладётся сырой, а к поиску добавлен код ответа.
    $каталог = outbox_tmp('web');
    @mkdir($каталог, 0700, true);
    $метка = 'OUTBOX-LEAK-CANARY';
    file_put_contents($каталог . '/2026-08-27.pending.jsonl',
                      '{"event_uuid":"' . $метка . '"}' . "\n");
    putenv("MVB_FUNNEL_OUTBOX={$каталог}");

    $порт = mvb_free_port();
    $сервер = mvb_serve($ROOT, $порт);
    try {
        // Каталог лежит вне корня сайта, поэтому адреса к нему нет вовсе.
        // Проверяются пути, которыми к нему пробуют пройти: прямой,
        // подъёмом и подъёмом в кодировке — последний потому, что сервер
        // раскодирует %2e%2e раньше, чем сравнит с корнем.
        $относительный = ltrim(str_replace(realpath($ROOT), '',
                                           (string)realpath($каталог)), '/');
        $пути = [
            '/' . basename($каталог) . '/2026-08-27.pending.jsonl',
            '/../' . basename(dirname($каталог)) . '/' . basename($каталог)
                   . '/2026-08-27.pending.jsonl',
            '/%2e%2e/' . basename($каталог) . '/2026-08-27.pending.jsonl',
            '/' . $относительный . '/2026-08-27.pending.jsonl',
        ];
        foreach ($пути as $путь) {
            $ch = curl_init("http://127.0.0.1:{$порт}{$путь}");
            curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true,
                                    CURLOPT_TIMEOUT => 10]);
            $тело = (string)curl_exec($ch);
            $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            mvb_true(strpos($тело, $метка) === false,
                     "поток событий отдан по HTTP: {$путь} (код {$код})");
            // Кода 403/404 здесь не требуем, и это не послабление. Встроенный
            // сервер PHP на несуществующий путь идёт вверх по дереву за
            // index.html и отвечает 200 страницей сайта — то есть 200 тут
            // свойство оснастки, а не сервера хостинга. Требование «403 или
            // 404» осталось, но проверяется на боевом Apache шагом 3
            // процедуры включения, а не здесь. Проверяемое здесь сильнее и от
            // оснастки не зависит: ответ не должен быть потоком событий.
            mvb_true(strpos(ltrim($тело), '{') !== 0,
                     "по адресу {$путь} отдан JSON — похоже на поток событий");
        }
    } finally {
        mvb_kill($сервер);
        foreach ((array)glob($каталог . '/*') as $ф) { @unlink($ф); }
        @rmdir($каталог);
    }
});

mvb_check('проверка недоступности умеет падать', function () use ($ROOT) {
    // Оснастка проверяется на себе: положить файл внутрь корня сайта и
    // убедиться, что встроенный сервер его ОТДАЁТ. Без этого предыдущая
    // проверка доказывала бы только то, что она ничего не проверяет.
    $внутри = $ROOT . '/mvb-outbox-selfcheck';
    @mkdir($внутри, 0700, true);
    $метка = 'OUTBOX-LEAK-CANARY';
    file_put_contents($внутри . '/x.jsonl', '{"event_uuid":"' . $метка . '"}' . "\n");
    $порт = mvb_free_port();
    $сервер = mvb_serve($ROOT, $порт);
    try {
        $ch = curl_init("http://127.0.0.1:{$порт}/mvb-outbox-selfcheck/x.jsonl");
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true,
                                CURLOPT_TIMEOUT => 10]);
        $тело = (string)curl_exec($ch);
        curl_close($ch);
        mvb_true(strpos($тело, $метка) !== false,
                 'сервер не отдал файл изнутри корня — значит проверка '
                 . 'недоступности прошла бы и на дырявом сборщике');
    } finally {
        mvb_kill($сервер);
        foreach ((array)glob($внутри . '/*') as $ф) { @unlink($ф); }
        @rmdir($внутри);
    }
});

mvb_check('сборщик отказывается писать в открытое веб-сервером место', function () use ($ROOT) {
    require_once $ROOT . '/mvb_funnel.php';
    $открытый = $ROOT . '/mvb-outbox-inside';
    putenv("MVB_FUNNEL_OUTBOX={$открытый}");
    // Корень документов = корень сайта: ровно то, что видит веб-сервер.
    $_SERVER['DOCUMENT_ROOT'] = $ROOT;
    try {
        $записал = mvb_funnel_event('funnel.content_viewed',
                                    ['content_id' => 'articles/x']);
        mvb_equal($записал, false,
                  'запись внутрь корня сайта обязана быть отказом, а не удачей');
        mvb_equal(glob($открытый . '/*.jsonl') ?: [], [],
                  'внутри корня сайта не должно появиться ни одного файла');
    } finally {
        unset($_SERVER['DOCUMENT_ROOT']);
        foreach ((array)glob($открытый . '/*') as $ф) { @unlink($ф); }
        @rmdir($открытый);
    }
});

/* ── 4. Отказ сборщика не трогает человека ───────────────────────────── */

mvb_check('материал выдаётся, когда сборщик писать не может', function () use ($ROOT) {
    // Каталог существует и закрыт на запись: самый частый отказ на хостинге.
    $закрытый = sys_get_temp_dir() . '/mvb_outbox_ro_' . getmypid();
    @mkdir($закрытый, 0500, true);
    @chmod($закрытый, 0500);
    [$порт, $сервер] = outbox_serve($ROOT, $закрытый);
    try {
        $ответ = mvb_post_raw($порт, '/lead.php',
            http_build_query(['key' => 'checklist', 'name' => 'Иван',
                              'contact' => 'a@b.ru', 'consent' => 'yes',
                              'source' => 'test']),
            'application/x-www-form-urlencoded');
        mvb_equal($ответ['code'], 200, 'код ответа при неработающем сборщике');
        $тело = json_decode($ответ['body'], true);
        mvb_true(is_array($тело) && ($тело['ok'] ?? false),
                 'человек обязан получить материал: ' . $ответ['body']);
    } finally {
        mvb_kill($сервер);
        @chmod($закрытый, 0700);
        @rmdir($закрытый);
    }
});

mvb_check('сайт работает, когда домашней машины нет вовсе', function () use ($ROOT) {
    // Приёмный контур не поднимается ни в одном сценарии этого файла: в этом
    // и смысл варианта C. Проверка называет это явно — событие копится
    // локально, ответ человеку не меняется, сети никто не касается.
    $каталог = outbox_tmp('offline');
    putenv('MVB_FUNNEL_ENDPOINT=');
    putenv('MVB_FUNNEL_TOKEN=');
    [$порт, $сервер] = outbox_serve($ROOT, $каталог);
    try {
        $ответ = mvb_post_raw($порт, '/lead.php',
            http_build_query(['key' => 'checklist', 'name' => 'Иван',
                              'contact' => 'a@b.ru', 'consent' => 'yes',
                              'source' => 'test']),
            'application/x-www-form-urlencoded');
        mvb_equal($ответ['code'], 200, 'код ответа');
        mvb_true($ответ['time'] < 3.0,
                 'ответ не должен ждать сети: ' . $ответ['time'] . ' с');
        mvb_equal(count(outbox_wait($каталог, 1)), 1, 'событие всё равно записано');
    } finally { mvb_kill($сервер); }
});

/* ── 5. Проверка конверта на транспортном уровне ─────────────────────── */

mvb_check('негодный конверт до файла не доходит', function () use ($ROOT) {
    require_once $ROOT . '/mvb_funnel.php';
    $каталог = outbox_tmp('bad');
    putenv("MVB_FUNNEL_OUTBOX={$каталог}");
    mvb_equal(mvb_funnel_event('', ['content_id' => 'x']), false, 'пустой тип');
    mvb_equal(mvb_funnel_event('чужое.событие', []), false, 'тип не из воронки');
    // Значение, которое невозможно закодировать в JSON.
    mvb_equal(mvb_funnel_event('funnel.content_viewed',
                               ['content_id' => "\xB1\x31"]), false,
              'битая строка в поле');
    mvb_equal(count(outbox_lines($каталог)), 0, 'в файл не должно попасть ничего');
});

mvb_check('здоровье сборщика считается, а не объявляется', function () use ($ROOT) {
    require_once $ROOT . '/mvb_funnel.php';
    $каталог = outbox_tmp('health');
    putenv("MVB_FUNNEL_OUTBOX={$каталог}");
    mvb_funnel_event('funnel.content_viewed', ['content_id' => 'a']);
    mvb_funnel_event('funnel.content_viewed', ['content_id' => 'b']);
    $здоровье = mvb_funnel_outbox_status();
    mvb_equal($здоровье['pending_count'], 2, 'событий в очереди');
    mvb_equal($здоровье['usable'], true, 'сборщик пригоден');
    mvb_true($здоровье['total_bytes'] > 0, 'размер очереди');
    mvb_true(array_key_exists('oldest_pending_age_seconds', $здоровье),
             'нет возраста старейшего события');
    mvb_true(array_key_exists('append_failures', $здоровье),
             'нет счёта отказов записи');
});

mvb_check('здоровье не отдаётся через веб', function () use ($ROOT) {
    // Файл лежит в каталоге сайта и после заливки доступен по HTTP.
    // Отдавать путь к сборщику и число накопленных событий незачем никому.
    $порт = mvb_free_port();
    $сервер = mvb_serve($ROOT, $порт);
    try {
        $ch = curl_init("http://127.0.0.1:{$порт}/tools/funnel_outbox_health.php");
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true,
                                CURLOPT_TIMEOUT => 10]);
        $тело = (string)curl_exec($ch);
        $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        mvb_equal($код, 404, 'здоровье сборщика открыто по HTTP');
        mvb_true(strpos($тело, 'каталог сборщика') === false,
                 'путь к сборщику отдан по HTTP');
    } finally { mvb_kill($сервер); }
});

mvb_check('здоровье из командной строки считает то же самое', function () use ($ROOT) {
    $каталог = outbox_tmp('healthcli');
    putenv("MVB_FUNNEL_OUTBOX={$каталог}");
    require_once $ROOT . '/mvb_funnel.php';
    mvb_funnel_event('funnel.content_viewed', ['content_id' => 'a']);
    $вывод = [];
    $код = 0;
    exec('MVB_FUNNEL_OUTBOX=' . escapeshellarg($каталог) . ' php '
         . escapeshellarg($ROOT . '/tools/funnel_outbox_health.php') . ' --json',
         $вывод, $код);
    mvb_equal($код, 0, 'код прогона здоровья');
    $здоровье = json_decode(implode("\n", $вывод), true);
    mvb_true(is_array($здоровье), 'здоровье не разобралось как JSON');
    mvb_equal($здоровье['pending_count'], 1, 'событий в очереди');
    mvb_equal($здоровье['usable'], true, 'пригодность');
});

mvb_finish();
