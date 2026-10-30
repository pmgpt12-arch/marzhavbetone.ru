<?php
declare(strict_types=1);
// Individual object review has been discontinued. No input is collected or sent.
header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
http_response_code(410);
echo json_encode(['ok'=>false,'code'=>'SERVICE_RETIRED','message'=>'Услуга индивидуального разбора объекта больше не предоставляется.'], JSON_UNESCAPED_UNICODE);
