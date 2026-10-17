#!/usr/bin/env python3
"""No-network negative-path regression suite for the SSL monitor."""
import datetime as dt
import ssl
import unittest
import ssl_watch as watch

NOW = dt.datetime(2026, 12, 1, tzinfo=dt.timezone.utc)

def cert(host, days):
    end = NOW + dt.timedelta(days=days)
    return {"notAfter": end.strftime("%b %d %H:%M:%S %Y GMT"),
            "subjectAltName": (("DNS", host),)}

def good_http(host):
    return {"http_status": 200, "final_url": "https://" + host + "/"}

class MonitorRegressions(unittest.TestCase):
    def test_cert_valid(self):
        self.assertEqual(watch.evaluate_certificate(watch.HOSTS[0], cert(watch.HOSTS[0], 50), NOW)["status"], "OK")
    def test_22_days_passes(self):
        self.assertEqual(watch.evaluate_certificate(watch.HOSTS[0], cert(watch.HOSTS[0], 22), NOW)["status"], "OK")
    def test_21_days_warns(self):
        self.assertEqual(watch.evaluate_certificate(watch.HOSTS[0], cert(watch.HOSTS[0], 21), NOW)["status"], "WARNING")
    def test_14_days_critical(self):
        self.assertEqual(watch.evaluate_certificate(watch.HOSTS[0], cert(watch.HOSTS[0], 14), NOW)["status"], "CRITICAL")
    def test_expired_critical(self):
        self.assertEqual(watch.evaluate_certificate(watch.HOSTS[0], cert(watch.HOSTS[0], -1), NOW)["status"], "CRITICAL")
    def test_missing_san_fails(self):
        with self.assertRaisesRegex(ValueError, "CERT_MISSING_SAN"):
            watch.evaluate_certificate(watch.HOSTS[0], {"notAfter": cert(watch.HOSTS[0], 80)["notAfter"]}, NOW)
    def test_mismatched_san_fails(self):
        with self.assertRaisesRegex(ValueError, "CERT_SAN_MISMATCH"):
            watch.evaluate_certificate(watch.HOSTS[0], cert("attacker.invalid", 80), NOW)
    def test_tls_chain_error_critical(self):
        def bad_cert(host):
            raise ssl.SSLCertVerificationError("certificate verify failed")
        x = watch.collect(NOW, tls=bad_cert, http=good_http)
        self.assertEqual(x["status"], "CRITICAL")
        self.assertIn("SSLCertVerificationError", x["hosts"][0]["errors"][0])
    def test_dns_failure_critical(self):
        def bad_cert(host):
            raise OSError("Name or service not known")
        x = watch.collect(NOW, tls=bad_cert, http=good_http)
        self.assertEqual(x["status"], "CRITICAL")
        self.assertTrue(all(r["errors"] for r in x["hosts"]))
    def test_http_down_critical(self):
        def bad_http(host):
            raise TimeoutError("Connection timed out")
        x = watch.collect(NOW, tls=lambda h: cert(h, 60), http=bad_http)
        self.assertEqual(x["status"], "CRITICAL")
        self.assertTrue(all(any("HTTP:" in e for e in r["errors"]) for r in x["hosts"]))
    def test_origin_expired_causes_critical_even_public_ok(self):
        def tls(host, connect_ip=None):
            return cert(host, 5 if connect_ip else 60)
        x = watch.collect(NOW, tls=tls, http=good_http, origin_ip="37.140.192.133")
        self.assertEqual(x["status"], "CRITICAL")
        self.assertTrue(x["origin_checked"])
    def test_both_good(self):
        x = watch.collect(NOW, tls=lambda h: cert(h, 60), http=good_http)
        self.assertEqual(x["status"], "OK")
        self.assertEqual(len(x["hosts"]), 2)
    def test_public_warning_never_hidden_by_origin_ok(self):
        def tls(host, connect_ip=None):
            return cert(host, 80 if connect_ip else 20)
        x = watch.collect(NOW, tls=tls, http=good_http, origin_ip="37.140.192.133")
        self.assertEqual(x["status"], "WARNING")

if __name__ == "__main__":
    unittest.main()
