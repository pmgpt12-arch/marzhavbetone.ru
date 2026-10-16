#!/usr/bin/env python3
"""HTTP acceptance of the real download.php, with synthetic orders and a local
PHP server. No third-party services, emails, payments or production files.

Run: python3 tools/test_delivery_expiry_http.py
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = "0123456789abcdef0123456789abcdef"
ORDER_ID = "order_20261016_080000_abc123"
SKU = "p7"


def iso(seconds: int) -> str:
    return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat(timespec="seconds")


def request(url: str) -> tuple[int, bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def require(ok: bool, label: str) -> None:
    if not ok:
        raise AssertionError(label)
    print("PASS:", label, flush=True)


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="mvb-onehour-http-") as tmp:
        base = Path(tmp)
        web = base / "site"
        orders = base / "private-orders"
        delivery = orders / "delivery"
        products = base / "private-products"
        for folder in (web, delivery, products):
            folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "download.php", web / "download.php")
        shutil.copy2(ROOT / "products-config.php", web / "products-config.php")
        (web / "health.txt").write_text("OK", encoding="utf-8")
        with zipfile.ZipFile(delivery / "qa.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("01-qa.txt", "Only synthetic QA content.\n")
        def php_path(path: Path) -> str:
            return str(path).replace("\\", "\\\\").replace("'", "\\'")
        config = (
            "<?php\ndeclare(strict_types=1);\n"
            f"define('ORDERS_DIR','{php_path(orders)}');\n"
            f"define('DELIVERY_DIR','{php_path(delivery)}');\n"
            f"define('PRODUCTS_DIR','{php_path(products)}');\n"
            "define('SITE_URL','http://127.0.0.1');\n"
            "define('ADMIN_EMAIL','qa@example.invalid');\n"
        )
        (web / "config.php").write_text(config, encoding="utf-8")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen(
            ["php", "-S", f"127.0.0.1:{port}", "-t", str(web)],
            cwd=web, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            health = f"http://127.0.0.1:{port}/health.txt"
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError("Synthetic PHP server exited")
                try:
                    code, body, _ = request(health)
                    if code == 200 and body == b"OK":
                        break
                except (OSError, TimeoutError):
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Synthetic PHP server did not become ready")
            now = int(time.time())
            order = {
                "id": ORDER_ID,
                "status": "paid",
                "email": "synthetic@example.invalid",
                "delivery": {
                    "token": TOKEN, "created_at": iso(now),
                    "expires_at": iso(now + 3600),
                    "items": {SKU: "qa.zip"}, "downloads": 0,
                },
            }
            order_file = orders / (ORDER_ID + ".json")
            def store(data: dict) -> None:
                order_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            def url(token: str = TOKEN, sku: str = SKU, order_id: str = ORDER_ID) -> str:
                return (f"http://127.0.0.1:{port}/download.php"
                        f"?o={order_id}&t={token}&f={sku}")
            store(order)
            status, data, headers = request(url())
            require(status == 200, "fresh paid link HTTP 200")
            require(data.startswith(b"PK") and "qa.zip" in headers.get("Content-Disposition", ""), "actual ZIP transfer")
            saved = json.loads(order_file.read_text(encoding="utf-8"))
            require(saved["delivery"]["downloads"] == 1, "successful request increments protected counter")
            status, _, _ = request(url(token="ffffffffffffffffffffffffffffffff"))
            require(status == 403, "wrong token HTTP 403")
            status, _, _ = request(url(sku="nonexistent"))
            require(status == 404, "SKU not part of paid order HTTP 404")
            for name, expiry in [
                ("past", iso(now - 10)),
                ("exact", iso(int(time.time()))),
                ("malformed", "not-a-date"),
                ("blank", ""),
            ]:
                item = json.loads(order_file.read_text(encoding="utf-8"))
                item["status"] = "paid"
                item["delivery"]["expires_at"] = expiry
                item["delivery"]["downloads"] = 0
                store(item)
                status, _, _ = request(url())
                require(status == 410, f"{name} expiry HTTP 410")
            missing = json.loads(order_file.read_text(encoding="utf-8"))
            del missing["delivery"]["expires_at"]
            store(missing)
            status, _, _ = request(url())
            require(status == 410, "missing expiry HTTP 410; no unlimited legacy URL")
            unpaid = json.loads(order_file.read_text(encoding="utf-8"))
            unpaid["status"] = "pending"
            unpaid["delivery"]["expires_at"] = iso(int(time.time()) + 3600)
            store(unpaid)
            status, _, _ = request(url())
            require(status == 403, "unpaid HTTP 403")
            maximum = dict(unpaid)
            maximum["status"] = "paid"
            maximum["delivery"]["downloads"] = 30
            store(maximum)
            status, _, _ = request(url())
            require(status == 429, "maximum downloads HTTP 429")
            status, _, _ = request(url(order_id="order_20261016_080000_unknown"))
            require(status == 404, "unrecognized order HTTP 404")
            print("HTTP_DOWNLOAD_EXPIRY_GATE=PASS 13 CHECKS (NO PAYMENTS)", flush=True)
        finally:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)


if __name__ == "__main__":
    run()
