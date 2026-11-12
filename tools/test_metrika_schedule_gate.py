"""Regression gate: scheduled Metrika snapshots must be committed, manual opt-out respected."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/metrika.yml"


class MetrikaScheduleGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_commit_step_accepts_schedule_without_dispatch_inputs(self):
        block = re.search(
            r"(?ms)^      - name: Commit snapshot\n(.*?)(?=^      - name:|\Z)",
            self.source,
        )
        self.assertIsNotNone(block, "Commit snapshot step must exist")
        gate = re.search(r"^        if: (.*)$", block.group(1), re.M)
        self.assertIsNotNone(gate, "Commit step must have explicit gate")
        self.assertEqual(
            gate.group(1),
            "steps.check.outputs.enabled == 'true' && "
            "(github.event_name == 'schedule' || inputs.write == true)",
        )

    def test_writer_and_committer_share_schedule_default(self):
        self.assertIn(
            'if [ "${{ inputs.write }}" != "false" ]; then write="--write"; fi',
            self.source,
        )
        self.assertIn(
            "github.event_name == 'schedule' || inputs.write == true",
            self.source,
        )

    def test_only_one_commit_step(self):
        self.assertEqual(self.source.count("- name: Commit snapshot"), 1)

    def test_metrics_snapshot_push_cannot_trigger_legacy_site_deploy(self):
        self.assertIn('git commit -m "Снимок чисел сайта из Метрики за $(date -u +%F) [skip deploy]"', self.source)
        deploy = (WORKFLOW.parent / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("!contains(github.event.head_commit.message, '[skip deploy]')", deploy)

    def test_manual_report_does_not_create_provider_goals(self):
        block = re.search(r"(?ms)^      - name: Build snapshot\n(.*?)(?=^      - name:|\Z)", self.source)
        self.assertIsNotNone(block)
        commands = block.group(1)
        self.assertIn('create_goals=""', commands)
        self.assertIn('if [ "${{ github.event_name }}" = "schedule" ]; then create_goals="--create-goals"; fi', commands)
        self.assertIn('python3 tools/metrika_report.py --days "$days" $create_goals $write', commands)
        self.assertNotIn('--days "$days" --create-goals', commands)

    def test_api_failure_is_not_masked_by_tee(self):
        block = re.search(r"(?ms)^      - name: Build snapshot\n(.*?)(?=^      - name:|\Z)", self.source)
        self.assertIsNotNone(block)
        self.assertIn("set -o pipefail", block.group(1))
        self.assertIn("| tee /tmp/metrika.txt", block.group(1))

    def test_ignored_snapshot_is_committed_without_private_content(self):
        block = self.source.split("      - name: Commit snapshot", 1)[1]
        self.assertIn('snapshot="content/metrics/site-$(date -u +%F).yaml"', block)
        self.assertIn('if [ ! -f "$snapshot" ]; then', block)
        self.assertIn('git add -f -- "$snapshot"', block)
        self.assertIn('git diff --cached --quiet -- "$snapshot"', block)
        self.assertNotIn('git add content/metrics', block)
        with tempfile.TemporaryDirectory(prefix="nsp-metrika-git-fixture-") as tmp:
            root = Path(tmp)
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            (root / ".gitignore").write_text("content/\n", encoding="utf-8")
            path = "content/metrics/site-2026-11-12.yaml"
            snapshot = root / path
            snapshot.parent.mkdir(parents=True)
            snapshot.write_text("traffic:\n  visits: 0\n", encoding="utf-8")
            secret = root / "content" / "internal-secret.txt"
            secret.write_text("DO NOT PUBLISH\n", encoding="utf-8")
            ignored = subprocess.run(["git", "-C", tmp, "status", "--porcelain", "--", "content/"],
                                     check=True, capture_output=True, text=True)
            self.assertEqual(ignored.stdout.strip(), "")
            subprocess.run(["git", "-C", tmp, "add", "-f", "--", path], check=True)
            staged = subprocess.run(["git", "-C", tmp, "diff", "--cached", "--name-only"],
                                    check=True, capture_output=True, text=True)
            self.assertEqual(staged.stdout.splitlines(), [path])
            subprocess.run(["git", "-C", tmp, "-c", "user.name=qa",
                            "-c", "user.email=qa@example.invalid",
                            "commit", "-qm", "snapshot [skip deploy]", "--", path], check=True)
            committed = subprocess.run(["git", "-C", tmp, "show", "--pretty=format:",
                                        "--name-only", "HEAD"], check=True,
                                       capture_output=True, text=True)
            self.assertEqual(committed.stdout.strip(), path)
            self.assertTrue(secret.exists())


if __name__ == "__main__":
    unittest.main()
