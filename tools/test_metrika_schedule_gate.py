"""Regression gate: scheduled Metrika snapshots must be committed, manual opt-out respected."""
from pathlib import Path
import re
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


if __name__ == "__main__":
    unittest.main()
