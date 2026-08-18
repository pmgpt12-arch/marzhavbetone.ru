<?php
/**
 * Автовыдача бесплатного материала по слову в комментарии Instagram.
 *
 * Адрес для Meta: https://marzhavbetone.ru/ig-webhook.php
 *
 * ЧТО ЭТО ДЕЛАЕТ. Человек пишет под роликом «КС2» — ему в личные сообщения
 * уходит ссылка на бесплатный материал по теме. Механизм Meta называется
 * private reply: он открывает переписку с автором комментария без его
 * первого сообщения, но ровно один раз на комментарий и не позже семи
 * суток после него.
 *
 * ЧЕГО ЭТО НЕ ДЕЛАЕТ, И ЭТО ОГРАНИЧЕНИЕ ПЛОЩАДКИ. Проверить, подписан ли
 * комментатор, нельзя: у Meta нет метода, отдающего статус подписки
 * конкретного человека. Graph API отдаёт только число подписчиков и
 * обезличенную статистику аудитории. Поэтому «подпишись и получи» здесь
 * исполняется просьбой в тексте сообщения, а не проверкой. Условие,
 * которое нечем проверить, в код не попадает.
 *
 * ПОЧЕМУ ПОДПИСЬ ЗАПРОСА ПРОВЕРЯЕТСЯ ДО ВСЕГО ОСТАЛЬНОГО. Адрес открыт
 * наружу, и без проверки любой желающий заставит нас слать сообщения от
 * имени аккаунта. Meta подписывает тело запроса секретом приложения —
 * заголовок X-Hub-Signature-256.
 *
 * ЧТО ЛЕЖИТ В CONFIG.PHP, А НЕ ЗДЕСЬ: IG_APP_SECRET, IG_VERIFY_TOKEN,
 * IG_ACCESS_TOKEN. В репозиторий они не попадают ни в каком виде.
 */
declare(strict_types=1);

require __DIR__ . '/config.php';

const IG_API = 'https://graph.facebook.com/v21.0';
// Meta разрешает один частный ответ на комментарий. Свой журнал нужен не
// вместо этого правила, а чтобы не тратить попытку на повторной доставке
// уведомления: она приходит не один раз.
const IG_LOG = __DIR__ . '/orders/ig-replies.log';

/** Слово в комментарии, приведённое к сравнимому виду. */
function ig_normalize(string $слово): string
{
    $слово = mb_strtolower(trim($слово), 'UTF-8');
    $слово = str_replace('ё', 'е', $слово);
    // Дефисы и пробелы внутри слова человек ставит как придётся:
    // «КС-2», «кс 2», «кс2» — одно и то же
    return (string)preg_replace('/[^a-zа-я0-9]/u', '', $слово);
}

/**
 * Разбирает файл соответствий без библиотеки YAML: на боевом хостинге её
 * может не быть, а формат здесь простой и проверяется тестом.
 */
function ig_load_keywords(string $путь): array
{
    $правила = [];
    $текущее = null;
    $умолчания = ['deliver' => 'page', 'utm_source' => 'instagram', 'utm_medium' => 'dm'];
    $раздел = '';

    foreach (file($путь, FILE_IGNORE_NEW_LINES) as $строка) {
        if (preg_match('/^(\w+):\s*$/', $строка, $m)) {
            $раздел = $m[1];
            continue;
        }
        if ($раздел === 'defaults' && preg_match('/^\s+(\w+):\s*(\S+)/', $строка, $m)) {
            $умолчания[$m[1]] = $m[2];
            continue;
        }
        if ($раздел !== 'keywords') {
            continue;
        }
        if (preg_match('/^\s*-\s*слова:\s*\[(.+)\]/u', $строка, $m)) {
            if ($текущее) {
                $правила[] = $текущее;
            }
            $слова = array_map('ig_normalize', explode(',', $m[1]));
            $текущее = ['слова' => array_filter($слова)];
            continue;
        }
        if ($текущее && preg_match('/^\s+(материал|подпись|deliver):\s*"?(.*?)"?\s*$/u', $строка, $m)) {
            $текущее[$m[1]] = $m[2];
        }
    }
    if ($текущее) {
        $правила[] = $текущее;
    }
    return ['defaults' => $умолчания, 'rules' => $правила];
}

/** Первое правило, чьё слово встретилось в тексте комментария. */
function ig_match(string $текст, array $правила): ?array
{
    $слова = array_map('ig_normalize', preg_split('/\s+/u', $текст) ?: []);
    $слова = array_filter($слова);
    foreach ($правила as $правило) {
        foreach ($правило['слова'] as $искомое) {
            if (in_array($искомое, $слова, true)) {
                return $правило;
            }
        }
    }
    return null;
}

