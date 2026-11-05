#!/usr/bin/env python3
"""Isolated pinned P1 purchase → mocked YooKassa → webhook → exact ZIP download.

A 20-entry SYNTHETIC master ZIP is placed in a disposable PRODUCTS_DIR.
Only its SHA is substituted into a disposable products-config.php copy.
No commercial ZIP, real order, mail transport, or external payment is used.
"""
import hashlib
import io
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICE = 2990000
PINNED_SOURCE_SHA = "12abc5750cc7f1d223cbeb002628338e2261e85e4bd4c3d6b8988cd7da295934"
PRODUCTION_P1_SHA = "99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada"
MASTER_NAME = "P1-v1-current.zip"
ENTRY_COUNT = 20


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entries(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None, "ZIP CRC"
        return {n: sha(z.read(n)) for n in z.namelist() if not n.endswith("/")}


def synthetic_master():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("00-INSTRUKCIYA.txt", "Только синтетическая QA-инструкция, не товар.")
        for i in range(1, ENTRY_COUNT):
            z.writestr(f"{i:02d}-synthetic.txt", f"QA ONLY {i:02d}: не коммерческий документ.")
    return buf.getvalue()


def request(port, path, payload=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as response:
        return response.code, response.read()


def main():
    assert shutil.which("php"), "PHP is required"
    source = (ROOT / "products-config.php").read_bytes()
    assert sha(source) == PINNED_SOURCE_SHA, "SOURCE_VS_ACCEPTED_PRODUCTION_SHA_DRIFT"
    assert source.count(PRODUCTION_P1_SHA.encode()) == 1, "P1_PIN_OCCURRENCE_COUNT"

    master_bytes = synthetic_master()
    expected_entries = entries(master_bytes)
    assert len(expected_entries) == ENTRY_COUNT
    test_sha = sha(master_bytes)
    audit = []

    with tempfile.TemporaryDirectory(prefix="nsp-p1-pinned-price-") as td:
        base = Path(td)
        web, masters, orders = base / "web", base / "masters", base / "orders"
        for directory in (web, masters / "01-zakrytie-rabot", orders / "delivery"):
            directory.mkdir(parents=True)
        for name in ("payment.php", "products-config.php", "webhook.php", "download.php"):
            shutil.copy2(ROOT / name, web / name)

        (masters / MASTER_NAME).write_bytes(master_bytes)
        (masters / "01-zakrytie-rabot" / "untrusted-source.txt").write_text(
            "DO NOT REBUILD FROM UNPACKED SOURCES"
        )
        disposable = web / "products-config.php"
        runtime_copy = disposable.read_bytes()
        assert runtime_copy == source
        patched = runtime_copy.replace(PRODUCTION_P1_SHA.encode(), test_sha.encode())
        assert patched != runtime_copy and patched.count(test_sha.encode()) == 1
        disposable.write_bytes(patched)
        assert sha((ROOT / "products-config.php").read_bytes()) == PINNED_SOURCE_SHA

        class MockAPI(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, obj):
                data = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                assert self.path == "/payments"
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                order_id = payload["metadata"]["order_id"]
                order = json.loads((orders / (order_id + ".json")).read_text())
                edition = order["items"][0]["edition"]
                pinned = orders / "delivery" / edition["zip"]
                assert order["status"] == "pending"
                assert len(order["items"]) == 1
                assert order["items"][0]["sku"] == "p1"
                assert order["items"][0]["price"] == PRICE and order["total"] == PRICE
                assert payload["amount"] == {"value": "29900.00", "currency": "RUB"}
                assert edition == {"zip": "p1-" + test_sha + ".zip", "sha256": test_sha}
                assert pinned.is_file() and sha(pinned.read_bytes()) == test_sha
                assert entries(pinned.read_bytes()) == expected_entries
                audit.append(order_id)
                self.send({"id": "mock_" + order_id, "status": "pending",
                           "confirmation": {"confirmation_url": "https://example.invalid/test"}})

            def do_GET(self):
                assert self.path.startswith("/payments/mock_")
                self.send({"id": self.path.removeprefix("/payments/"), "status": "succeeded",
                           "metadata": {"order_id": self.path.removeprefix("/payments/mock_")}})

        api = ThreadingHTTPServer(("127.0.0.1", 0), MockAPI)
        thread = threading.Thread(target=api.serve_forever, daemon=True)
        thread.start()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        config = {
            "ORDERS_DIR": str(orders), "PRODUCTS_DIR": str(masters),
            "SITE_URL": f"http://127.0.0.1:{port}",
            "ADMIN_EMAIL": "nobody@example.invalid",
            "YOOKASSA_SHOP_ID": "mock", "YOOKASSA_SECRET_KEY": "mock",
            "YOOKASSA_MODE": "test",
            "YOOKASSA_API_URL": f"http://127.0.0.1:{api.server_port}",
            "DELIVERY_TTL_SECONDS": 3600,
        }
        (web / "config.php").write_text(
            "<?php\n" + "\n".join(
                f"define({json.dumps(k)}, {json.dumps(v)});" for k, v in config.items()
            )
        )
        with (base / "php.log").open("wb") as log:
            proc = subprocess.Popen(
                ["php", "-d", "sendmail_path=/bin/false", "-S",
                 f"127.0.0.1:{port}", "-t", str(web)],
                stdout=log, stderr=log,
            )
            try:
                for _ in range(50):
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=.1):
                            break
                    except OSError:
                        time.sleep(.05)
                else:
                    raise AssertionError("LOCAL_PHP_SERVER_NOT_READY")

                code, data = request(port, "/payment.php", {
                    "items": [{"sku": "p1", "price": 1,
                               "edition": {"zip": "forged.zip", "sha256": "0" * 64}}],
                    "phone": "synthetic test only",
                })
                assert code == 200, (code, data[:500])
                checkout = json.loads(data)
                assert checkout["ok"] and len(audit) == 1
                order_id = checkout["order_id"]
                order_path = orders / (order_id + ".json")
                order = json.loads(order_path.read_text())
                assert order["total"] == PRICE and order["items"][0]["edition"]["sha256"] == test_sha
                assert order["items"][0]["edition"]["zip"] != "forged.zip"
                assert order["status"] == "pending"

                code, data = request(port, "/webhook.php", {
                    "event": "payment.succeeded",
                    "object": {"id": order["payment_id"], "status": "canceled",
                               "metadata": {"order_id": "forged"}},
                })
                assert code == 200 and json.loads(data)["ok"], (code, data[:500])
                paid = json.loads(order_path.read_text())
                assert paid["status"] == "paid" and paid["payment_status"] == "succeeded"
                assert paid["delivery"]["items"]["p1"] == "p1-" + test_sha + ".zip"
                assert paid["delivery"]["editions"]["p1"]["sha256"] == test_sha
                token = paid["delivery"]["token"]

                code, data = request(port, f"/download.php?o={order_id}&t={token}&f=p1")
                assert code == 200, (code, data[:100])
                assert data == master_bytes and sha(data) == test_sha
                assert entries(data) == expected_entries

                # Repeated webhook and cached download retain the edition and token.
                code, _ = request(port, "/webhook.php", {
                    "event": "payment.succeeded",
                    "object": {"id": order["payment_id"], "status": "pending"},
                })
                assert code == 200
                again = json.loads(order_path.read_text())
                assert again["delivery"]["token"] == token
                assert again["delivery"]["editions"] == paid["delivery"]["editions"]
                assert again["delivery"]["items"] == paid["delivery"]["items"]
                assert again["delivery"]["downloads"] == 1
                assert len(audit) == 1, "Mock payment called twice"

                print("PASS: P1 pinned synthetic 20 files, price 29 900 ₽,"
                      " forged edition denied, webhook, replay and HTTP ZIP")
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                api.shutdown()
                api.server_close()


if __name__ == "__main__":
    main()
