import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).parents[1]
sys.path.insert(0, str(TOOLS))
import p1_production_inventory as I
import run_p1_inventory_ssh as T
sys.path.pop(0)
SECRET = 'DO_NOT_LOG_HOST_USER_KEY_PATH_OR_ORDER_ID'
REVIEW_BRANCH = 'codex/p1-production-inventory-reviewed-20261008'
REVIEW_TOKENS = (
    'ROOT_APPROVAL_STATUS: APPROVED_ONCE',
    'ROOT_APPROVAL_BRANCH: ' + REVIEW_BRANCH,
    'ROOT_APPROVAL_IMPLEMENTATION: 4c787439170e211d967920a2517c758b4d1a8c81',
    'ROOT_APPROVAL_MAX_PRODUCTION_ATTEMPTS: 1',
    'ROOT_APPROVAL_LEGAL_BATCH: EXACT_FIVE_KNOWN_URLS_ONCE',
)


def optional_gate_valid(workflow, review):
    disabled = "RUN_LEGAL_SOURCE_BATCH: 'false'" in workflow
    enabled = "RUN_LEGAL_SOURCE_BATCH: 'true'" in workflow
    if disabled == enabled:
        return False
    if disabled:
        return True
    return all(token in review.splitlines() for token in REVIEW_TOKENS)



class TransportTests(unittest.TestCase):
    def sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'orders').mkdir()
            (root / 'config.php').write_text("<?php define('ORDERS_DIR', __DIR__ . '/orders');")
            return I.scan(root)

    def test_real_report_validates_and_pii_or_extra_fields_are_rejected(self):
        data = self.sample()
        self.assertTrue(T.validate(data))
        data['email'] = SECRET
        self.assertFalse(T.validate(data))
        del data['email']
        data['status_counts'][SECRET] = 1
        self.assertFalse(T.validate(data))

    def test_untyped_match_false_positive_and_unknown_members_are_rejected(self):
        data = self.sample()
        data['configured_orders_dir_matches_known_path'] = 1
        self.assertFalse(T.validate(data))
        data['configured_orders_dir_matches_known_path'] = True
        data['remaining_blockers'] = [SECRET]
        self.assertFalse(T.validate(data))
        for invalid in [None, [], SECRET, {'schema_version': 1, 'status': {'private': SECRET}}]:
            self.assertFalse(T.validate(invalid))

    def test_ssh_scope_is_quoted_identity_and_batch_strict_no_retry(self):
        env = {'INVENTORY_HOST': 'host.example', 'INVENTORY_USER': 'user', 'SSH_PORT': '22',
               'SITE_PATH': "www/site;$(touch SHOULD_NEVER_EXECUTE)"}
        command = T.invocation(env)
        self.assertIn('IdentitiesOnly=yes', command)
        self.assertIn('BatchMode=yes', command)
        self.assertIn('StrictHostKeyChecking=yes', command)
        self.assertIn('ConnectionAttempts=1', command)
        self.assertEqual(command[-1], "python3 -B - 'www/site;$(touch SHOULD_NEVER_EXECUTE)'")
        for key, value in [('INVENTORY_HOST', '-oInjected'), ('INVENTORY_USER', 'user@evil'),
                           ('SSH_PORT', '0'), ('SITE_PATH', 'path\ncommand')]:
            changed = dict(env, **{key: value})
            with self.assertRaises(ValueError):
                T.invocation(changed)

    def test_stderr_and_nonjson_stdout_are_never_logged_or_artifacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                env = {'INVENTORY_HOST': 'host.example', 'INVENTORY_USER': 'user', 'SSH_PORT': '22', 'SITE_PATH': 'www/site'}
                result = mock.Mock(stdout=SECRET.encode(), stderr=SECRET.encode(), returncode=255)
                output = io.StringIO()
                with mock.patch.dict(T.os.environ, env), mock.patch.object(T.subprocess, 'run', return_value=result) as call, mock.patch('sys.stdout', output):
                    self.assertEqual(T.main(), 2)
                self.assertEqual(call.call_count, 1)
                self.assertNotIn(SECRET, output.getvalue())
                artifact = Path('inventory-output/P1_inventory_report.json').read_text()
                self.assertNotIn(SECRET, artifact)
                self.assertEqual(json.loads(artifact)['status'], 'TRANSPORT_FAILED_SANITIZED')
            finally:
                os.chdir(old)

    def test_workflow_is_branch_creation_only_enabled_requires_exact_once_root_review(self):
        workflow = (TOOLS.parent / '.github/workflows/p1-production-inventory-once.yml').read_text()
        self.assertIn('branches: [codex/p1-production-inventory-reviewed-20261008]', workflow)
        self.assertIn('github.event.created == true', workflow)
        self.assertIn('timeout-minutes: 5', workflow)
        self.assertIn('persist-credentials: false', workflow)
        for forbidden in ['workflow_dispatch:', 'schedule:', 'pull_request:', 'rsync', 'scp ', 'curl ', 'source-probe']:
            self.assertNotIn(forbidden, workflow)
        review = (TOOLS / 'reports/p1-production-inventory-20261008/ROOT_PRE_RUN_REVIEW.md').read_text()
        self.assertIn("RUN_LEGAL_SOURCE_BATCH: 'true'", workflow)
        self.assertTrue(optional_gate_valid(workflow, review))
        self.assertFalse(optional_gate_valid(workflow, ''))
        for token in REVIEW_TOKENS:
            self.assertFalse(optional_gate_valid(workflow, review.replace(token, '')))
        disabled_fixture = workflow.replace("RUN_LEGAL_SOURCE_BATCH: 'true'", "RUN_LEGAL_SOURCE_BATCH: 'false'")
        self.assertTrue(optional_gate_valid(disabled_fixture, ''))
        self.assertFalse(optional_gate_valid(workflow.replace("RUN_LEGAL_SOURCE_BATCH: 'true'", "RUN_LEGAL_SOURCE_BATCH: 'maybe'"), review))
        self.assertIn("if: env.RUN_LEGAL_SOURCE_BATCH == 'true'", workflow)
        self.assertIn("secrets.DEPLOY_PATH || 'www/marzhavbetone.ru'", workflow)


if __name__ == '__main__':
    unittest.main()
