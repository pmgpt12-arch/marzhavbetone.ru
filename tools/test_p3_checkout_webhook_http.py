#!/usr/bin/env python3
"""Isolated P3 order/payment mock/webhook/HTTP download, exact 11 SHA."""
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
PRICE = 199000
SOURCE = ROOT / "products-storage/05-ks-bez-vozvrata"
REFERENCE = ROOT / "tools/candidates/p3-aosr-form-layout-20261015/P3-11-buyer-AOSR-formatted-20261015.zip"
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
    assert len(original) == 11
    assert entries(REFERENCE.read_bytes()) == original
    assert sha(REFERENCE.read_bytes()) == "955e6e0ee686f5f9e03a0dc8141c021db5667e35f195c3886f630555acd2a5b1"
    with tempfile.TemporaryDirectory(prefix="p3-payment-webhook-http-") as td:
        base = Path(td)
        web, masters, orders = base / "web", base / "masters", base / "orders"
        for d in (web, masters / "05-ks-bez-vozvrata", orders / "delivery"):
            d.mkdir(parents=True)
        for name in ("payment.php", "products-config.php", "webhook.php", "download.php"):
            shutil.copy2(ROOT / name, web / name)
        for name in original:
            dest = masters / "05-ks-bez-vozvrata" / name
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
                assert order["status"] == "pending"
                assert order["items"][0]["sku"] == "p3"
                assert order["items"][0]["price"] == PRICE and order["total"] == PRICE
                assert payload["amount"] == {"value": "1990.00", "currency": "RUB"}
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
                    "items": [{"sku": "p3", "price": 1}],
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
                assert paid["status"] == "paid" and "p3" in paid["delivery"]["items"]
                original_delivery = dict(paid["delivery"])
                notification = {"event": "payment.succeeded", "object": {
                    "id": paid["payment_id"], "status": "succeeded",
                    "metadata": {"order_id": order_id}}}
                repeat_code, repeat_data = request(port, "/webhook.php", notification)
                assert repeat_code == 200 and json.loads(repeat_data)["ok"]
                repeated = json.loads((orders / (order_id + ".json")).read_text())
                assert repeated["status"] == "paid"
                assert repeated["delivery"] == original_delivery, "duplicate webhook changed issued link"
                assert repeated["admin_notified_at"] == paid["admin_notified_at"]
                assert 3598 <= __import__("datetime").datetime.fromisoformat(paid["delivery"]["expires_at"]).timestamp() - time.time() <= 3601
                code, data = request(port, "/download.php?o=%s&t=%s&f=p3" %
                                     (order_id, paid["delivery"]["token"]))
                assert code == 200 and entries(data) == original
                assert len(entries(data)) == 11
                assert paid["delivery"]["downloads"] == 0
                after = json.loads((orders / (order_id + ".json")).read_text())
                assert after["delivery"]["downloads"] == 1
                assert entries(data) == entries(REFERENCE.read_bytes())
                # Review the actual buyer email body without invoking mail().
                php = '''require $argv[1]; require $argv[2]; $o=json_decode(file_get_contents($argv[3]),true); $p=mvb_products()["p3"]; $url=SITE_URL."/download.php?o=".$o["id"]."&t=".$o["delivery"]["token"]."&f=p3"; echo mvb_delivery_email($o,[["sku"=>"p3","name"=>$p["name"],"url"=>$url]]);'''
                message = subprocess.run(["php", "-r", php, str(web / "config.php"),
                    str(web / "products-config.php"), str(orders / (order_id + ".json"))],
                    capture_output=True, text=True, timeout=5, check=True).stdout
                assert "1 час" in message and "/download.php?o=" in message
                assert paid["delivery"]["token"] in message
                print("PASS: P3 mock API, genuine duplicate webhook, buyer email body, one-hour HTTP ZIP 11/11 SHA")
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                api.shutdown()
                api.server_close()


if __name__ == "__main__":
    main()
