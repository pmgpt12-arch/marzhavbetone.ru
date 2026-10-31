<?php
declare(strict_types=1);

header('Content-Type: application/javascript; charset=UTF-8');
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

readfile(__DIR__ . '/app.js');
