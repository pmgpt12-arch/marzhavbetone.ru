#!/usr/bin/env python3
"""Deduplicated GitHub issue notifications for SSL monitoring."""
from __future__ import annotations
import argparse
import json
import os
import urllib.request
from pathlib import Path

REPO = "pmgpt12-arch/marzhavbetone.ru"
TITLE = "[SSL-WATCH] HTTPS/сертификат — nastoronepodryadchika.ru"
API = f"https://api.github.com/repos/{REPO}"

def decide(report: dict, open_issue: dict | None) -> str:
    status = report.get("status")
    if status not in ("OK", "WARNING", "CRITICAL"):
        raise ValueError("INVALID_MONITOR_REPORT")
    if status == "OK":
        return "close" if open_issue else "none"
    if not open_issue:
        return "open"
    current = open_issue.get("body") or ""
    old_severity = "CRITICAL" if "Severity: CRITICAL" in current else (
        "WARNING" if "Severity: WARNING" in current else "UNKNOWN")
    return "escalate" if status == "CRITICAL" and old_severity != "CRITICAL" else "none"

def render_issue(report: dict) -> str:
    items = [
        "Автоматическая проверка HTTPS. Подробный JSON сохранён как GitHub Actions artifact.",
        "", f"Severity: {report['status']}", f"Checked: {report.get('checked_utc', 'unknown')} UTC", "",
    ]
    for h in report.get("hosts", []):
        items.extend([f"### {h['host']}", f"- Status: {h['status']}",
                      f"- Days remaining: {h.get('days_left', 'unknown')}",
                      f"- Certificate expires: {h.get('expiry_utc', 'unknown')}",
                      f"- HTTP: {h.get('http_status', 'unavailable')}"])
        if h.get("origin_tls"):
            items.append("- Origin TLS: " + json.dumps(h["origin_tls"], ensure_ascii=False))
        for error in h.get("errors", []):
            items.append("- ERROR: " + error)
        items.append("")
    items.extend(["**Что делать:** проверьте HTTPS, DNS, сертификат в ispmanager и журнал Let's Encrypt.",
                  "Не запускайте слепой повторный выпуск сертификата; сначала определите первопричину.",
                  "При настоящем предупреждении проверить ежедневный workflow SSL Monitor и его artifact."])
    return "\n".join(items)

def call_api(token: str, method: str, path: str, payload: dict | None = None):
    url = API + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ssl-watch/1.0"}
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read())

def open_monitor_issue(token: str) -> dict | None:
    for page in range(1, 11):
        results = call_api(token, "GET", f"/issues?state=open&per_page=100&page={page}")
        if not isinstance(results, list):
            raise ValueError("UNEXPECTED_GITHUB_ISSUE_RESPONSE")
        for issue in results:
            if issue.get("title") == TITLE and not issue.get("pull_request"):
                return issue
        if len(results) < 100:
            return None
    raise RuntimeError("ISSUE_LIST_PAGINATION_LIMIT")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()
    report = json.loads(Path(opts.report).read_text(encoding="utf-8"))
    if report.get("schema_version") != 1 or len(report.get("hosts", [])) != 2:
        raise ValueError("BAD_MONITOR_ARTIFACT")
    if os.getenv("GITHUB_REPOSITORY", REPO) != REPO:
        raise ValueError("WRONG_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN", "")
    if opts.dry_run:
        print(json.dumps({"mode": "dry_run", "severity": report["status"],
                          "message": render_issue(report)}, ensure_ascii=False, indent=2))
        return 0
    if not token:
        raise RuntimeError("GITHUB_TOKEN_MISSING")
    found = open_monitor_issue(token)
    action = decide(report, found)
    if action == "open":
        result = call_api(token, "POST", "/issues", {"title": TITLE, "body": render_issue(report)})
        print("ALERT_CREATED", result.get("html_url"))
    elif action == "escalate":
        result = call_api(token, "POST", f"/issues/{found['number']}/comments", {"body": render_issue(report)})
        print("ALERT_ESCALATED", result.get("html_url"))
    elif action == "close":
        result = call_api(token, "POST", f"/issues/{found['number']}/comments",
                          {"body": "✅ Монитор восстановился: HTTPS и сертификаты проходят проверки. " + report.get("checked_utc", "")})
        call_api(token, "PATCH", f"/issues/{found['number']}", {"state": "closed", "state_reason": "completed"})
        print("ALERT_CLOSED", result.get("html_url"))
    else:
        print("NO_ALERT_CHANGE", report["status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
