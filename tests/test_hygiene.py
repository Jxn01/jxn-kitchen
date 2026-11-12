"""Repo hygiene guards: no secrets, no venv/node_modules in the shared tree.

They run as plain unittest TestCases so both `pytest` and `python -m unittest` collect them.
Each pattern has a positive control so a guard that stopped biting fails loudly.
"""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SECRET_NAMES = re.compile(
    r'(^|/)(\.env(\.[^/]*)?|[^/]*\.(pem|key|token)|\.ha-token|kitchen\.env|credentials[^/]*)$', re.I)
SECRET_TEXT = [
    re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}'),  # JWT (HA tokens are JWTs)
    re.compile(r'DefaultPassword"?\s*[=:]\s*"?[^"\s]'),                            # Winlogon autologon password
    re.compile(r'HA_TOKEN\s*=\s*[A-Za-z0-9._-]{20,}'),                               # a filled-in env line (not a <placeholder>)
]


def candidate_files():
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-co', '--exclude-standard'],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


class Hygiene(unittest.TestCase):
    def test_no_secret_named_files(self):
        bad = [f for f in candidate_files() if SECRET_NAMES.search(f) and not f.endswith('.example')]
        self.assertEqual(bad, [])

    def test_no_secret_text(self):
        bad = []
        for f in candidate_files():
            p = ROOT / f
            if not p.is_file() or p.stat().st_size > 2_000_000:
                continue
            text = p.read_bytes().decode('utf-8', errors='ignore')
            if '\x00' in text[:4096]:          # UTF-16 (e.g. reg export) -> decode properly
                text = p.read_bytes().decode('utf-16', errors='ignore')
            if any(rx.search(text) for rx in SECRET_TEXT) and not f.startswith('tests/'):
                bad.append(f)
        self.assertEqual(bad, [])

    def test_no_venv_or_node_modules_in_tree(self):
        self.assertEqual([str(p) for p in ROOT.rglob('pyvenv.cfg')], [])
        self.assertEqual([str(p) for p in ROOT.rglob('node_modules')], [])

    def test_positive_controls(self):
        self.assertTrue(SECRET_NAMES.search('deploy/kitchen.env'))
        self.assertTrue(SECRET_NAMES.search('.env.bak-20260910'))
        self.assertFalse(SECRET_NAMES.search('deploy/kitchen.env.example'.removesuffix('.example') + 'x'))
        jwt = 'ey' + 'J' + 'a' * 24 + '.' + 'b' * 24 + '.' + 'c' * 12   # built at runtime: never a literal JWT on disk
        self.assertTrue(SECRET_TEXT[0].search(jwt))
        self.assertTrue(SECRET_TEXT[1].search('"DefaultPassword"="hunter2"'))
        self.assertTrue(SECRET_TEXT[2].search('HA_TOKEN=abcdefghijklmnopqrstuvwxyz0123'))
        self.assertFalse(SECRET_TEXT[2].search('HA_TOKEN=<a long-lived token>'))




class DeployShipsOnlyGitVisibleFiles(unittest.TestCase):
    """deploy.sh must build its file set from git (ignored secrets never leave the machine), never rsync the tree."""

    def test_deploy_uses_git_ls_files(self):
        text = (ROOT / 'deploy.sh').read_text()
        self.assertIn('ls-files -z --cached --others --exclude-standard', text)
        self.assertNotRegex(text, r'rsync[^\n]*"\$REPO/"\s+"\$HOST')

    def test_dockerignore_blocks_secrets(self):
        text = (ROOT / '.dockerignore').read_text()
        for pattern in ('**/.env', '**/*.token', '**/kitchen.env'):
            self.assertIn(pattern, text)


class OneWebBuild(unittest.TestCase):
    """The scratch build and the Docker image must build the same things (the app AND the Browse overlay): both run
    `npm run build`, which is the only place the build steps are listed."""
    def test_same_build_command(self):
        import json
        build = json.loads((ROOT / 'web/package.json').read_text())['scripts']['build']
        self.assertIn('vite.overlay.config.ts', build)
        self.assertIn('npm run build', (ROOT / 'scripts/build-web.sh').read_text())
        self.assertIn('npm run build', (ROOT / 'deploy/Dockerfile').read_text())
        self.assertNotIn('npx vite build', (ROOT / 'deploy/Dockerfile').read_text())


