"""Every file the sprite is built from must be COMMITTED.

`icons/build_sprite.py --fetch` drops each newly named OpenMoji drawing into icons/openmoji/; a commit that names the
icon in the YAML but forgets the file leaves a fresh clone unable to rebuild the sprite. It happened to the
classic-blends picker's four (taco, curry, gyros, star) on 2026-10-11 — every other test passed, because the files were
on disk. This one asks git.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'icons'))
import build_sprite  # noqa: E402


def sources() -> set[str]:
    """The repo paths build_sprite.build() reads, from the same two inputs it merges."""
    manifest = yaml.safe_load((ROOT / 'icons/manifest.yaml').read_text())['icons']
    return {f"icons/openmoji/{src['openmoji']}.svg" if 'openmoji' in src else f"icons/custom/{src['custom']}"
            for src in {**build_sprite.catalogue_icons(), **manifest}.values()}


def untracked(needed: set[str], tracked: set[str]) -> list[str]:
    return sorted(needed - tracked)


class IconSourcesCommitted(unittest.TestCase):
    def test_positive_control(self):
        self.assertEqual(untracked({'icons/openmoji/1F32E.svg', 'icons/custom/kettle.svg'}, {'icons/custom/kettle.svg'}),
                         ['icons/openmoji/1F32E.svg'])

    def test_every_source_is_tracked(self):
        r = subprocess.run(['git', '-C', str(ROOT), 'ls-files', 'icons'], capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest('not a git checkout')
        needed = sources()
        self.assertGreater(len(needed), 100)          # the sweep really saw the library and the catalogue
        self.assertEqual(untracked(needed, set(r.stdout.split())), [],
                         'git add these — the sprite is built from them')


if __name__ == '__main__':
    unittest.main()
