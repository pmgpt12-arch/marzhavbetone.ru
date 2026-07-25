<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['ok'=>false,'message'=>'Метод не поддерживается'], JSON_UNESCAPED_UNICODE); exit; }
$product=trim((string)($_POST['product']??'Общий запрос'));
$contact=trim((string)($_POST['contact']??''));
$consent=(string)($_POST['consent']??'');
if ($contact===''||$consent!=='yes') { http_response_code(422); echo json_encode(['ok'=>false,'message'=>'Укажите контакт и подтвердите согласие'], JSON_UNESCAPED_UNICODE); exit; }
if (mb_strlen($product)>500||mb_strlen($contact)>120) { http_response_code(422); echo json_encode(['ok'=>false,'message'=>'Данные заказа слишком длинные'], JSON_UNESCAPED_UNICODE); exit; }
$clean=static fn(string $value):string=>str_replace(["\r","\n"],' ',strip_tags($value));
$subject='Новый заказ с marzhavbetone.ru';
$body="Пакет: {$clean($product)}\nКонтакт: {$clean($contact)}\nСогласие: получено";
$headers=['From: site@marzhavbetone.ru','Reply-To: marzhavbetone@yandex.ru','Content-Type: text/plain; charset=UTF-8'];
$sent=mail('marzhavbetone@yandex.ru','=?UTF-8?B?'.base64_encode($subject).'?=',$body,implode("\r\n",$headers));
if (!$sent) { http_response_code(500); echo json_encode(['ok'=>false,'message'=>'Сервер не подтвердил отправку'], JSON_UNESCAPED_UNICODE); exit; }
echo json_encode(['ok'=>true], JSON_UNESCAPED_UNICODE);
