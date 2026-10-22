"""Execute the real workflow shell against a non-networked CLI recorder."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class MetrikaReadonly(unittest.TestCase):
    def test_dispatch_side_effect_flags(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/metrika.yml').read_text())
        script = next(step['run'] for step in workflow['jobs']['snapshot']['steps']
                      if step.get('name') == 'Build snapshot')
        for create, write, expected in [
            ('false', 'false', []),
            ('true', 'false', ['--create-goals']),
            ('false', 'true', ['--write']),
            ('', '', ['--create-goals', '--write']),
        ]:
            with self.subTest(create=create, write=write), tempfile.TemporaryDirectory() as td:
                base = Path(td)
                recorder = base / 'python3'
                recorder.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$QA_ARGS"\nprintf "synthetic report\\n"\n')
                recorder.chmod(0o700)
                rendered = script.replace('${{ inputs.days || \'7\' }}', '7')
                rendered = rendered.replace('${{ inputs.write }}', write)
                rendered = rendered.replace('${{ inputs.create_goals }}', create)
                self.assertNotIn('${{', rendered)
                env = {**os.environ, 'PATH': str(base) + os.pathsep + os.environ['PATH'],
                       'QA_ARGS': str(base / 'args'), 'GITHUB_STEP_SUMMARY': str(base / 'summary')}
                # Existing workflow uses /tmp/metrika.txt. Keep the test isolated.
                rendered = rendered.replace('/tmp/metrika.txt', str(base / 'metrika.txt'))
                subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', rendered],
                               env=env, capture_output=True, check=True, timeout=5)
                self.assertEqual((base / 'args').read_text().splitlines(),
                                 ['tools/metrika_report.py', '--days', '7', *expected])


if __name__ == '__main__':
    unittest.main()