/** Ссылка, которая уйдёт в сообщение. */
function ig_link(array $правило, array $умолчания): string
{
    $ключ = $правило['материал'];
    $способ = $правило['deliver'] ?? $умолчания['deliver'];
    $метки = http_build_query([
        'utm_source'   => $умолчания['utm_source'],
        'utm_medium'   => $умолчания['utm_medium'],
        'utm_campaign' => 'dm-' . $ключ,
    ]);
    return $способ === 'file'
        ? 'https://marzhavbetone.ru/downloads/' . rawurlencode($ключ) . '.zip?' . $метки
        : 'https://marzhavbetone.ru/materialy/' . rawurlencode($ключ) . '.html?' . $метки;
}

/** Текст сообщения. Просьба подписаться — просьба, а не условие выдачи. */
function ig_message(array $правило, string $ссылка): string
{
    return $правило['подпись'] . "\n\n" . $ссылка . "\n\n"
        . 'Это бесплатно и без обязательств. Если материал пригодится — '
        . 'подпишитесь, чтобы не потерять: разборы выходят регулярно.' . "\n\n"
        . 'Материал информационный: по конкретному договору нужна проверка юристом.';
}

/** Уже отвечали на этот комментарий? Попытка у нас одна. */
function ig_already_replied(string $commentId): bool
{
    if (!is_file(IG_LOG)) {
        return false;
    }
    foreach (file(IG_LOG, FILE_IGNORE_NEW_LINES) as $строка) {
        if (str_starts_with($строка, $commentId . "\t")) {
            return true;
        }
    }
    return false;
}

function ig_remember(string $commentId, string $материал, string $итог): void
{
    @mkdir(dirname(IG_LOG), 0770, true);
    // Ни текста комментария, ни имени человека: журнал не должен собирать
    // персональные данные ради того, чтобы не отправить письмо дважды
    @file_put_contents(
        IG_LOG,
        implode("\t", [$commentId, $материал, $итог, gmdate('c')]) . "\n",
        FILE_APPEND | LOCK_EX
    );
}

/** Частный ответ: сообщение автору комментария. */
function ig_private_reply(string $commentId, string $текст): array
{
    $ch = curl_init(IG_API . '/' . rawurlencode($commentId) . '/private_replies');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query([
            'message' => $текст,
            'access_token' => IG_ACCESS_TOKEN,
        ]),
        CURLOPT_TIMEOUT => 20,
    ]);
    $ответ = curl_exec($ch);
    $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return ['code' => $код, 'body' => (string)$ответ];
}

// --- Точка входа. Тесты подключают файл как библиотеку. -----------------

if (PHP_SAPI === 'cli' || defined('IG_WEBHOOK_AS_LIBRARY')) {
    return;
}

// Проверка адреса при подключении: Meta присылает свой токен и ждёт
// challenge обратно
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
    $ок = ($_GET['hub_mode'] ?? '') === 'subscribe'
        && hash_equals(IG_VERIFY_TOKEN, (string)($_GET['hub_verify_token'] ?? ''));
    if ($ок) {
        header('Content-Type: text/plain');
        echo $_GET['hub_challenge'] ?? '';
        exit;
    }
    http_response_code(403);
    exit;
}

$body = file_get_contents('php://input');
$подпись = $_SERVER['HTTP_X_HUB_SIGNATURE_256'] ?? '';
$ожидается = 'sha256=' . hash_hmac('sha256', (string)$body, IG_APP_SECRET);
if (!hash_equals($ожидается, $подпись)) {
    http_response_code(403);
    exit;
}

// Meta повторяет доставку, пока не получит 200. Отвечаем сразу и всегда:
// иначе одна наша ошибка превращается в бесконечный поток повторов.
http_response_code(200);
header('Content-Type: application/json; charset=utf-8');
echo json_encode(['ok' => true]);
if (function_exists('fastcgi_finish_request')) {
    fastcgi_finish_request();
}

$событие = json_decode((string)$body, true) ?: [];
$соответствия = ig_load_keywords(__DIR__ . '/data/social/ig-keywords.yaml');

foreach ($событие['entry'] ?? [] as $запись) {
    foreach ($запись['changes'] ?? [] as $изменение) {
        if (($изменение['field'] ?? '') !== 'comments') {
            continue;
        }
        $значение = $изменение['value'] ?? [];
        $commentId = (string)($значение['id'] ?? '');
        $текст = (string)($значение['text'] ?? '');
        $автор = (string)($значение['from']['id'] ?? '');

        // Свои же комментарии в ответ не получают ничего
        if (!$commentId || !$текст || $автор === IG_USER_ID) {
            continue;
        }
        if (ig_already_replied($commentId)) {
            continue;
        }
        $правило = ig_match($текст, $соответствия['rules']);
        if (!$правило) {
            continue;
        }

        $ссылка = ig_link($правило, $соответствия['defaults']);
        $ответ = ig_private_reply($commentId, ig_message($правило, $ссылка));
        ig_remember($commentId, $правило['материал'],
            $ответ['code'] === 200 ? 'ok' : 'error-' . $ответ['code']);
    }
}
