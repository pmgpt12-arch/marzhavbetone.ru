<?php
declare(strict_types=1);
// Scoped SEO correction: remove two archived product redirects from live sitemap.
if ($argc !== 3) exit(2);
$root=rtrim($argv[1],'/');
$backup=rtrim($argv[2],'/');
$items=[
 'products/p12-spor-s-summoy.html'=>'products/p5-shtrafy-uderzhaniya.html',
 'products/t6-kvartiry-vmesto-deneg.html'=>'products/p11-raschet-metrami.html',
];
function gate(bool $ok,string $why):void {if(!$ok)throw new RuntimeException($why);}
function atomicWrite(string $path,string $data):void {
 $tmp=tempnam(dirname($path),'.seo-archive-');
 gate($tmp!==false,'TEMP_FAILED');
 try {gate(file_put_contents($tmp,$data,LOCK_EX)===strlen($data),'WRITE_FAILED');chmod($tmp,0644);gate(rename($tmp,$path),'RENAME_FAILED');}
 finally {if(is_file($tmp))unlink($tmp);}
}
try {
 $xmlpath=$root.'/sitemap.xml';
 $xml=file_get_contents($xmlpath);
 gate($xml!==false && substr_count($xml,'<loc>')===84,'LIVE_SITEMAP_NOT_84');
 $changes=[];
 foreach($items as $path=>$target){
   $url='https://nastoronepodryadchika.ru/'.$path;
   $targetUrl='https://nastoronepodryadchika.ru/'.$target;
   $regex='~\\s*<url>\\s*<loc>'.preg_quote($url,'~').'</loc>.*?</url>~s';
   $n=0;$next=preg_replace($regex,'',$xml,1,$n);
   gate($next!==null && $n===1,'SITEMAP_URL_NOT_UNIQUE_'.$path);
   $xml=$next;
   $file=$root.'/'.$path;
   $body=file_get_contents($file);
   gate($body!==false,'HTML_MISSING_'.$path);
   gate(stripos($body,'name="robots"')===false,'ROBOTS_ALREADY_SET_'.$path);
   $oldTag='<link rel="canonical" href="'.$url.'">';
   $newTag='<link rel="canonical" href="'.$targetUrl.'">';
   gate(substr_count($body,$oldTag)===1,'CANONICAL_UNEXPECTED_'.$path);
   gate(substr_count(strtolower($body),'<head>')===1,'HEAD_NOT_UNIQUE_'.$path);
   $body=str_replace($oldTag,$newTag,$body);
   $body=preg_replace('~<head>~i','<head>'."\\n".'  <meta name="robots" content="noindex,follow">',$body,1,$count);
   gate($body!==null && $count===1,'META_INSERT_FAILED_'.$path);
   $changes[$path]=$body;
 }
 gate(substr_count($xml,'<loc>')===82,'SITEMAP_RESULT_NOT_82');
 $changes['sitemap.xml']=$xml;
 gate(!file_exists($backup),'BACKUP_EXISTS');
 gate(mkdir($backup,0700,true),'BACKUP_CREATE_FAILED');
 foreach($changes as $rel=>$body){
   $file=$root.'/'.$rel;$dest=$backup.'/'.$rel;
   $dir=dirname($dest);
   if(!is_dir($dir))gate(mkdir($dir,0700,true),'BACKUP_SUBDIR_FAILED');
   gate(copy($file,$dest),'BACKUP_COPY_FAILED_'.$rel);
   chmod($dest,0600);
   gate(hash_file('sha256',$file)===hash_file('sha256',$dest),'BACKUP_SHA_FAILED_'.$rel);
 }
 try {
   foreach($changes as $rel=>$body)atomicWrite($root.'/'.$rel,$body);
   foreach($items as $path=>$target){
     $s=file_get_contents($root.'/'.$path);
     gate($s!==false && str_contains($s,'<meta name="robots" content="noindex,follow">'),'META_VERIFY_'.$path);
     gate(str_contains($s,'href="https://nastoronepodryadchika.ru/'.$target.'"'),'CANONICAL_VERIFY_'.$path);
   }
   gate(substr_count((string)file_get_contents($xmlpath),'<loc>')===82,'SITEMAP_VERIFY');
 } catch(Throwable $e) {
   foreach($changes as $rel=>$body)if(is_file($backup.'/'.$rel))atomicWrite($root.'/'.$rel,(string)file_get_contents($backup.'/'.$rel));
   throw $e;
 }
 echo "ARCHIVE_SITEMAP_URLS_REMOVED=2\\n";
 echo "LIVE_INDEXABLE_SITEMAP_URLS=82\\n";
 echo "ARCHIVE_NOINDEX_AND_CANONICAL=PASS\\n";
} catch(Throwable $e){fwrite(STDERR,"ARCHIVE_SEO_ERROR=".$e->getMessage()."\\n");exit(1);}
