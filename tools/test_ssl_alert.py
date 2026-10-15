#!/usr/bin/env python3
"""Mock alert decision suite: no GitHub writes."""
import unittest
import ssl_alert as alert

class AlertRegressions(unittest.TestCase):
    def row(self, state):
        return {"status": state, "hosts": [
            {"host": "nastoronepodryadchika.ru", "status": state, "errors": []},
            {"host": "www.nastoronepodryadchika.ru", "status": state, "errors": []}]}
    def test_open_warning(self):
        self.assertEqual(alert.decide(self.row("WARNING"), None), "open")
    def test_open_critical(self):
        self.assertEqual(alert.decide(self.row("CRITICAL"), None), "open")
    def test_warn_dedupe(self):
        self.assertEqual(alert.decide(self.row("WARNING"), {"body": "Severity: WARNING"}), "none")
    def test_critical_escalates(self):
        self.assertEqual(alert.decide(self.row("CRITICAL"), {"body": "Severity: WARNING"}), "escalate")
    def test_critical_dedupe(self):
        self.assertEqual(alert.decide(self.row("CRITICAL"), {"body": "Severity: CRITICAL"}), "none")
    def test_recovery_closes(self):
        self.assertEqual(alert.decide(self.row("OK"), {"body": "Severity: CRITICAL"}), "close")
    def test_recovered_and_no_issue(self):
        self.assertEqual(alert.decide(self.row("OK"), None), "none")
    def test_bad_state_fails(self):
        with self.assertRaisesRegex(ValueError, "INVALID_MONITOR_REPORT"):
            alert.decide(self.row("UNKNOWN"), None)


class FakeAPIFlow(unittest.TestCase):
    """Prove the dispatch commands, without sending real GitHub alerts."""
    def invoke(self, status, existing):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import json
        import os
        import sys
        report = {"schema_version": 1, "checked_utc": "2026-10-15T16:00:00+00:00",
                  "status": status, "hosts": [
                  {"host": "nastoronepodryadchika.ru", "status": status, "errors": []},
                  {"host": "www.nastoronepodryadchika.ru", "status": status, "errors": []}]}
        with TemporaryDirectory() as folder:
            filepath = Path(folder) / "report.json"
            filepath.write_text(json.dumps(report), encoding="utf-8")
            with patch.object(alert, "open_monitor_issue", return_value=existing), \
                 patch.object(alert, "call_api", return_value={"html_url": "https://github.com/example"}) as call, \
                 patch.dict(os.environ, {"GITHUB_TOKEN": "fake-test-token", "GITHUB_REPOSITORY": alert.REPO}), \
                 patch.object(sys, "argv", ["ssl_alert.py", "--report", str(filepath)]):
                self.assertEqual(alert.main(), 0)
                return [x.args for x in call.call_args_list]

    def test_alert_open_mock_api(self):
        calls = self.invoke("CRITICAL", None)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1:3], ("POST", "/issues"))
        self.assertEqual(calls[0][3]["title"], alert.TITLE)

    def test_alert_escalate_mock_api(self):
        calls = self.invoke("CRITICAL", {"number": 7341, "body": "Severity: WARNING"})
        self.assertEqual(calls[0][1:3], ("POST", "/issues/7341/comments"))

    def test_alert_recovery_mock_api(self):
        calls = self.invoke("OK", {"number": 7341, "body": "Severity: CRITICAL"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1:3], ("POST", "/issues/7341/comments"))
        self.assertEqual(calls[1][1:3], ("PATCH", "/issues/7341"))
        self.assertEqual(calls[1][3]["state"], "closed")

if __name__ == "__main__":
    unittest.main()
