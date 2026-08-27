<?php
/**
 * Приём событий браузера сайтом. Запуск: php tools/test_event_proxy.php
 *
 * ЗАЧЕМ ПОСРЕДНИК ВООБЩЕ. Приёмник Control Plane закрыт токеном
 * `X-Connector-Token`. Положить токен в браузерный JS нельзя — его прочтёт
 * любой. Поэтому браузер шлёт событие на СВОЙ домен, а токен остаётся на
 * сервере. Заодно исчезает CORS: запрос свой.
 *
 * ЧТО ПОСРЕДНИК ОБЯЗАН ДЕЛАТЬ. Принимать только те типы событий, которые
 * браузеру вообще позволено слать: открытый наружу адрес, принимающий любой
 * `event_type`, позволил бы кому угодно писать в поток покупки и выдачи.
 *
 * ЧЕГО ОН НЕ ДЕЛАЕТ. Не ждёт Control Plane и не сообщает браузеру о его
 * судьбе: ответ 204 приходит в любом случае.
 */
declare(strict_types=1);

$ROOT = dirname(__DIR__);
$провалов = 0;

require_once __DIR__ . '/_test_http.php';

echo "посредник событий браузера\n";

/**
 * Сценарий: сайт со своим каталогом сборщика.
 *
 * Приёмника здесь больше нет ни в одном режиме, и это не упрощение
 * оснастки: посредник в сеть не ходит вовсе. Режим теперь описывает
 * состояние сборщика — «пишет» и «записать нельзя».
 */
$сценарий = static function (string $режим, callable $тело) use ($ROOT) {
    $каталог = sys_get_temp_dir() . '/mvb_proxy_' . getmypid() . '_' . $режим;
    foreach ((array)glob($каталог . '/*') as $файл) {
        is_dir($файл) ? @rmdir($файл) : @unlink($файл);
    }
    @rmdir($каталог);
    @unlink($каталог);
    if ($режим === 'down') {
        // На месте каталога файл: сборщик не создаётся.
        @file_put_contents($каталог, 'не каталог');
    }
    putenv("MVB_FUNNEL_OUTBOX={$каталог}");
    $порт = mvb_free_port();
    $сайт = mvb_serve($ROOT, $порт);
    try { $тело($порт, $каталог); }
    finally { mvb_kill($сайт); }
};

/** События сборщика в том виде, в каком их получит приёмник. */
function proxy_events(string $каталог): array
{
    $записи = [];
    foreach ((array)glob($каталог . '/*.pending.jsonl') as $файл) {
        if (!is_file($файл)) { continue; }
        foreach (explode("\n", (string)file_get_contents($файл)) as $строка) {
            if (trim($строка) === '') { continue; }
            $конверт = json_decode($строка, true);
            if (!is_array($конверт)) { continue; }
            $тип = $конверт['event_type'] ?? null;
            unset($конверт['event_type']);
            $записи[] = ['event_type' => $тип, 'payload' => $конверт];
        }
    }
    return $записи;
}

/** Дождаться записи: сборщик пишет ПОСЛЕ ответа браузеру. */
function proxy_wait(string $каталог, int $сколько): array
{
    for ($i = 0; $i < 50; $i++) {
        $записи = proxy_events($каталог);
        if (count($записи) >= $сколько) { return $записи; }
        usleep(10000);
    }
    return proxy_events($каталог);
}

mvb_check('test_content_viewed_accepted_and_stored', static function () use ($сценарий) {
    $сценарий('ok', static function (int $порт, string $журнал) {
        $ответ = mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.content_viewed',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
            'session_id' => 'b1b2c3d4-5555-4666-8777-888899990000',
            'content_id' => '/materialy/dengi.html',
            'magnet_id' => 'dengi',
            'source' => 'instagram_reels',
        ]);
        mvb_equal($ответ['code'], 204, 'код ответа браузеру');
        $события = proxy_wait($журнал, 1);
        mvb_true(count($события) === 1, 'событие не легло в сборщик');
        mvb_equal($события[0]['event_type'], 'funnel.content_viewed', 'тип');
        mvb_equal($события[0]['payload']['magnet_id'], 'dengi', 'magnet_id');
    });
});

