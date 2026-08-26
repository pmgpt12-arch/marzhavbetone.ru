<?php
/**
 * Выдача материала против отказа приёмника событий. Запуск:
 *   php tools/test_lead_event.php
 *
 * ЗАЧЕМ ЭТОТ ТЕСТ ГЛАВНЫЙ В ЭТАПЕ 2. Инвариант этапа звучит так:
 * наблюдаемость никогда не становится условием работы коммерческого контура.
 * Проверить его чтением кода нельзя — можно только отключив приёмник и
 * посмотрев, получит ли человек файл. Здесь приёмник отключается пятью
 * разными способами.
 *
 * Как устроено. Поднимаются два встроенных сервера PHP: сайт и подставной
 * приёмник. Приёмник умеет отвечать нормально, спать дольше таймаута,
 * отвечать пятисоткой и мусором; «отказ соединения» изображается закрытым
 * портом. Запросы приёмник пишет в файл — по нему и проверяется payload.
 */
declare(strict_types=1);

$ROOT = dirname(__DIR__);
$провалов = 0;

function проверка(string $имя, callable $тело): void
{
    global $провалов;
    try {
        $тело();
        echo "  ok   {$имя}\n";
    } catch (Throwable $ошибка) {
        $провалов++;
        echo "  FAIL {$имя}\n         " . $ошибка->getMessage() . "\n";
    }
}

function равно($получено, $ожидалось, string $что): void
{
    if ($получено !== $ожидалось) {
        throw new RuntimeException(
            "{$что}: ожидалось " . var_export($ожидалось, true)
            . ", получено " . var_export($получено, true));
    }
}

function истинно($значение, string $что): void
{
    if (!$значение) throw new RuntimeException($что);
}

/** Свободный порт: занимаем и сразу отпускаем. */
function свободный_порт(): int
{
    $сокет = stream_socket_server('tcp://127.0.0.1:0', $код, $ошибка);
    $имя = stream_socket_get_name($сокет, false);
    fclose($сокет);
    return (int)substr($имя, strrpos($имя, ':') + 1);
}

function поднять(string $корень, int $порт, string $роутер = ''): array
{
    $команда = ['php', '-S', "127.0.0.1:{$порт}", '-t', $корень];
    if ($роутер !== '') $команда[] = $роутер;
    $процесс = proc_open($команда, [1 => ['file', '/dev/null', 'w'],
                                    2 => ['file', '/dev/null', 'w']], $трубы);
    // Ждём готовности порта, а не спим наугад.
    for ($i = 0; $i < 100; $i++) {
        $связь = @fsockopen('127.0.0.1', $порт, $к, $о, 0.2);
        if ($связь) { fclose($связь); return [$процесс, $порт]; }
        usleep(50000);
    }
    throw new RuntimeException("сервер на {$порт} не поднялся");
}

function погасить(array $сервер): void
{
    if (is_resource($сервер[0])) proc_terminate($сервер[0], 9);
}

/** POST на lead.php живого сервера. */
function послать(int $порт, array $поля): array
{
    $ch = curl_init("http://127.0.0.1:{$порт}/lead.php");
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query($поля),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
    ]);
    $тело = curl_exec($ch);
    $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $время = (float)curl_getinfo($ch, CURLINFO_TOTAL_TIME);
    curl_close($ch);
    return ['code' => $код, 'body' => $тело, 'time' => $время,
            'json' => json_decode((string)$тело, true)];
}

// ── Подставной приёмник ─────────────────────────────────────────────────
$приёмник_код = <<<'PHPR'
<?php
$журнал = getenv('MVB_TEST_LOG');
$режим  = getenv('MVB_TEST_MODE') ?: 'ok';
$тело = file_get_contents('php://input');
if ($журнал) {
    file_put_contents($журнал, $тело . "\n", FILE_APPEND);
}
if ($режим === 'slow')  { sleep(10); }
if ($режим === 'error') { http_response_code(500); echo 'сломалось'; return true; }
if ($режим === 'junk')  { echo 'не json <<<'; return true; }
http_response_code(201);
echo json_encode(['id' => 1, 'event_type' => 'funnel.magnet_delivered']);
return true;
PHPR;

