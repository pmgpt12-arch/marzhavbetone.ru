"""Real Git fixture mutations: scope changes must fail before snapshot exceptions."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools import check_p3_current_site_delta as gate


class StagingScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_git('init', '-q')
        self.run_git('config', 'user.name', 'Synthetic QA')
        self.run_git('config', 'user.email', 'qa@example.invalid')
        for name in ['index.html', 'app.js', 'payment.php',
                     'products-storage/master.txt', 'downloads/free.pdf']:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('synthetic fixture\n')
        self.commit()
        self.reference = self.run_git('rev-parse', 'HEAD').strip()

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                       text=True, stderr=subprocess.DEVNULL, timeout=5)

    def commit(self):
        self.run_git('add', '.')
        self.run_git('commit', '-qm', 'fixture')

    def verify(self):
        return gate.verify_staging_source_scope(self.root, self.reference)

    def test_exact_reference(self):
        self.assertEqual(self.verify(), 5)

    def test_internal_test_change_is_allowed(self):
        p = self.root / 'tools/test_new.py'
        p.parent.mkdir()
        p.write_text('pass\n')
        self.commit()
        self.assertEqual(self.verify(), 5)

    def test_dirty_app_payment_product_and_download_are_rejected(self):
        for name in ['app.js', 'payment.php', 'products-storage/master.txt', 'downloads/free.pdf']:
            with self.subTest(path=name):
                p = self.root / name
                before = p.read_bytes()
                try:
                    p.write_text('unreviewed\n')
                    with self.assertRaisesRegex(ValueError, 'unreviewed staging worktree'):
                        self.verify()
                finally:
                    p.write_bytes(before)

    def test_committed_app_change_is_rejected(self):
        (self.root / 'app.js').write_text('unreviewed\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'unreviewed staging source delta'):
            self.verify()

    def test_untracked_php_route_is_rejected(self):
        (self.root / 'unexpected.php').write_text('<?php')
        with self.assertRaisesRegex(ValueError, 'unreviewed staging worktree'):
            self.verify()

    def test_deleted_product_is_rejected(self):
        (self.root / 'products-storage/master.txt').unlink()
        self.commit()
        with self.assertRaisesRegex(ValueError, 'unreviewed staging source delta'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
