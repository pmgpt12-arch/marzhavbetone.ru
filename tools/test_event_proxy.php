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

$сценарий = static function (string $режим, callable $тело) use ($ROOT) {
    $временный = sys_get_temp_dir() . '/mvb_proxy_' . getmypid();
    @mkdir($временный, 0700, true);
    $роутер = $временный . '/receiver.php';
    file_put_contents($роутер, mvb_receiver_code());
    $журнал = $временный . '/events.log';
    @unlink($журнал);

    $порт_приёмника = mvb_free_port();
    $приём = null;
    if ($режим !== 'down') {
        putenv("MVB_TEST_MODE={$режим}");
        putenv("MVB_TEST_LOG={$журнал}");
        $приём = mvb_serve($временный, $порт_приёмника, $роутер);
    }
    putenv("MVB_FUNNEL_ENDPOINT=http://127.0.0.1:{$порт_приёмника}/receiver.php");
    putenv("MVB_FUNNEL_TOKEN=тестовый-токен");
    $порт = mvb_free_port();
    $сайт = mvb_serve($ROOT, $порт);
    try { $тело($порт, $журнал); }
    finally { mvb_kill($сайт); if ($приём) mvb_kill($приём); }
};

mvb_check('test_content_viewed_accepted_and_forwarded', static function () use ($сценарий) {
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
        usleep(300000);
        $события = mvb_events($журнал);
        mvb_true(count($события) === 1, 'событие не доехало до приёмника');
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
        mvb_equal(count(mvb_events($журнал)), 1, 'событий у приёмника');
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
        mvb_equal(count(mvb_events($журнал)), 0,
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

mvb_check('test_proxy_answers_when_receiver_is_down', static function () use ($сценарий) {
    $сценарий('down', static function (int $порт, string $журнал) {
        $ответ = mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.session_started',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
        ]);
        mvb_equal($ответ['code'], 204, 'браузер обязан получить ответ');
        mvb_true($ответ['time'] < 8.0,
                 'ответ занял ' . round($ответ['time'], 1) . ' с');
    });
});

mvb_check('test_proxy_answers_when_receiver_hangs', static function () use ($сценарий) {
    $сценарий('slow', static function (int $порт, string $журнал) {
        $ответ = mvb_post_json($порт, '/event.php', [
            'event_type' => 'funnel.session_started',
            'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000',
        ]);
        mvb_equal($ответ['code'], 204, 'браузер обязан получить ответ');
        mvb_true($ответ['time'] < 8.0,
                 'браузер ждал приёмника: ' . round($ответ['time'], 1) . ' с');
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
        mvb_equal(count(mvb_events($журнал)), 0, 'мусор переслан приёмнику');
    });
});

mvb_finish();
