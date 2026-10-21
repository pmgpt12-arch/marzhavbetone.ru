<?php
// Export only public static files. Never traverse runtime/private/source directories.
declare(strict_types=1);
$root=realpath($argv[1]??'');
if (!$root || basename($root)!=='nastoronepodryadchika.ru') throw new RuntimeException('WRONG_SITE');
$dirs=['articles','materialy','products','assets','images','img','css','js','fonts'];
$ext=['html','css','js','svg','png','jpg','jpeg','webp','ico','gif','avif','woff','woff2','ttf','eot','webmanifest','xml'];
$rows=[];
function collect(string $root,string $dir,array $ext,array &$rows): void {
    foreach(new DirectoryIterator($dir) as $f) {
        if($f->isDot() || $f->isLink()) continue;
        $name=$f->getFilename();
        if(preg_match('/backup|archive|rebrand-preview|\.bak|\.old|^\./i',$name)) continue;
        if($f->isDir()) { collect($root,$f->getPathname(),$ext,$rows); continue; }
        $path=substr($f->getPathname(),strlen($root)+1);
        if(!in_array(strtolower($f->getExtension()),$ext,true) && $path!=='robots.txt') continue;
        if(!preg_match('~^[a-zA-Z0-9_./-]+$~D',$path)) throw new RuntimeException('UNSAFE_PATH');
        if($f->getSize()>15000000) throw new RuntimeException('OVERSIZE_STATIC_FILE');
        $rows[]=['path'=>$path,'size'=>$f->getSize(),'sha256'=>hash_file('sha256',$f->getPathname())];
    }
}
// Root files and explicitly public subdirectories only.
foreach(new DirectoryIterator($root) as $f) {
    if($f->isDot()||$f->isLink()) continue;
    if($f->isDir()) { if(in_array($f->getFilename(),$dirs,true)) collect($root,$f->getPathname(),$ext,$rows); continue; }
    $path=$f->getFilename();
    if(preg_match('/backup|archive|rebrand-preview|\.bak|\.old|^\./i',$path)) continue;
    if(!in_array(strtolower($f->getExtension()),$ext,true)&&$path!=='robots.txt') continue;
    if(!preg_match('~^[a-zA-Z0-9_.-]+$~D',$path)||$f->getSize()>15000000) throw new RuntimeException('UNSAFE_ROOT_FILE');
    $rows[]=['path'=>$path,'size'=>$f->getSize(),'sha256'=>hash_file('sha256',$f->getPathname())];
}
usort($rows,fn($a,$b)=>strcmp($a['path'],$b['path']));
if(count($rows)<90||count($rows)>1200) throw new RuntimeException('STATIC_COUNT_OUT_OF_BOUNDS');
echo json_encode($rows,JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR)."\n";