mvb_check('test_session_started_accepted', static function () use ($сценарий) {
    $сценарий('ok', static function (int $порт, string $журнал) {
        $ответ = mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.session_started',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
            'session_id' => 'b1b2c3d4-5555-4666-8777-888899990000',
        ]);
        mvb_equal($ответ['code'], 204, 'код ответа');
        usleep(300000);
        mvb_equal(count(proxy_events($журнал)), 1, 'событий у приёмника');
    });
});

mvb_check('test_proxy_refuses_events_browser_may_not_send', static function () use ($сценарий) {
    // Открытый адрес, принимающий любой тип, позволил бы писать покупки.
    $сценарий('ok', static function (int $порт, string $журнал) {
        foreach (['funnel.purchase_completed', 'funnel.product_delivered',
                  'funnel.magnet_delivered', 'task.created', 'выдуманное'] as $тип) {
            $ответ = mvb_post_json($порт, '/event.php', [
                'event_type' => $тип,
                'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
            ]);
            mvb_equal($ответ['code'], 204, "код на {$тип} (молча, но не шлём)");
        }
        usleep(300000);
        mvb_equal(count(proxy_events($журнал)), 0,
                  'посредник переслал событие, которого браузеру слать нельзя');
    });
});

mvb_check('test_proxy_strips_pii', static function () use ($сценарий) {
    $сценарий('ok', static function (int $порт, string $журнал) {
        mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.content_viewed',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
            'email' => 'denis@example.com',
            'phone' => '+79991234567',
            'name' => 'Денис',
        ]);
        usleep(300000);
        $сырой = is_file($журнал) ? (string)file_get_contents($журнал) : '';
        mvb_true(!str_contains($сырой, 'denis@example.com'), 'почта уехала в поток');
        mvb_true(!str_contains($сырой, '79991234567'), 'телефон уехал в поток');
        mvb_true(!str_contains($сырой, 'Денис'), 'имя уехало в поток');
    });
});

mvb_check('test_proxy_answers_when_outbox_is_unusable', static function () use ($сценарий) {
    $сценарий('down', static function (int $порт, string $журнал) {
        $ответ = mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.session_started',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
        ]);
        mvb_equal($ответ['code'], 204, 'браузер обязан получить ответ');
        mvb_true($ответ['time'] < 8.0,
                 'ответ занял ' . round($ответ['time'], 1) . ' с');
        usleep(200000);
        mvb_equal(count(proxy_events($журнал)), 0,
                  'сборщик не создан, а событие где-то оказалось');
    });
});

mvb_check('test_proxy_answers_without_touching_the_network', static function () use ($сценарий) {
    // Прежде эта проверка поднимала приёмник, который спит десять секунд, и
    // доказывала, что браузер его не ждёт. Приёмника больше нет: посредник
    // кладёт строку в файл. Доказывать теперь надо другое — что событие
    // доехало до сборщика и что ответ пришёл быстро, хотя домашней машины в
    // сети нет вовсе. Это и есть смысл варианта C, выраженный проверкой.
    $сценарий('offline', static function (int $порт, string $журнал) {
        $ответ = mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.session_started',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
        ]);
        mvb_equal($ответ['code'], 204, 'браузер обязан получить ответ');
        mvb_true($ответ['time'] < 3.0,
                 'ответ занял ' . round($ответ['time'], 1) . ' с — похоже на сеть');
        mvb_equal(count(proxy_wait($журнал, 1)), 1,
                  'событие не легло в сборщик без сети');
    });
});

mvb_check('test_proxy_rejects_garbage_without_crashing', static function () use ($сценарий) {
    $сценарий('ok', static function (int $порт, string $журнал) {
        foreach (['', 'не json', '[]', '{"event_type":123}'] as $мусор) {
            $ответ = mvb_post_raw($порт, '/event.php', $мусор);
            mvb_true($ответ['code'] === 204 || $ответ['code'] === 400,
                     "мусор дал код {$ответ['code']}");
        }
        usleep(300000);
        mvb_equal(count(proxy_events($журнал)), 0, 'мусор переслан приёмнику');
    });
});

mvb_finish();
