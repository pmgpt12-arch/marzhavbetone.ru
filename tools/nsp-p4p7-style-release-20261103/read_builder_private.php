<?php
declare(strict_types=1);
// Read-only owner-authorized diagnostic. Output solely the buyer ZIP builder's
// exact PHP function into the private ai-workstation filesystem; NEVER a GitHub artifact.
if (PHP_SAPI !== 'cli') exit(7);
$site=realpath($argv[1]??'');
if (!is_string($site) || basename($site)!=='nastoronepodryadchika.ru') exit(8);
require $site.'/config.php';
require $site.'/products-config.php';
$ref=new ReflectionFunction('mvb_build_product_zip');
$source=realpath((string)$ref->getFileName());
if ($source!==realpath($site.'/products-config.php')) exit(9);
$lines=file($source);
if (!is_array($lines)) exit(10);
$body=implode('',array_slice($lines,$ref->getStartLine()-1,$ref->getEndLine()-$ref->getStartLine()+1));
if (strlen($body)<800 || strlen($body)>16000 ||
    !str_contains($body,'function mvb_build_product_zip')) exit(11);
echo "<?php\n", $body;
