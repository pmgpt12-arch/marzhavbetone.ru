#!/usr/bin/env python3
"""R3 source gate: exactly the owner-approved 3600-second delivery change.

Compares the staged PHP files against immutable R2 commit byte-for-byte after
reversing ONLY these sanctioned changes. Preserves product catalog, prices,
orders, old sender address, archives, payment and webhook logic unchanged.

    python3 tools/check_r3_one_hour_delta.py --check
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "9a2e7936c8dc1b4c4e5afc8b654d82736f12e0af"
TESTS = [
    "tools/test_delivery_all_or_nothing.php",
    "tools/test_delivery_cache_freshness.php",
    "tools/test_order_lock.php",
    "tools/test_price_authority.php",
]
ALLOWED = {
    "products-config.php", "download.php", *TESTS,
    "tools/test_delivery_one_hour.php", "tools/test_delivery_expiry_http.py",
    "tools/check_r3_one_hour_delta.py", ".github/workflows/r3-one-hour-delivery.yml",
    "docs/brand/r3-one-hour-delivery-20261016.json",
}

def original(name: str) -> str:
    return subprocess.run(["git", "show", f"{BASE}:{name}"],cwd=ROOT,
        text=True,capture_output=True,check=True,timeout=15).stdout

def reverse_one(text: str, name: str, new: str, old: str) -> str:
    if text.count(new) != 1:
        raise ValueError(f"{name}: expected unique new delivery element, found {text.count(new)}: {new[:80]!r}")
    return text.replace(new, old)

def verify() -> dict:
    product=(ROOT/"products-config.php").read_text(encoding="utf-8")
    old_block="""// Срок жизни ссылки на скачивание (обещание из письма покупателю — 30 дней)
if (!defined('DELIVERY_TTL_DAYS')) {
    define('DELIVERY_TTL_DAYS', 30);
}"""
    new_block="""// Срок ссылки на скачивание новых заказов — ровно 1 час (3600 секунд).
// Исторические delivery.expires_at не продлеваем и не перезаписываем.
if (!defined('DELIVERY_TTL_SECONDS')) {
    define('DELIVERY_TTL_SECONDS', 3600);
}
if ((int) DELIVERY_TTL_SECONDS !== 3600) {
    throw new RuntimeException('DELIVERY_TTL_SECONDS must be exactly 3600');
}

/** Просроченная, отсутствующая или повреждённая дата запрещает скачивание. */
function mvb_delivery_link_expired(array $delivery, ?int $now = null): bool
{
    $raw = $delivery['expires_at'] ?? null;
    if (!is_string($raw) || trim($raw) === '') return true;
    $expiry = strtotime($raw);
    return $expiry === false || $expiry <= ($now ?? time());
}"""
    product = reverse_one(product, "products-config.php", new_block, old_block)
    guard="""    // Повторный webhook не продлевает уже выданный или просроченный токен.
    if ($token !== '' && mvb_delivery_link_expired($existing)) {
        return ['links' => [], 'missing' => [['sku' => '—',
            'reason' => 'срок прежней ссылки истёк или отсутствует']]];
    }
"""
    product = reverse_one(product,"products-config.php",guard,"")
    product = reverse_one(product,"products-config.php","    $issuedAt = time();\n","")
    product = reverse_one(product,"products-config.php","'created_at' => (string)($existing['created_at'] ?? date('c', $issuedAt))",
                          "'created_at' => (string)($existing['created_at'] ?? date('c'))")
    product = reverse_one(product,"products-config.php","?? date('c', $issuedAt + DELIVERY_TTL_SECONDS)",
                          "?? date('c', time() + DELIVERY_TTL_DAYS * 86400)")
    product = reverse_one(product,"products-config.php","$subject = 'Ваши материалы «На стороне подрядчика» — заказ оплачен';",
                          "$subject = 'Ваши материалы «Маржа в бетоне» — заказ оплачен';")
    product = reverse_one(product,"products-config.php",
      '    $body .= "Ссылки действуют 1 час с момента формирования. Сохраните файлы на свой компьютер.\\n\\n";',
      '    $days = DELIVERY_TTL_DAYS;\n    $body .= "Ссылки действуют {$days} дней. Сохраните файлы на свой компьютер.\\n\\n";')
    product = reverse_one(product,"products-config.php",'$body .= "Команда «На стороне подрядчика»\\n";',
                          '$body .= "Команда «Маржа в бетоне»\\n";')
    php_exact=(product == original("products-config.php"))

    download=(ROOT/"download.php").read_text(encoding="utf-8")
    download=reverse_one(download,"download.php","if (mvb_delivery_link_expired($delivery))",
      "if (!empty($delivery['expires_at']) && strtotime((string)$delivery['expires_at']) < time())")
    download_exact=(download == original("download.php"))
    fixtures={}
    for path in TESTS:
        s=(ROOT/path).read_text(encoding="utf-8")
        count=s.count("'DELIVERY_TTL_SECONDS' => 3600")
        if count not in (1,2):
            raise ValueError(f"{path}: expected one or two synthetic TTL settings, found {count}")
        s=s.replace("'DELIVERY_TTL_SECONDS' => 3600","'DELIVERY_TTL_DAYS' => 7")
        fixtures[path]=(s == original(path))

    extra = subprocess.run(["git","diff","--name-only",BASE,"HEAD"],
        cwd=ROOT,text=True,capture_output=True,check=True,timeout=12).stdout.splitlines()
    unexpected=[p for p in extra if p not in ALLOWED]
    return {
       "gate":"ONE_HOUR_DELIVERY_EXACT_SOURCE_DELTA",
       "baseline_commit":BASE,
       "products_config_only_approved_changes":php_exact,
       "download_php_only_expiry_guard":download_exact,
       "synthetic_fixture_only_ttl_config":fixtures,
       "unexpected_committed_paths":unexpected,
       "committed_changed_paths":extra,
       "ttl_seconds":3600,
       "pass":php_exact and download_exact and all(fixtures.values()) and not unexpected,
       "limitations":["No live checkout, production mail, YooKassa webhook or real buyer data tested",
         "Live old production default remains 30 days; no production file changed"],
    }

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--report",type=Path)
    a=parser.parse_args()
    result=verify()
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if a.check and not result["pass"] else 0

if __name__=="__main__":
    raise SystemExit(main())
