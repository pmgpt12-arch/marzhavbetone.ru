<?php
/**
 * Приём событий воронки от браузера. Тонкий посредник, и только.
 *
 * ЗАЧЕМ ОН НУЖЕН. Приёмник Control Plane закрыт токеном `X-Connector-Token`.
 * Положить токен в браузерный JS нельзя — его прочтёт любой открывший
 * исходник страницы. Поэтому браузер шлёт событие на свой домен, а токен
 * остаётся на сервере. Заодно исчезает CORS: запрос свой.
 *
 * ЧТО ЗДЕСЬ ЗАПРЕЩЕНО. Пересылать типы событий, которых браузер слать не
 * может. Адрес открыт наружу; принимай он любой `event_type`, кто угодно
 * писал бы в поток «покупка совершена» и «материал выдан», и отчёт по
 * выручке врал бы по чужой воле. Перечень закрытый.
 *
 * ЧЕГО ОН НЕ ДЕЛАЕТ. Не ждёт Control Plane и не рассказывает браузеру о его
 * судьбе: 204 приходит в любом случае и всегда быстро. Отказ приёмника —
 * наше дело, а не посетителя.
 */
declare(strict_types=1);

require_once __DIR__ . '/mvb_funnel.php';

/** Ответить и закрыть соединение. Дальше человек уже не ждёт. */
function mvb_event_done(int $код = 204): void
{
    http_response_code($код);
    header('Content-Length: 0');
    mvb_funnel_release();
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    mvb_event_done(405);
    exit;
}

/* Только то, что браузер вправе сообщить о себе сам. Покупка, выдача
 * материала и выдача продукта сюда не входят намеренно: их источник —
 * сервер, который эти события и наблюдает. */
const MVB_BROWSER_EVENTS = [
    'funnel.session_started',
    'funnel.content_viewed',
    'funnel.pain_page_viewed',
    'funnel.cta_clicked',
    'funnel.solution_viewed',
    'funnel.pricing_viewed',
];

/* Поля, которые браузеру позволено прислать. Всё прочее отбрасывается —
 * это и есть защита от персональных данных: не «вырезаем почту», а «берём
 * только перечисленное». Перечень нельзя обойти, добавив новое поле. */
const MVB_BROWSER_FIELDS = [
    'anonymous_id', 'session_id', 'content_id', 'pain_id', 'stage_id',
    'magnet_id', 'sku', 'source', 'utm', 'occurred_at', 'event_uuid',
];

$сырое = (string)file_get_contents('php://input');
$данные = json_decode($сырое, true);
if (!is_array($данные)) {
    mvb_event_done(400);
    exit;
}

$тип = $данные['event_type'] ?? null;
if (!is_string($тип) || !in_array($тип, MVB_BROWSER_EVENTS, true)) {
    // Молча: сообщать отправителю, какие типы приняты, незачем.
    mvb_event_done();
    exit;
}

$payload = [];
foreach (MVB_BROWSER_FIELDS as $поле) {
    if (!array_key_exists($поле, $данные)) {
        continue;
    }
    $значение = $данные[$поле];
    if ($поле === 'utm') {
        if (!is_array($значение)) {
            continue;
        }
        $метки = [];
        foreach (['source', 'medium', 'campaign', 'content', 'term'] as $метка) {
            if (isset($значение[$метка]) && is_scalar($значение[$метка])) {
                $метки[$метка] = mb_substr((string)$значение[$метка], 0, 200);
            }
        }
        if ($метки) {
            $payload['utm'] = $метки;
        }
        continue;
    }
    if (is_scalar($значение)) {
        $payload[$поле] = mb_substr((string)$значение, 0, 200);
    }
}

// Ответ уходит ДО отправки: посетитель не ждёт ни приёмника, ни сети.
mvb_event_done();
mvb_funnel_event($тип, $payload);
