<?php
declare(strict_types=1);
$root=realpath($argv[1]??'');if(!$root||basename($root)!=='nastoronepodryadchika.ru')throw new RuntimeException('WRONG_SITE');
$rows=[];
foreach(['downloads','downloads/checklist-zakrytiya-rabot.pdf','downloads/.htaccess'] as $name){$p=$root.'/'.$name;clearstatcache(true,$p);$rows[$name]=['exists'=>file_exists($p),'symlink'=>is_link($p),'directory'=>is_dir($p),'file'=>is_file($p),'readable'=>is_readable($p),'mode'=>file_exists($p)?decoct(fileperms($p)&0777):null,'size'=>is_file($p)?filesize($p):null,'sha256'=>is_file($p)?hash_file('sha256',$p):null];}
$lead=(string)file_get_contents($root.'/lead.php');preg_match("/'checklist'\s*=>\s*\[\s*'file'\s*=>\s*'([^']+)'/",$lead,$match);
echo json_encode(['status'=>'PASS','read_only'=>true,'paths'=>$rows,'lead_checklist_target'=>$match[1]??null],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
