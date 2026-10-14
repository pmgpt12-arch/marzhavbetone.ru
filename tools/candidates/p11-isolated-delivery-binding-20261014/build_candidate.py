#!/usr/bin/env python3
"""Exact-source isolated overlay. No network, checkout, canonical or live changes."""
from pathlib import Path
import difflib, hashlib, json

BASE = '8311bb2dc7b497415952d03630e4a477f8bf9d7c'
EXPECTED_BLOBS = {'products-config.php': '1d2a0225c3974d0fd44b9011b1b06803ceadb16e',
                  'download.php': 'f642cf899acf0915e27ced6f626bdc78424c41c9'}

def blob(b):
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Exact unique patch anchor failed: '+repr(before[:100]))
    return text.replace(before, after, 1)

def build(inputs: dict[str, bytes], helpers: str):
    for path, expected in EXPECTED_BLOBS.items():
        if blob(inputs[path]) != expected:
            raise ValueError('Source drift: '+path)
    p=inputs['products-config.php'].decode()
    before="""        $edition = $sku === 'p1' ? ($existing['editions'][$sku] ?? ($position['edition'] ?? null)) : null;
        if ($sku === 'p1' && $issued !== null) {"""
    after="""        $edition = $sku === 'p1' ? ($existing['editions'][$sku] ?? ($position['edition'] ?? null)) : null;
        $p11IssuedEdition = $existing['editions']['p11'] ?? null;
        if (($sku === 'p11' || $sku === 't6') && $issued !== null
            && ($sku !== 'p11' || $p11IssuedEdition === null)) {
            // Previously issued P11/T6 keeps its original archive, token and route.
            // Even a later edition marker must not migrate a historical order.
            $zipPath = is_string($issued) && basename($issued) === $issued
                && !preg_match('/^p11-[a-f0-9]{64}\\.zip$/D', $issued)
                && is_file(DELIVERY_DIR . '/' . $issued) ? DELIVERY_DIR . '/' . $issued : null;
        } elseif ($sku === 'p11' && ($p11IssuedEdition !== null || array_key_exists('edition', $position))) {
            $edition = $p11IssuedEdition ?? $position['edition'];
            $zipPath = null;
            if (($order['status'] ?? '') === 'paid' && mvb_p11_binding_valid($edition)) {
                if ($p11IssuedEdition !== null) {
                    $zipPath = mvb_p11_edition_path($edition);
                    if ($issued !== $edition['zip'] || mvb_p11_edition_letter($edition) === null) $zipPath = null;
                } else {
                    $zipPath = mvb_p11_stage_edition($edition);
                }
            }
        } elseif ($sku === 't6' && array_key_exists('edition', $position)) {
            // Consolidated P11 must not be selected through standalone T6.
            $zipPath = null;
        } elseif ($sku === 'p1' && $issued !== null) {"""
    p=replace_once(p,before,after)
    p=replace_once(p,"        if ($sku === 'p1' && $edition !== null) $editions[$sku] = $edition;",
                     "        if (($sku === 'p1' || $sku === 'p11') && $edition !== null) $editions[$sku] = $edition;")
    p=replace_once(p,"function mvb_delivery_email(array $order, array $links): string\n{",
        "function mvb_delivery_email(array $order, array $links): string\n{\n    if (isset($order['delivery']['editions']['p11'])) {\n        return mvb_p11_bound_delivery_email($order, $links);\n    }")
    p=replace_once(p,"'name' => $product['name'],", "'name' => ($sku === 'p11' && $edition !== null)\n                ? 'Система проверки расчётов недвижимостью и уступки прав' : $product['name'],")
    p=p.rstrip()+"\n"+helpers
    d=inputs['download.php'].decode()
    d=replace_once(d,"$edition = $sku === 'p1' ? ($delivery['editions'][$sku] ?? null) : null;",
                     "$edition = ($sku === 'p1' || $sku === 'p11') ? ($delivery['editions'][$sku] ?? null) : null;")
    d=replace_once(d,"    if ($edition !== null) {", """    if ($sku === 'p11' && $edition === null
        && preg_match('/^p11-[a-f0-9]{64}\\.zip$/D', (string)$delivery['items'][$sku])) {
        return ['deny' => [500, 'Missing P11 edition metadata.']];
    }
    if ($edition !== null) {""")
    d=replace_once(d,"$pinnedPath = mvb_p1_edition_path($edition);",
                     "$pinnedPath = $sku === 'p11' ? mvb_p11_edition_path($edition) : mvb_p1_edition_path($edition);")
    d=replace_once(d,"if ($sku === 'p1' && !is_file(DELIVERY_DIR . '/' . basename((string)$delivery['items'][$sku]))) {",
                     "if (in_array($sku, ['p1', 'p11', 't6'], true) && !is_file(DELIVERY_DIR . '/' . basename((string)$delivery['items'][$sku]))) {")
    d=replace_once(d,"if (!is_file($zipPath) && !$decision['pinned'] && $sku !== 'p1') {",
                     "if (!is_file($zipPath) && !$decision['pinned'] && !in_array($sku, ['p1', 'p11', 't6'], true)) {")
    outputs={'products-config.php':p.encode(),'download.php':d.encode()}
    patch=''.join(''.join(difflib.unified_diff(inputs[k].decode().splitlines(True),v.decode().splitlines(True),
                         fromfile='a/'+k,tofile='b/'+k)) for k,v in outputs.items())
    return outputs,patch