class NoRawUserTextInLogs(unittest.TestCase):
    """Log injection (security review 2026-10-10): text a user or HA can influence goes into a log line as %r (control
    characters escaped), never as a bare %s. Allowed %s arguments are listed here by what they are."""
    SAFE_S = ('domain', 'service', 'entity_id', 'e', 'PING_WINDOW', 'r.status_code', 'n')

    def test_log_calls(self):
        import re
        bad = []
        for f in (ROOT / 'server/kitchen').glob('*.py'):
            for m in re.finditer(r'log\.(?:info|warning|error)\((.+?)\)\n', f.read_text(), re.S):
                call = m.group(1)
                fmt = re.match(r"\s*'([^']*)'", call)
                if not fmt or '%s' not in fmt.group(1):
                    continue
                args = [a.strip() for a in call[fmt.end():].split(',') if a.strip()]
                specs = re.findall(r'%[srd]', fmt.group(1))
                for spec, arg in zip(specs, args):
                    if spec == '%s' and arg not in self.SAFE_S:
                        bad.append(f'{f.name}: {arg}')
        self.assertEqual(bad, [])


class OneImageOpener(unittest.TestCase):
    """Untrusted image bytes are opened ONLY through images.open_image (format allow-list + pixel count checked before
    decoding). A second raw Image.open is how OCR shipped without the bomb guard (security review 2026-10-10)."""
    def test_no_raw_image_open(self):
        bad = [f.name for f in (ROOT / 'server/kitchen').glob('*.py')
               if f.name != 'images.py' and 'Image.open(' in f.read_text()]
        self.assertEqual(bad, [])


if __name__ == '__main__':      # at the END: anything defined after it would not run when the file is run directly
    unittest.main()


class HeadlessChromeUsesTheSharedFlags(unittest.TestCase):
    """Every headless Chrome a script starts takes scripts/chrome-flags.txt (Python: cdp.CHROME_FLAGS; screens.sh: the same
    file), and that file keeps the two flags that cost the evening of 2026-11-11: --password-store=basic (without it
    Chrome hangs forever on the locked GNOME keyring while nobody is logged in) and --disable-background-networking (a fresh
    profile's background work on the browser main thread stalled every DevTools call: 3m27s vs 43.6 s for one walk)."""
    LAUNCH = re.compile(r'--headless')

    @classmethod
    def unguarded(cls, text: str) -> int:
        """Launches whose argument list (the next ~200 characters) does not take the shared flags."""
        return sum(1 for m in cls.LAUNCH.finditer(text) if 'CHROME_FLAGS' not in text[m.start():m.start() + 200])

    def test_every_launch_takes_the_shared_flags(self):
        bad = {}
        for p in sorted((ROOT / 'scripts').glob('*')):
            if p.suffix in ('.py', '.sh') and p.is_file():
                n = self.unguarded(p.read_text(encoding='utf-8'))
                if n:
                    bad[p.name] = n
        self.assertEqual(bad, {})

    def test_the_flag_file_keeps_the_two_that_mattered(self):
        flags = [ln.strip() for ln in (ROOT / 'scripts/chrome-flags.txt').read_text().splitlines()
                 if ln.strip() and not ln.lstrip().startswith('#')]
        for f in ('--password-store=basic', '--disable-background-networking'):
            self.assertIn(f, flags)

    def test_positive_control(self):
        self.assertEqual(self.unguarded("Popen([chrome, '--headless=new', '--disable-gpu'])"), 1)
        self.assertEqual(self.unguarded("Popen([chrome, '--headless=new', *CHROME_FLAGS])"), 0)


class OneCdpClient(unittest.TestCase):
    """No script reads a Chrome DevTools websocket itself: scripts/cdp.py's Page reads it continuously on its own task.
    Reading only while awaiting a reply let Chrome's events pile up unread, and the socket's flow control then made every
    later call stall for seconds, growing (a clip-audit pass took ~7 minutes instead of ~1.5; 2026-11-11)."""
    RECV = re.compile(r'\.recv\(\)')
    ALLOWED = {
        'cdp.py': 'the client itself',
        'kiosk-measure.py': 'one call per connection, closed after its reply: nothing can pile up',
    }

    def test_no_script_reads_a_cdp_socket_itself(self):
        bad = sorted(p.name for p in (ROOT / 'scripts').glob('*.py')
                     if p.name not in self.ALLOWED and self.RECV.search(p.read_text(encoding='utf-8')))
        self.assertEqual(bad, [])

    def test_positive_control(self):
        self.assertTrue(self.RECV.search('m = json.loads(await ws.recv())'))
        self.assertFalse(self.RECV.search('async for raw in self.ws:'))
