<?php
/**
 * Общая оснастка для PHP-тестов, поднимающих встроенный сервер.
 *
 * Заведена, потому что второй такой тест появился в этом же заходе, и
 * копия оснастки разошлась бы с оригиналом на первой же правке.
 */
declare(strict_types=1);

function mvb_check(string $имя, callable $тело): void
{
    global $провалов;
    try { $тело(); echo "  ok   {$имя}\n"; }
    catch (Throwable $ошибка) {
        $провалов = ($провалов ?? 0) + 1;
        echo "  FAIL {$имя}\n         " . $ошибка->getMessage() . "\n";
    }
}

function mvb_equal($получено, $ожидалось, string $что): void
{
    if ($получено !== $ожидалось) {
        throw new RuntimeException("{$что}: ожидалось " . var_export($ожидалось, true)
            . ", получено " . var_export($получено, true));
    }
}

function mvb_true($значение, string $что): void
{
    if (!$значение) throw new RuntimeException($что);
}

function mvb_free_port(): int
{
    $сокет = stream_socket_server('tcp://127.0.0.1:0', $код, $ошибка);
    $имя = stream_socket_get_name($сокет, false);
    fclose($сокет);
    return (int)substr($имя, strrpos($имя, ':') + 1);
}

function mvb_serve(string $корень, int $порт, string $роутер = ''): array
{
    $команда = ['php', '-S', "127.0.0.1:{$порт}", '-t', $корень];
    if ($роутер !== '') $команда[] = $роутер;
    $процесс = proc_open($команда, [1 => ['file', '/dev/null', 'w'],
                                    2 => ['file', '/dev/null', 'w']], $трубы);
    for ($i = 0; $i < 100; $i++) {
        $связь = @fsockopen('127.0.0.1', $порт, $к, $о, 0.2);
        if ($связь) { fclose($связь); return [$процесс]; }
        usleep(50000);
    }
    throw new RuntimeException("сервер на {$порт} не поднялся");
}

function mvb_kill(array $сервер): void
{
    if (is_resource($сервер[0])) proc_terminate($сервер[0], 9);
}

function mvb_post_raw(int $порт, string $путь, string $тело,
                      string $тип = 'application/json'): array
{
    $ch = curl_init("http://127.0.0.1:{$порт}{$путь}");
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $тело,
        CURLOPT_HTTPHEADER => ['Content-Type: ' . $тип],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
    ]);
    $ответ = curl_exec($ch);
    $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $время = (float)curl_getinfo($ch, CURLINFO_TOTAL_TIME);
    curl_close($ch);
    return ['code' => $код, 'body' => (string)$ответ, 'time' => $время];
}

function mvb_post_json(int $порт, string $путь, array $данные): array
{
    return mvb_post_raw($порт, $путь,
                        (string)json_encode($данные, JSON_UNESCAPED_UNICODE));
}

function mvb_receiver_code(): string
{
    return <<<'PHPR'
<?php
$журнал = getenv('MVB_TEST_LOG');
$режим  = getenv('MVB_TEST_MODE') ?: 'ok';
$тело = file_get_contents('php://input');
if ($журнал) { file_put_contents($журнал, $тело . "\n", FILE_APPEND); }
if ($режим === 'slow')  { sleep(10); }
if ($режим === 'error') { http_response_code(500); echo 'сломалось'; return true; }
if ($режим === 'junk')  { echo 'не json <<<'; return true; }
http_response_code(201);
echo json_encode(['id' => 1]);
return true;
PHPR;
}

function mvb_events(string $журнал): array
{
    if (!is_file($журнал)) return [];
    $строки = array_filter(explode("\n", (string)file_get_contents($журнал)));
    return array_map(static fn($с) => json_decode($с, true), $строки);
}

function mvb_finish(): void
{
    global $провалов;
    echo "\n";
    if (!empty($провалов)) { echo "провалов: {$провалов}\n"; exit(1); }
    echo "все проверки пройдены\n";
}
