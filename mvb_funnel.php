<?php
/**
 * Отправка событий воронки в Control Plane. Best effort и только так.
 *
 * ГЛАВНОЕ ПРАВИЛО ФАЙЛА. Наблюдаемость никогда не становится условием работы
 * коммерческого контура. Ни одна функция отсюда не бросает исключений наружу,
 * не печатает ничего и не меняет код ответа. Отказ приёмника, закрытый порт,
 * зависший ответ, мусор вместо JSON — всё это молча заканчивается `false`.
 *
 * ПОРЯДОК ВЫЗОВА ОБЯЗАТЕЛЕН. Сначала человек получает то, за чем пришёл,
 * потом отправляется событие. Ради этого есть `mvb_funnel_release()`: на
 * PHP-FPM он закрывает соединение с браузером, и дальнейшая работа идёт уже
 * без человека на другом конце.
 *
 * НАСТРОЙКА ЧЕРЕЗ ОКРУЖЕНИЕ, А НЕ ЧЕРЕЗ РЕПОЗИТОРИЙ:
 *   MVB_FUNNEL_ENDPOINT  адрес приёмника, например
 *                        https://…/api/connector/events
 *   MVB_FUNNEL_TOKEN     значение заголовка X-Connector-Token
 * Не задано хотя бы одно — событий нет вовсе, сети никто не трогает. Это
 * рабочее состояние, а не поломка: сайт обязан работать без Control Plane.
 *
 * ПЕРСОНАЛЬНЫХ ДАННЫХ ЗДЕСЬ НЕ БЫВАЕТ. Имя, почта и телефон в событие не
 * попадают ни под каким ключом. Понадобится опознание по почте — это
 * отдельный слой идентичности с хешем, а не временный перенос открытого
 * адреса «пока что».
 */
declare(strict_types=1);

/** Снимок таксономии. Сгенерирован в ai-business-os, руками не правится. */
const MVB_TAXONOMY_SNAPSHOT = __DIR__ . '/taxonomy/pains.generated.json';

/** Потолки на сеть. Человек уже получил своё, но процесс держать незачем. */
const MVB_FUNNEL_CONNECT_TIMEOUT = 2;
const MVB_FUNNEL_TIMEOUT = 3;

/**
 * Закрыть соединение с браузером, оставив процесс работать.
 *
 * На PHP-FPM это `fastcgi_finish_request()`. Там, где его нет (встроенный
 * сервер, mod_php), остаётся обычный сброс буфера: событие тогда отправится
 * до закрытия соединения, и потолок в три секунды — единственное, что стоит
 * между человеком и зависшим приёмником. Поэтому потолок маленький.
 */
function mvb_funnel_release(): void
{
    if (function_exists('fastcgi_finish_request')) {
        @fastcgi_finish_request();
        return;
    }
    if (function_exists('litespeed_finish_request')) {
        @litespeed_finish_request();
        return;
    }
    while (ob_get_level() > 0) { @ob_end_flush(); }
    @flush();
}

/** Боль по ключу материала. `null` — соответствия нет, и это законно. */
function mvb_pain_of_magnet(string $magnet): ?string
{
    static $указатель = null;
    if ($указатель === null) {
        $указатель = [];
        if (is_readable(MVB_TAXONOMY_SNAPSHOT)) {
            $снимок = json_decode((string)@file_get_contents(MVB_TAXONOMY_SNAPSHOT), true);
            if (is_array($снимок)) {
                $указатель = $снимок['taxonomy']['magnet_to_pain'] ?? [];
            }
        }
    }
    $боль = $указатель[$magnet] ?? null;
    return is_string($боль) && $боль !== '' ? $боль : null;
}

/** UUIDv4 из случайных байт. */
function mvb_uuid4(): string
{
    try {
        $байты = random_bytes(16);
    } catch (Throwable $ошибка) {
        // Ни один источник случайности не должен ронять выдачу материала.
        $байты = pack('N4', mt_rand(), mt_rand(), mt_rand(), mt_rand());
    }
    $байты[6] = chr((ord($байты[6]) & 0x0f) | 0x40);
    $байты[8] = chr((ord($байты[8]) & 0x3f) | 0x80);
    return implode('-', [bin2hex(substr($байты, 0, 4)), bin2hex(substr($байты, 4, 2)),
                         bin2hex(substr($байты, 6, 2)), bin2hex(substr($байты, 8, 2)),
                         bin2hex(substr($байты, 10, 6))]);
}

/** Значение вида UUID из недоверенного ввода или `null`. */
function mvb_clean_uuid($значение): ?string
{
    $строка = trim((string)$значение);
    return preg_match('/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
                      . '[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/', $строка)
        ? strtolower($строка) : null;
}

/**
 * Отправить событие воронки. Возвращает `true` только при коде 2xx.
 *
 * Возвращаемое значение существует для тестов и журнала, а не для решений:
 * ни один вызывающий не имеет права менять поведение в зависимости от него.
 */
function mvb_funnel_event(string $тип, array $payload): bool
{
    $адрес = (string)getenv('MVB_FUNNEL_ENDPOINT');
    $токен = (string)getenv('MVB_FUNNEL_TOKEN');
    if ($адрес === '' || $токен === '') {
        return false;               // не настроено — сети не касаемся
    }
    if (!function_exists('curl_init')) {
        return false;
    }

    $payload += [
        'event_uuid'  => mvb_uuid4(),
        'occurred_at' => gmdate('c'),
    ];
    $тело = json_encode(['event_type' => $тип, 'agent' => 'site',
                         'payload' => $payload],
                        JSON_UNESCAPED_UNICODE);
    if ($тело === false) {
        return false;
    }

    try {
        $ch = curl_init($адрес);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $тело,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json',
                                   'X-Connector-Token: ' . $токен],
            CURLOPT_CONNECTTIMEOUT => MVB_FUNNEL_CONNECT_TIMEOUT,
            CURLOPT_TIMEOUT => MVB_FUNNEL_TIMEOUT,
            CURLOPT_FAILONERROR => false,
        ]);
        curl_exec($ch);
        $код = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        return $код >= 200 && $код < 300;
    } catch (Throwable $ошибка) {
        return false;               // молча: человек своё уже получил
    }
}
