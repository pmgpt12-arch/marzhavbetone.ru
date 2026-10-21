<?php
declare(strict_types=1);
$root=realpath($argv[1]??'');if(!$root||basename($root)!=='nastoronepodryadchika.ru')throw new RuntimeException('WRONG_SITE');
$slugs=['dengi','dop-raboty','vozvrat-ks','uderzhaniya','dogovor','bankrotstvo','avans','raschet-metrami','ispolnitelnaya-dokumentaciya','akt-skrytyh-rabot'];$rows=[];
foreach($slugs as $slug){$name='downloads/'.$slug.'.zip';$p=$root.'/'.$name;$rows[]=['path'=>$name,'exists'=>file_exists($p),'symlink'=>is_link($p),'sha256'=>is_file($p)?hash_file('sha256',$p):null];}
$lead=(string)file_get_contents($root.'/lead.php');preg_match_all("/'([a-z0-9-]+)'\s*=>\s*\[\s*'file'\s*=>\s*'([^']+)'/",$lead,$m,PREG_SET_ORDER);$map=[];foreach($m as $r)$map[$r[1]]=$r[2];
echo json_encode(['status'=>'PASS','read_only'=>true,'paths'=>$rows,'lead_material_targets'=>$map],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