$временный = sys_get_temp_dir() . '/mvb_test_' . getmypid();
@mkdir($временный, 0700, true);
$роутер = $временный . '/receiver.php';
file_put_contents($роутер, $приёмник_код);
$журнал = $временный . '/events.log';

function запустить_сценарий(string $ROOT, string $роутер, string $журнал,
                            string $режим, bool $приёмник_жив = true): array
{
    @unlink($журнал);
    $порт_приёмника = свободный_порт();
    $сервер_приёмника = null;
    if ($приёмник_жив) {
        putenv("MVB_TEST_MODE={$режим}");
        putenv("MVB_TEST_LOG={$журнал}");
        $сервер_приёмника = поднять(dirname($роутер), $порт_приёмника, $роутер);
    }
    putenv("MVB_FUNNEL_ENDPOINT=http://127.0.0.1:{$порт_приёмника}/receiver.php");
    putenv("MVB_FUNNEL_TOKEN=тестовый-токен");
    $порт_сайта = свободный_порт();
    $сервер_сайта = поднять($ROOT, $порт_сайта);
    return [$сервер_сайта, $сервер_приёмника, $порт_сайта, $журнал];
}

function события(string $журнал): array
{
    if (!is_file($журнал)) return [];
    $строки = array_filter(explode("\n", (string)file_get_contents($журнал)));
    return array_map(static fn($с) => json_decode($с, true), $строки);
}

$поля = ['name' => 'Тест', 'contact' => 'denis@example.com', 'consent' => 'yes',
         'material' => 'dengi', 'source' => 'telegram',
         'anonymous_id' => 'a1b2c3d4-5555-4666-8777-888899990000'];

echo "выдача материала против отказа приёмника\n";

проверка('test_lead_delivers_when_event_receiver_online', function () use ($ROOT, $роутер, $журнал, $поля) {
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'ok');
    try {
        $ответ = послать($порт, $поля);
        равно($ответ['code'], 200, 'код ответа');
        истинно($ответ['json']['ok'] ?? false, 'ok не true');
        равно($ответ['json']['download'], '/downloads/dengi.zip', 'ссылка');
        usleep(300000);
        истинно(count(события($лог)) === 1, 'событие не дошло до приёмника');
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_lead_delivers_when_event_receiver_down', function () use ($ROOT, $роутер, $журнал, $поля) {
    // Приёмник не поднят: порт закрыт, соединение отвергается.
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'ok', false);
    try {
        $ответ = послать($порт, $поля);
        равно($ответ['code'], 200, 'код ответа при мёртвом приёмнике');
        истинно($ответ['json']['ok'] ?? false, 'ok не true');
        равно($ответ['json']['download'], '/downloads/dengi.zip', 'ссылка');
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_lead_delivers_when_event_receiver_times_out', function () use ($ROOT, $роутер, $журнал, $поля) {
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'slow');
    try {
        $ответ = послать($порт, $поля);
        равно($ответ['code'], 200, 'код ответа при висящем приёмнике');
        истинно($ответ['json']['ok'] ?? false, 'ok не true');
        // Человек не ждёт приёмника: ответ обязан прийти заметно быстрее,
        // чем спит приёмник (10 с).
        истинно($ответ['time'] < 8.0,
                'ответ занял ' . round($ответ['time'], 1) . ' с — человек ждал приёмника');
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_event_failure_does_not_change_user_response', function () use ($ROOT, $роутер, $журнал, $поля) {
    $ответы = [];
    foreach (['ok', 'error', 'junk'] as $режим) {
        [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, $режим);
        try { $ответы[$режим] = послать($порт, $поля)['json']; }
        finally { погасить($сайт); if ($приём) погасить($приём); }
    }
    равно($ответы['error'], $ответы['ok'], 'ответ при 500 у приёмника');
    равно($ответы['junk'], $ответы['ok'], 'ответ при мусоре от приёмника');
});

