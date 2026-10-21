<?php
declare(strict_types=1);
$root=realpath($argv[1]??'');if(!$root||basename($root)!=='nastoronepodryadchika.ru')throw new RuntimeException('WRONG_SITE');
$names=['index.html','katalog.html','brand-approved-2026.css','attribution.js','sitemap.xml','products/p3-shablony-ks2-ks3.html','assets/nsp-hero-desktop.webp','assets/nsp-hero-mobile.webp','assets/nsp-stage-icons.svg'];$rows=[];
foreach($names as $name){$p=$root.'/'.$name;if(is_link($p)||is_link(dirname($p)))throw new RuntimeException('SYMLINK');$rows[]=['path'=>$name,'exists'=>file_exists($p),'sha256'=>is_file($p)?hash_file('sha256',$p):null];}
echo json_encode(['status'=>'PASS','read_only'=>true,'paths'=>$rows],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
