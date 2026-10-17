#!/usr/bin/env python3
"""External HTTPS and origin TLS certificate monitor; Python stdlib only."""
from __future__ import annotations
import argparse
import datetime as dt
import ipaddress
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOSTS = ("nastoronepodryadchika.ru", "www.nastoronepodryadchika.ru")
TIMEOUT_S = 7

def evaluate_certificate(host: str, cert: dict, now: dt.datetime,
                         warn_days: int = 21, critical_days: int = 14) -> dict:
    if not cert or not cert.get("notAfter"):
        raise ValueError("CERT_MISSING_EXPIRY")
    if not any(kind == "DNS" for kind, _ in cert.get("subjectAltName", ())):
        raise ValueError("CERT_MISSING_SAN")
    def matches(dns_name: str) -> bool:
        name = dns_name.lower().rstrip(".")
        requested = host.lower().rstrip(".")
        if name == requested:
            return True
        if name.startswith("*."):
            suffix = name[2:]
            return requested.endswith("." + suffix) and requested.count(".") == suffix.count(".") + 1
        return False
    if not any(kind == "DNS" and matches(value) for kind, value in cert.get("subjectAltName", ())):
        raise ValueError("CERT_SAN_MISMATCH")
    seconds = ssl.cert_time_to_seconds(cert["notAfter"])
    expires = dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("UTC_CLOCK_REQUIRED")
    days = (expires - now).total_seconds() / 86400
    state = "CRITICAL" if days <= critical_days else ("WARNING" if days <= warn_days else "OK")
    return {"status": state, "expiry_utc": expires.isoformat(), "days_left": round(days, 2)}

def tls_probe(host: str, connect_ip: str | None = None) -> dict:
    if connect_ip is not None:
        ipaddress.ip_address(connect_ip)
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    with socket.create_connection((connect_ip or host, 443), timeout=TIMEOUT_S) as s:
        with context.wrap_socket(s, server_hostname=host) as tls:
            tls.settimeout(TIMEOUT_S)
            cert = tls.getpeercert()
    if not cert:
        raise ValueError("PEER_CERT_EMPTY")
    return cert

def http_probe(host: str) -> dict:
    url = f"https://{host}/"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "ContractorSSLWatch/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ssl.create_default_context()) as response:
        final_url = response.url
        destination = urllib.parse.urlsplit(final_url)
        if destination.scheme != "https" or destination.hostname not in HOSTS:
            raise ValueError("UNEXPECTED_REDIRECT_DESTINATION")
        code = response.status
        if code < 200 or code >= 400:
            raise ValueError("HTTP_STATUS_" + str(code))
        return {"http_status": code, "final_url": final_url}

def collect(now: dt.datetime, tls=tls_probe, http=http_probe,
            origin_ip: str | None = None, warn_days: int = 21,
            critical_days: int = 14) -> dict:
    rows = []
    for host in HOSTS:
        row = {"host": host, "status": "OK", "errors": []}
        try:
            cert = tls(host)
            row.update(evaluate_certificate(host, cert, now, warn_days, critical_days))
        except (OSError, ssl.SSLError, ValueError, TimeoutError) as exc:
            row["status"] = "CRITICAL"
            row["errors"].append("TLS: " + type(exc).__name__ + ": " + str(exc)[:170])
        try:
            row.update(http(host))
        except (OSError, urllib.error.URLError, ValueError, TimeoutError) as exc:
            row["status"] = "CRITICAL"
            row["errors"].append("HTTP: " + type(exc).__name__ + ": " + str(exc)[:170])
        if origin_ip:
            try:
                origin_cert = tls(host, origin_ip)
                row["origin_tls"] = evaluate_certificate(host, origin_cert, now, warn_days, critical_days)
                if row["origin_tls"]["status"] == "CRITICAL":
                    row["status"] = "CRITICAL"
                elif row["origin_tls"]["status"] == "WARNING" and row["status"] == "OK":
                    row["status"] = "WARNING"
            except (OSError, ssl.SSLError, ValueError, TimeoutError) as exc:
                row["status"] = "CRITICAL"
                row["errors"].append("ORIGIN_TLS: " + type(exc).__name__ + ": " + str(exc)[:170])
        rows.append(row)
    severity = "CRITICAL" if any(r["status"] == "CRITICAL" for r in rows) else (
        "WARNING" if any(r["status"] == "WARNING" for r in rows) else "OK")
    return {"schema_version": 1, "checked_utc": now.isoformat(), "status": severity,
            "warn_days": warn_days, "critical_days": critical_days,
            "hosts": rows, "origin_checked": bool(origin_ip)}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="ssl-watch-report.json")
    parser.add_argument("--origin-ip", default=os.getenv("SSL_ORIGIN_IP", ""))
    parser.add_argument("--warn-days", type=int, default=21)
    parser.add_argument("--critical-days", type=int, default=14)
    args = parser.parse_args()
    if not 0 <= args.critical_days < args.warn_days:
        parser.error("Require 0 <= critical-days < warn-days")
    now = dt.datetime.now(dt.timezone.utc)
    result = collect(now, origin_ip=args.origin_ip or None,
                     warn_days=args.warn_days, critical_days=args.critical_days)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "OK" else 2

if __name__ == "__main__":
    sys.exit(main())
