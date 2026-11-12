"""The image takes Debian's security fixes on every build, from a freshly pulled base (2026-10-26: the python:3.13-slim
base still carried a libbrotli1 vulnerable to Node2Shell, CVE-2026-111497, weeks after Debian's fix). a weekly
image refresh can rebuild this same Dockerfile with --pull and the build id the app was deployed with."""
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]


class ImageTakesSecurityUpdates(unittest.TestCase):
    def test_runtime_stage_upgrades(self):
        text = (REPO / 'deploy/Dockerfile').read_text()
        runtime = text.split('FROM python', 1)[1]          # the stage that ships, not the node build stage
        self.assertRegex(runtime, r'apt-get[^\n]*-y upgrade')

    def test_deploy_pulls_the_base(self):
        self.assertRegex((REPO / 'deploy.sh').read_text(), r'docker compose build --pull')

    def test_the_remote_build_fails_loudly(self):
        # the build is piped through tail: without pipefail a failed build looked like a success
        self.assertIn('set -o pipefail;', (REPO / 'deploy.sh').read_text())

    def test_positive_control(self):
        self.assertIsNone(re.search(r'apt-get[^\n]*-y upgrade', 'RUN apt-get update && apt-get install -y x'))


if __name__ == '__main__':
    unittest.main()
