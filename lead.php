<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['ok'=>false,'message'=>'Метод не поддерживается'], JSON_UNESCAPED_UNICODE); exit; }

/**
 * Бесплатные материалы. Ключ приходит из формы, поэтому список закрытый:
 * значение уходит в путь файла, и подстановка произвольной строки недопустима.
 * Архивы собирает tools/build_free_zips.py, идентификаторы там те же.
 *
 * Ключ по умолчанию — прежний чек-лист: форма на главной работает давно,
 * ссылки на неё могли разойтись, и запрос без параметра должен отдавать файл,
 * а не ошибку.
 */
const MVB_MATERIALS = [
    'checklist' => [
        'file'  => '/downloads/checklist-zakrytiya-rabot.pdf',
        'title' => 'Чек-лист закрытия выполненных работ',
        'label' => 'Скачать чек-лист PDF',
    ],
    'dengi' => [
        'file'  => '/downloads/dengi.zip',
        'title' => 'КС подписаны, денег нет: первые 7 проверок',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'dop-raboty' => [
        'file'  => '/downloads/dop-raboty.zip',
        'title' => 'Допработы: как зафиксировать поручение до начала',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'vozvrat-ks' => [
        'file'  => '/downloads/vozvrat-ks.zip',
        'title' => 'КС без возврата: проверочный лист комплекта',
        'label' => 'Скачать материалы (ZIP)',
    ],

    'uderzhaniya' => [
        'file'  => '/downloads/uderzhaniya.zip',
        'title' => 'Гарантийное удержание: что проверить до подписи',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'dogovor' => [
        'file'  => '/downloads/dogovor.zip',
        'title' => 'Договор субподряда: красные флаги до подписи',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'bankrotstvo' => [
        'file'  => '/downloads/bankrotstvo.zip',
        'title' => 'Банкротство заказчика: проверка контрагента до подписи',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'avans' => [
        'file'  => '/downloads/avans.zip',
        'title' => 'Аванс и обеспечение: что проверить до подписи',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'raschet-metrami' => [
        'file'  => '/downloads/raschet-metrami.zip',
        'title' => 'Красные флаги сделки «работы за квартиры»',
        'label' => 'Скачать материалы (ZIP)',
    ],
    'ispolnitelnaya-dokumentaciya' => [
        'file'  => '/downloads/ispolnitelnaya-dokumentaciya.zip',
        'title' => 'Исполнительная документация: проверка комплекта до передачи',
        'label' => 'Скачать материалы (ZIP)',
    ],
    // Десятый материал, 11.08.2026. Под самый большой измеренный кластер
    // спроса: акты скрытых работ — 68 745 частотности, 42% всего спроса.
    'akt-skrytyh-rabot' => [
        'file'  => '/downloads/akt-skrytyh-rabot.zip',
        'title' => 'Акт скрытых работ: какие работы его требуют и что в нём проверяют',
        'label' => 'Скачать материалы (ZIP)',
    ],
];

$name=trim((string)($_POST['name']??'')); $contact=trim((string)($_POST['contact']??'')); $consent=(string)($_POST['consent']??'');
if ($name===''||$contact===''||$consent!=='yes') { http_response_code(422); echo json_encode(['ok'=>false,'message'=>'Заполните имя, контакт и согласие'], JSON_UNESCAPED_UNICODE); exit; }

$key = (string)($_POST['material'] ?? 'checklist');
if (!isset(MVB_MATERIALS[$key])) { $key = 'checklist'; }
$material = MVB_MATERIALS[$key];

// Откуда пришёл человек: канал и слово. Нужно, чтобы понимать, что сработало
$source = preg_replace('/[^a-zA-Z0-9_\-.]/', '', (string)($_POST['source'] ?? ''));
if ($source === '') { $source = 'сайт'; }

$clean=static fn(string $value):string=>str_replace(["\r","\n"],' ',strip_tags($value));
$body="Новый лид\nМатериал: {$material['title']}\nИсточник: {$source}\nИмя: {$clean($name)}\nКонтакт: {$clean($contact)}\nСогласие: получено";
mail('marzhavbetone@yandex.ru','=?UTF-8?B?'.base64_encode('Заявка на материал: '.$material['title']).'?=',$body,implode("\r\n",['From: site@marzhavbetone.ru','Content-Type: text/plain; charset=UTF-8']));

echo json_encode([
    'ok'       => true,
    'download' => $material['file'],
    'label'    => $material['label'],
], JSON_UNESCAPED_UNICODE);

/* Событие «материал выдан» — ПОСЛЕ выдачи и только после неё.
 *
 * Порядок здесь и есть смысл правки. Заявка без согласия уходит выше по
 * коду с 422 и до этой строки не доходит: magnet_requested и
 * magnet_delivered — разные события, и второе означает, что человек
 * действительно получил ссылку.
 *
 * mvb_funnel_release() закрывает соединение с браузером до отправки: на
 * PHP-FPM человек не ждёт приёмника вовсе. Там, где закрыть нельзя,
 * остаётся потолок в три секунды внутри отправителя.
 *
 * Отказ сборщика здесь не проверяется и не может ни на что повлиять:
 * возвращаемое значение намеренно не читается. Ответ человеку уже ушёл.
 * Событие ложится строкой в файл на этом же хостинге; сети этот путь не
 * касается, и спящая домашняя машина на выдачу материала не влияет.
 *
 * Соответствие «материал -> боль» читается из сгенерированного снимка
 * taxonomy/pains.generated.json, а не записано здесь: своя таблица в этом
 * файле была бы четвёртой таксономией.
 *
 * Ни имени, ни контакта в событии нет ни под каким ключом.
 */
require_once __DIR__ . '/mvb_funnel.php';
mvb_funnel_release();

$событие = [
    'anonymous_id' => mvb_clean_uuid($_POST['anonymous_id'] ?? null),
    'session_id'   => mvb_clean_uuid($_POST['session_id'] ?? null),
    'magnet_id'    => $key,
    'source'       => $source,
];
$боль = mvb_pain_of_magnet($key);
if ($боль !== null) {
    $событие['pain_id'] = $боль;
}
$contentId = preg_replace('/[^a-zA-Z0-9_\-.]/', '',
                          (string)($_POST['content_id'] ?? ''));
if ($contentId !== '') {
    $событие['content_id'] = $contentId;
}
mvb_funnel_event('funnel.magnet_delivered', $событие);