проверка('test_magnet_delivered_only_after_successful_delivery', function () use ($ROOT, $роутер, $журнал) {
    // Заявка без согласия отвергается 422 — материал НЕ выдан, значит и
    // события «выдан» быть не должно. magnet_requested != magnet_delivered.
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'ok');
    try {
        $ответ = послать($порт, ['name' => 'Тест', 'contact' => 'x', 'consent' => '']);
        равно($ответ['code'], 422, 'код отказа');
        usleep(300000);
        равно(count(события($лог)), 0,
              'событие «материал выдан» ушло, хотя материал не выдан');
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_lead_event_contains_no_plain_email', function () use ($ROOT, $роутер, $журнал, $поля) {
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'ok');
    try {
        послать($порт, $поля);
        usleep(300000);
        $сырой = (string)file_get_contents($лог);
        истинно(!str_contains($сырой, 'denis@example.com'), 'адрес почты в событии');
        истинно(!str_contains($сырой, 'Тест'), 'имя человека в событии');
        $событие = события($лог)[0]['payload'] ?? [];
        foreach (['email', 'contact', 'name', 'phone'] as $поле) {
            истинно(!array_key_exists($поле, $событие), "поле {$поле} в payload");
        }
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_lead_event_contains_known_pain_and_magnet', function () use ($ROOT, $роутер, $журнал, $поля) {
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'ok');
    try {
        послать($порт, $поля);
        usleep(300000);
        $событие = события($лог)[0] ?? [];
        равно($событие['event_type'] ?? null, 'funnel.magnet_delivered', 'тип');
        $тело = $событие['payload'] ?? [];
        равно($тело['magnet_id'] ?? null, 'dengi', 'magnet_id');
        равно($тело['pain_id'] ?? null, 'neoplata', 'pain_id из снимка');
        равно($тело['anonymous_id'] ?? null, $поля['anonymous_id'], 'anonymous_id');
        равно($тело['source'] ?? null, 'telegram', 'source');
        истинно(preg_match('/^[0-9a-f-]{36}$/', (string)($тело['event_uuid'] ?? '')),
                'event_uuid не uuid: ' . ($тело['event_uuid'] ?? ''));
        истинно(!empty($тело['occurred_at']), 'нет occurred_at');
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_unmapped_magnet_sends_event_without_pain', function () use ($ROOT, $роутер, $журнал, $поля) {
    // `checklist` объявлен несопоставленным: событие уходит, боль пустая.
    // Пустое поле честнее наугад выбранной боли.
    [$сайт, $приём, $порт, $лог] = запустить_сценарий($ROOT, $роутер, $журнал, 'ok');
    try {
        послать($порт, array_merge($поля, ['material' => 'checklist']));
        usleep(300000);
        $тело = события($лог)[0]['payload'] ?? [];
        равно($тело['magnet_id'] ?? null, 'checklist', 'magnet_id');
        истинно(!array_key_exists('pain_id', $тело),
                'у несопоставленного магнита проставлена боль: '
                . var_export($тело['pain_id'] ?? null, true));
    } finally { погасить($сайт); if ($приём) погасить($приём); }
});

проверка('test_no_event_when_endpoint_not_configured', function () use ($ROOT, $поля) {
    // Не настроен адрес — сети нет вовсе, и выдача идёт как раньше.
    putenv('MVB_FUNNEL_ENDPOINT=');
    putenv('MVB_FUNNEL_TOKEN=');
    $порт = свободный_порт();
    $сайт = поднять($ROOT, $порт);
    try {
        $ответ = послать($порт, $поля);
        равно($ответ['code'], 200, 'код ответа без настроенного приёмника');
        истинно($ответ['json']['ok'] ?? false, 'ok не true');
        истинно($ответ['time'] < 5.0, 'ответ занял ' . round($ответ['time'], 1) . ' с');
    } finally { погасить($сайт); }
});

echo "\n";
if ($провалов) { echo "провалов: {$провалов}\n"; exit(1); }
echo "выдача материала не зависит от приёмника событий\n";
