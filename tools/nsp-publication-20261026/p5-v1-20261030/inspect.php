<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') {exit(1);}
$site=realpath($argv[1]??'');
if (!$site || basename($site)!=='nastoronepodryadchika.ru' || !is_file($site.'/index.html')) {throw new RuntimeException('SITE_IDENTITY');}
$paths=['products/p5-shtrafy-uderzhaniya.html','katalog.html','products-config.php','payment.php','download.php','app.js','app-script.php'];
$out=['schema'=>'NSP_P5_PRODUCTION_SNAPSHOT_v1','captured_utc'=>gmdate('c'),'read_only'=>true,'files'=>[],'product_locations'=>[]];
foreach($paths as $p){
 $raw=file_get_contents($site.'/'.$p);
 if($raw===false || strlen($raw)>1000000)throw new RuntimeException('SOURCE_READ:'.$p);
 if(preg_match('/-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|sk_live_[A-Za-z0-9]{12}|gh[pousr]_[A-Za-z0-9]{20}/',$raw))throw new RuntimeException('SOURCE_SECRET_PATTERN:'.$p);
 $out['files'][$p]=['sha256'=>hash('sha256',$raw),'bytes'=>strlen($raw),'base64'=>base64_encode($raw)];
}
// Read only known product locations. No credentials or order contents are copied.
foreach(['../../products-marzhavbetone','../products-marzhavbetone','products-storage']as $candidate){
 $d=realpath($site.'/'.$candidate);
 if(!$d||!is_dir($d.'/07-uderzhaniya-shtrafy-zachety'))continue;
 $files=[];foreach(glob($d.'/07-uderzhaniya-shtrafy-zachety/*')?:[]as $p){if(is_file($p))$files[]=['name'=>basename($p),'bytes'=>filesize($p),'sha256'=>hash_file('sha256',$p)];}
 $out['product_locations'][]=['relative_candidate'=>$candidate,'p5_files'=>$files];
}
echo json_encode($out,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES),"\n";
