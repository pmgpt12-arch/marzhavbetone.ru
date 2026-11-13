<?php
$root = getenv('HOME').'/www/nastoronepodryadchika.ru';
if (!is_dir($root) || !is_file($root.'/index.html')) { throw new Exception('WEBROOT_NOT_FOUND'); }
$name = 'zen_lm2h1UtRaVJ0bSUDComGw1B9e8aXdbt5EwOX7doqOsT2BwKNNePwa3iF9ALamaWS.html';
$body = "<meta name=\"zen-verification\" content=\"lm2h1UtRaVJ0bSUDComGw1B9e8aXdbt5EwOX7doqOsT2BwKNNePwa3iF9ALamaWS\" />\n";
$path = $root.'/'.$name;
$before = hash_file('sha256', $root.'/index.html');
if (is_link($path)) { throw new Exception('SYMLINK_REFUSED'); }
if (file_exists($path)) {
  if (file_get_contents($path) !== $body) { throw new Exception('EXISTING_CONTENT_MISMATCH'); }
  $action = 'already_exact';
} else {
  $tmp = tempnam($root, '.zen-verify-');
  try {
    if (file_put_contents($tmp, $body) !== strlen($body)) { throw new Exception('WRITE_FAILED'); }
    chmod($tmp, 0644);
    if (!link($tmp, $path)) { throw new Exception('ATOMIC_CREATE_FAILED'); }
    $action = 'created';
  } finally { unlink($tmp); }
}
if (file_get_contents($path) !== $body) { throw new Exception('CONTENT_CHECK_FAILED'); }
if (hash_file('sha256', $root.'/index.html') !== $before) { throw new Exception('INDEX_CHANGED'); }
echo json_encode(['action'=>$action,'filename'=>$name,'sha256'=>hash_file('sha256',$path),'index_sha256'=>$before,'index_unchanged'=>true], JSON_PRETTY_PRINT)."\n";
