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
