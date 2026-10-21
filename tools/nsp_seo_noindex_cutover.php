<?php
declare(strict_types=1);
// Scoped migration tool: only sitemap-listed HTML and one migration X-Robots-Tag rule.
if ($argc !== 4 || !in_array($argv[1], ['apply', 'rollback'], true)) { exit(2); }
[$script, $mode, $site, $backup] = $argv;
$site = rtrim($site, '/');
$backup = rtrim($backup, '/');
$tag = '<meta name="robots" content="noindex,nofollow,noarchive">';
$rule = '~^[ \\t]*Header always set X-Robots-Tag "noindex, nofollow, noarchive"\\r?\\n~m';
function must(bool $ok, string $reason): void { if (!$ok) { throw new RuntimeException($reason); } }
function safeWrite(string $path, string $data): void {
    $tmp = tempnam(dirname($path), '.seo-next-');
    must($tmp !== false, 'TEMP_FAILED');
    try {
        must(file_put_contents($tmp, $data, LOCK_EX) !== false, 'WRITE_FAILED');
        chmod($tmp, 0644);
        must(rename($tmp, $path), 'RENAME_FAILED');
    } finally { if (is_file($tmp)) unlink($tmp); }
}
try {
    $xml = file_get_contents($site . '/sitemap.xml');
    must($xml !== false, 'SITEMAP_MISSING');
    preg_match_all('~<loc>([^<]+)</loc>~', $xml, $m);
    $paths = [];
    foreach ($m[1] as $loc) {
        $url = html_entity_decode($loc, ENT_QUOTES | ENT_XML1, 'UTF-8');
        must(str_starts_with($url, 'https://nastoronepodryadchika.ru/'), 'FOREIGN_URL');
        $rel = ltrim(rawurldecode((string)parse_url($url, PHP_URL_PATH)), '/');
        if ($rel === '' || str_ends_with($rel, '/')) $rel .= 'index.html';
        must(!str_contains($rel, '..') && str_ends_with($rel, '.html'), 'UNSAFE_PATH');
        $file = realpath($site . '/' . $rel);
        must($file !== false && str_starts_with($file, $site . '/'), 'MISSING_HTML');
        $paths[$rel] = $file;
    }
    must(count($paths) === 84, 'SITEMAP_COUNT_CHANGED');
    $ht = $site . '/.htaccess';
    must(is_file($ht), 'HTACCESS_MISSING');
    if ($mode === 'rollback') {
        must(is_file($backup . '/.htaccess'), 'NO_BACKUP');
        foreach ($paths as $rel => $file) {
            $saved = $backup . '/' . $rel;
            must(is_file($saved), 'BACKUP_INCOMPLETE');
            safeWrite($file, (string)file_get_contents($saved));
        }
        safeWrite($ht, (string)file_get_contents($backup . '/.htaccess'));
        echo "SEO_NOINDEX_ROLLBACK=PASS\\n";
        exit(0);
    }
    $new = [];
    foreach ($paths as $rel => $file) {
        $s = file_get_contents($file);
        must($s !== false && substr_count($s, $tag) === 1, 'META_TAG_NOT_UNIQUE');
        $new[$rel] = str_replace($tag, '', $s);
    }
    $oldHt = file_get_contents($ht);
    must($oldHt !== false, 'HTACCESS_READ_FAILED');
    $n = 0;
    $newHt = preg_replace($rule, '', $oldHt, 1, $n);
    must($newHt !== null && $n === 1, 'HEADER_RULE_NOT_UNIQUE');
    must(!file_exists($backup), 'BACKUP_ALREADY_EXISTS');
    must(mkdir($backup, 0700, true), 'BACKUP_DIR_FAILED');
    chmod($backup, 0700);
    foreach ($paths as $rel => $file) {
        $dest = $backup . '/' . $rel;
        $dir = dirname($dest);
        if (!is_dir($dir)) must(mkdir($dir, 0700, true), 'BACKUP_SUBDIR_FAILED');
        must(copy($file, $dest), 'BACKUP_COPY_FAILED');
        chmod($dest, 0600);
        must(hash_file('sha256', $file) === hash_file('sha256', $dest), 'BACKUP_HASH_MISMATCH');
    }
    must(copy($ht, $backup . '/.htaccess'), 'HTACCESS_BACKUP_FAILED');
    chmod($backup . '/.htaccess', 0600);
    must(hash_file('sha256', $ht) === hash_file('sha256', $backup . '/.htaccess'), 'HTACCESS_BACKUP_HASH_MISMATCH');
    try {
        foreach ($new as $rel => $body) safeWrite($paths[$rel], $body);
        safeWrite($ht, $newHt);
        foreach ($paths as $rel => $file) must(!str_contains((string)file_get_contents($file), $tag), 'META_REMAINS');
        must(!str_contains((string)file_get_contents($ht), 'Header always set X-Robots-Tag "noindex, nofollow, noarchive"'), 'HEADER_REMAINS');
    } catch (Throwable $e) {
        foreach ($paths as $rel => $file) {
            $saved = $backup . '/' . $rel;
            if (is_file($saved)) safeWrite($file, (string)file_get_contents($saved));
        }
        safeWrite($ht, (string)file_get_contents($backup . '/.htaccess'));
        throw $e;
    }
    echo "SITEMAP_INDEXABLE_HTML=".count($paths)."\\n";
    echo "GLOBAL_NOINDEX_HEADER_REMOVED=YES\\n";
    echo "SEO_NOINDEX_FIX=VERIFIED\\n";
} catch (Throwable $e) {
    fwrite(STDERR, "SEO_FIX_FAILED=" . $e->getMessage() . "\\n");
    exit(1);
}
