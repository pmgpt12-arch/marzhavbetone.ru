#!/usr/bin/env python3
"""Isolated P1 order, mocked payment API, webhook and HTTP download at 29 900 ₽."""
import hashlib
import io
import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRICE = 2990000
SOURCE = ROOT / "products-storage/01-zakrytie-rabot"
REFERENCE = ROOT / "tools/reports/p1-final-delivery-20261008/p1-value-edition.zip"
EXCLUDE = {".htaccess", "00-PISMO-POSLE-POKUPKI.txt", "MANIFEST.md"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files(path):
    return {f.relative_to(path).as_posix(): sha(f.read_bytes())
            for f in path.rglob("*") if f.is_file() and f.name not in EXCLUDE}


def entries(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        return {n: sha(z.read(n)) for n in z.namelist() if not n.endswith("/")}


def request(port, path, payload=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as response:
        return response.code, response.read()


def main():
    assert shutil.which("php"), "PHP is required for the HTTP integration check"
    original = files(SOURCE)
    assert len(original) == 19
    assert entries(REFERENCE.read_bytes()) == original
    assert sha(REFERENCE.read_bytes()) == "7a6de2436f0896c3d59e1bd6501e9e7d7da8d59343c21e0f09aa05d47c26ed11"
    with tempfile.TemporaryDirectory(prefix="p1-price-http-") as td:
        base = Path(td)
        web, masters, orders = base / "web", base / "masters", base / "orders"
        for d in (web, masters / "01-zakrytie-rabot", orders / "delivery"):
            d.mkdir(parents=True)
        for name in ("payment.php", "products-config.php", "webhook.php", "download.php"):
            shutil.copy2(ROOT / name, web / name)
        for name in original:
            dest = masters / "01-zakrytie-rabot" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / name, dest)

        audit = []

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
                assert order["items"][0]["sku"] == "p1"
                assert order["items"][0]["price"] == PRICE and order["total"] == PRICE
                assert payload["amount"] == {"value": "29900.00", "currency": "RUB"}
                assert pinned.is_file() and sha(pinned.read_bytes()) == edition["sha256"]
                assert entries(pinned.read_bytes()) == original
                audit.append(order_id)
                self.send({"id": "mock_" + order_id, "status": "pending",
                           "confirmation": {"confirmation_url": "https://example.invalid/test"}})

            def do_GET(self):
                assert self.path.startswith("/payments/mock_")
                self.send({"id": self.path.removeprefix("/payments/"), "status": "succeeded",
                           "metadata": {"order_id": self.path.removeprefix("/payments/mock_")}})

        api = ThreadingHTTPServer(("127.0.0.1", 0), MockAPI)
        import threading
        thread = threading.Thread(target=api.serve_forever, daemon=True)
        thread.start()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        config = {"ORDERS_DIR": str(orders), "PRODUCTS_DIR": str(masters),
                  "SITE_URL": "http://127.0.0.1:%d" % port,
                  "ADMIN_EMAIL": "nobody@example.invalid", "YOOKASSA_SHOP_ID": "mock",
                  "YOOKASSA_SECRET_KEY": "mock", "YOOKASSA_MODE": "test",
                  "YOOKASSA_API_URL": "http://127.0.0.1:%d" % api.server_port}
        (web / "config.php").write_text("<?php\n" + "\n".join(
            "define(%s, %s);" % (json.dumps(k), json.dumps(v)) for k, v in config.items()))
        with (base / "php.log").open("wb") as log:
            proc = subprocess.Popen(["php", "-d", "sendmail_path=/bin/false", "-S",
                                     "127.0.0.1:%d" % port, "-t", str(web)],
                                    stdout=log, stderr=log)
            try:
                for _ in range(50):
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=.1):
                            break
                    except OSError:
                        time.sleep(.05)
                code, data = request(port, "/payment.php", {
                    "items": [{"sku": "p1", "price": 1,
                               "edition": {"zip": "forged.zip", "sha256": "0" * 64}}],
                    "phone": "synthetic test only"})
                assert code == 200, (code, data[:500])
                checkout = json.loads(data)
                assert checkout["ok"] and len(audit) == 1
                order_id = checkout["order_id"]
                order = json.loads((orders / (order_id + ".json")).read_text())
                assert order["total"] == PRICE
                code, data = request(port, "/webhook.php", {
                    "event": "payment.succeeded",
                    "object": {"id": order["payment_id"], "status": "canceled",
                               "metadata": {"order_id": "forged"}}})
                assert code == 200 and json.loads(data)["ok"], (code, data[:500])
                paid = json.loads((orders / (order_id + ".json")).read_text())
                assert paid["status"] == "paid" and "p1" in paid["delivery"]["items"]
                code, data = request(port, "/download.php?o=%s&t=%s&f=p1" %
                                     (order_id, paid["delivery"]["token"]))
                assert code == 200 and entries(data) == original
                assert sha(data) == paid["items"][0]["edition"]["sha256"]
                assert entries(data) == entries(REFERENCE.read_bytes())
                print("PASS: P1 29 900 ₽, server price, pinned 19 files, webhook, HTTP ZIP")
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                api.shutdown()
                api.server_close()


if __name__ == "__main__":
    main()
