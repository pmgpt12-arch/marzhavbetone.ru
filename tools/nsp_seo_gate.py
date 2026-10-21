#!/usr/bin/env python3
"""Fail-closed SEO gate for new-domain deployments. No network or secrets."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://nastoronepodryadchika.ru"
errors = []
robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
if re.search(r"(?im)^\s*Disallow:\s*/\s*$", robots):
    errors.append("robots blocks entire site")
if f"Sitemap: {DOMAIN}/sitemap.xml" not in robots:
    errors.append("new-domain sitemap directive missing")
ht = (ROOT / ".htaccess").read_text(encoding="utf-8")
if "Header always set X-Robots-Tag \"noindex" in ht or "R=503" in ht:
    errors.append("migration block present in .htaccess")
xml = ET.parse(ROOT / "sitemap.xml").getroot()
urls = [e.text.strip() for e in xml.findall(".//{*}loc") if e.text]
if len(urls) < 82 or len(urls) != len(set(urls)):
    errors.append("sitemap URL count/uniqueness invalid")
for url in urls:
    if not url.startswith(DOMAIN + "/"):
        errors.append(f"foreign sitemap host: {url}")
        continue
    path = unquote(urlsplit(url).path).lstrip("/")
    if not path or path.endswith("/"):
        path += "index.html"
    if ".." in Path(path).parts or not path.endswith(".html"):
        errors.append(f"unsafe sitemap path: {path}")
        continue
    file = ROOT / path
    if not file.is_file():
        errors.append(f"missing sitemap file: {path}")
        continue
    content = file.read_text(encoding="utf-8")
    canonical = re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', content, re.I)
    target = re.search(r'href=["\']([^"\']+)', canonical.group(0), re.I) if canonical else None
    if not target or target.group(1) != url:
        errors.append(f"canonical mismatch: {path}")
    if re.search(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', content, re.I):
        errors.append(f"noindex in sitemap: {path}")
    if 'data-nsp-staging="true"' in content:
        errors.append(f"migration banner: {path}")
test = ROOT / "test-pokupka.html"
if not test.is_file() or "noindex" not in test.read_text(encoding="utf-8").lower():
    errors.append("test checkout must remain noindex")
print("NSP_SEO_GATE_SITEMAP_URLS=", len(urls))
print("NSP_SEO_GATE_ERRORS=", len(errors))
for err in errors[:25]:
    print("NSP_SEO_GATE_ERROR:", err)
if errors:
    sys.exit(1)
print("NSP_SEO_GATE=PASS")
