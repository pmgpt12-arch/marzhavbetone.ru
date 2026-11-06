#!/usr/bin/env python3
"""T2/T3 retired: deny checkout by SKU/name, no legacy delivery exemption.

Uses exact candidate PHP copied into a disposable localhost-only fixture.
No real payments, provider requests, email or production files are accessed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
T2 = "Система документального подтверждения передачи исполнительной документации"
T3 = "Система подготовки возражений на односторонний акт или списание в одностороннем порядке"
EXPECTED_PAID = {"p1", "p2", "p3", "p4", "p5", "p7", "p8", "p9", "p10", "p11", "p13"}


def php_string(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def http(port: int, route: str, payload: dict | None = None) -> tuple[int, bytes]:
    req = Request(
        f"http://127.0.0.1:{port}{route}",
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


class MockKassa(BaseHTTPRequestHandler):
    attempts = 0

    def log_message(self, *_):
        pass

    def do_POST(self):
        assert self.path == "/payments"
        MockKassa.attempts += 1
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["amount"]["currency"] == "RUB"
        data = json.dumps({
            "id": "mock_safe_local_only",
            "status": "pending",
            "confirmation": {"confirmation_url": "https://example.invalid/qa-payment"},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    assert shutil.which("php"), "PHP_NOT_AVAILABLE"
    with tempfile.TemporaryDirectory(prefix="nsp-retired-t2-t3-qa-") as tmp:
        base = Path(tmp)
        web, orders, masters = base / "web", base / "orders", base / "masters"
        for directory in (web, orders, masters):
            directory.mkdir()
        for name in ("products-config.php", "payment.php", "download.php"):
            shutil.copy2(ROOT / name, web / name)
            lint = subprocess.run(
                ["php", "-l", str(web / name)], capture_output=True, text=True, timeout=8
            )
            assert lint.returncode == 0, (name, lint.stderr)

        mock = ThreadingHTTPServer(("127.0.0.1", 0), MockKassa)
        Thread(target=mock.serve_forever, daemon=True).start()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            site_port = s.getsockname()[1]

        settings = {
            "ORDERS_DIR": str(orders),
            "PRODUCTS_DIR": str(masters),
            "SITE_URL": f"http://127.0.0.1:{site_port}",
            "ADMIN_EMAIL": "qa@example.invalid",
            "YOOKASSA_SHOP_ID": "synthetic_mock",
            "YOOKASSA_SECRET_KEY": "synthetic_local_only",
            "YOOKASSA_MODE": "test",
            "YOOKASSA_API_URL": f"http://127.0.0.1:{mock.server_port}",
        }
        (web / "config.php").write_text(
            "<?php\n" + "".join(
                f"define({php_string(k)},{php_string(v)});\n"
                for k, v in settings.items()
            )
        )

        code = (
            "require " + php_string(str(web / "config.php")) + ";"
            "require " + php_string(str(web / "products-config.php")) + ";"
            "$c=mvb_products();"
            "$r=[];"
            "foreach(['t2','t3'] as $id){"
            " $r['retired_not_in_catalog'][$id]=!isset($c[$id]);"
            " $r['retired_resolver_reject'][$id]=mvb_resolve_product(['sku'=>$id])===null;"
            " $r['retired_archive_reject'][$id]=mvb_build_product_zip($id)===null;"
            "}"
            "$r['by_t2_name']=mvb_resolve_product(['name'=>" + php_string(T2) + "])===null;"
            "$r['by_t3_name']=mvb_resolve_product(['name'=>" + php_string(T3) + "])===null;"
            "$r['mixed_sku_p4_name']=mvb_resolve_product("
            " ['sku'=>'t2','name'=>$c['p4']['name']])===null;"
            "$r['p4_ok']=mvb_resolve_product(['sku'=>'p4'])!==null;"
            "$r['p5_ok']=mvb_resolve_product(['sku'=>'p5'])!==null;"
            "$r['test1_price']=mvb_resolve_product(['sku'=>'test1'])['price'];"
            "$r['active_paid']=array_values(array_filter(array_keys($c),"
            " static fn($k)=>preg_match('/^p\\d+$/',$k) && "
            "mvb_resolve_product(['sku'=>$k])!==null));"
            "$r['ttl_seconds']=DELIVERY_TTL_SECONDS;"
            "echo json_encode($r,JSON_UNESCAPED_UNICODE);"
        )
        unit = subprocess.run(["php", "-r", code], capture_output=True, timeout=12)
        assert unit.returncode == 0, unit.stderr.decode(errors="replace")
        facts = json.loads(unit.stdout)
        assert all(facts["retired_not_in_catalog"].values())
        assert all(facts["retired_resolver_reject"].values())
        assert all(facts["retired_archive_reject"].values())
        assert facts["by_t2_name"] and facts["by_t3_name"]
        assert facts["mixed_sku_p4_name"]
        assert facts["p4_ok"] and facts["p5_ok"] and facts["test1_price"] == 100
        assert set(facts["active_paid"]) == EXPECTED_PAID
        assert facts["ttl_seconds"] == 3600

        with (base / "php.log").open("wb") as log:
            server = subprocess.Popen(
                ["php", "-d", "sendmail_path=/bin/false",
                 "-S", f"127.0.0.1:{site_port}", "-t", str(web)],
                stdout=log, stderr=log,
            )
            try:
                for _ in range(70):
                    try:
                        with socket.create_connection(
                            ("127.0.0.1", site_port), timeout=.2
                        ):
                            break
                    except OSError:
                        time.sleep(.05)
                else:
                    raise AssertionError("LOCAL_PHP_NOT_READY")

                cases = [
                    [{"sku": "t2"}],
                    [{"sku": "t3"}],
                    [{"name": T2}],
                    [{"name": T3}],
                    [{"sku": "t2", "name": "Система ведения, проверки и передачи исполнительной документации"}],
                    [{"sku": "t3", "name": "Система защиты подрядчика от претензий, штрафов, удержаний и зачётов"}],
                    [{"sku": "p4"}, {"sku": "t2"}],
                    [{"sku": "test1"}, {"sku": "t3"}],
                ]
                for items in cases:
                    status, body = http(site_port, "/payment.php", {
                        "email": "qa@example.invalid",
                        "items": items,
                    })
                    assert status == 422, (items, status, body[:160])
                    assert not json.loads(body)["ok"]
                    assert not list(orders.glob("order_*.json"))
                    assert MockKassa.attempts == 0, "PROVIDER_CALLED_FOR_RETIRED"

                # Positive control: existing 1-ruble synthetic test SKU still
                # creates a LOCAL mocked payment and never reaches YooKassa.
                status, body = http(site_port, "/payment.php", {
                    "email": "qa@example.invalid",
                    "items": [{"sku": "test1"}],
                })
                assert status == 200, (status, body[:150])
                result = json.loads(body)
                assert result["ok"] and result["payment_url"].endswith("/qa-payment")
                assert MockKassa.attempts == 1
                assert len(list(orders.glob("order_*.json"))) == 1
                order = json.loads(next(orders.glob("order_*.json")).read_text())
                assert order["total"] == 100 and order["items"][0]["sku"] == "test1"

                # One-hour expiry is enforced by download.php: a paid,
                # valid-token synthetic expired order must return 410.
                old_order_id = "order_20261106_000000_synth1"
                (orders / (old_order_id + ".json")).write_text(json.dumps({
                    "id": old_order_id,
                    "status": "paid",
                    "items": [{"sku": "p4"}],
                    "delivery": {
                        "token": "qa_expired_test_only",
                        "expires_at": "2000-01-01T00:00:00+00:00",
                        "downloads": 0,
                        "items": {"p4": "no_archive_needed_for_expiry.zip"},
                    },
                }))
                code, _ = http(
                    site_port,
                    f"/download.php?o={old_order_id}&t=qa_expired_test_only&f=p4",
                )
                assert code == 410, "EXPIRED_LINK_NOT_REJECTED"
                old_data = json.loads((orders / (old_order_id + ".json")).read_text())
                assert old_data["delivery"]["downloads"] == 0

                print(json.dumps({
                    "status": "PASS",
                    "paid_sku_count": len(EXPECTED_PAID),
                    "retired_skus_denied": ["t2", "t3"],
                    "retired_checkout_negative_cases": len(cases),
                    "positive_control": "test1_local_mock_1_ruble_PASS",
                    "historical_access_preservation": "NOT_REQUIRED",
                    "link_ttl_seconds": facts["ttl_seconds"],
                    "expired_download_http": code,
                    "real_payment_calls": 0,
                    "real_emails_sent": 0,
                    "production_writes": 0,
                }, ensure_ascii=False))
            finally:
                server.terminate()
                server.wait(timeout=5)
                mock.shutdown()
                mock.server_close()


if __name__ == "__main__":
    main()
