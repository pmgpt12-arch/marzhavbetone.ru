<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['ok'=>false,'message'=>'Метод не поддерживается'], JSON_UNESCAPED_UNICODE); exit; }
$name=trim((string)($_POST['name']??'')); $contact=trim((string)($_POST['contact']??'')); $consent=(string)($_POST['consent']??'');
if ($name===''||$contact===''||$consent!=='yes') { http_response_code(422); echo json_encode(['ok'=>false,'message'=>'Заполните имя, контакт и согласие'], JSON_UNESCAPED_UNICODE); exit; }
$clean=static fn(string $value):string=>str_replace(["\r","\n"],' ',strip_tags($value));
$body="Новый лид на чек-лист\nИмя: {$clean($name)}\nКонтакт: {$clean($contact)}\nСогласие: получено";
mail('marzhavbetone@yandex.ru','=?UTF-8?B?'.base64_encode('Скачан чек-лист marzhavbetone.ru').'?=',$body,implode("\r\n",['From: site@marzhavbetone.ru','Content-Type: text/plain; charset=UTF-8']));
echo json_encode(['ok'=>true,'download'=>'/downloads/checklist-zakrytiya-rabot.pdf'], JSON_UNESCAPED_UNICODE);
