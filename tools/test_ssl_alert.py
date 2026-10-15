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

if __name__ == "__main__":
    unittest.main()
