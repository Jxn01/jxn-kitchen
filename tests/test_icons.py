"""The sprite must contain exactly the manifest's icons, each one the thickened, ink-recoloured OpenMoji source."""
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
import importlib.util as _u
_spec = _u.spec_from_file_location('build_sprite', ROOT / 'icons/build_sprite.py')
_bs = _u.module_from_spec(_spec); _spec.loader.exec_module(_bs)
MANIFEST = {**_bs.catalogue_icons(), **yaml.safe_load((ROOT / 'icons/manifest.yaml').read_text())['icons']}
SPRITE = (ROOT / 'web/public/sprite.svg').read_text()
SCALE = 1.7
SW = re.compile(r'stroke-width="([\d.]+)"')


def symbol(icon_id):
    m = re.search(rf'<symbol id="i-{re.escape(icon_id)}"[^>]*>(.*?)</symbol>', SPRITE, re.S)
    return m.group(1) if m else None


class Sprite(unittest.TestCase):
    def test_manifest_and_sprite_match(self):
        in_sprite = set(re.findall(r'<symbol id="i-([^"]+)"', SPRITE))
        self.assertEqual(in_sprite, set(MANIFEST))

    def test_outlines_are_thickened(self):
        for icon_id, src in MANIFEST.items():
            if 'openmoji' not in src:
                continue
            raw = (ROOT / 'icons/openmoji' / f"{src['openmoji']}.svg").read_text()
            want = {round(float(w) * SCALE, 2) for w in SW.findall(raw)}
            got = {round(float(w), 2) for w in SW.findall(symbol(icon_id))}
            self.assertEqual(got, want, icon_id)

    def test_ink_not_black_and_no_bare_ids(self):
        self.assertNotRegex(SPRITE, r'#000000|#000"|"black"')
        for sym_id, body in re.findall(r'<symbol id="(i-[^"]+)"[^>]*>(.*?)</symbol>', SPRITE, re.S):
            for inner in re.findall(r'\sid="([^"]+)"', body):
                self.assertTrue(inner.startswith(sym_id + '-'), (sym_id, inner))

    def test_custom_icons_are_thickened_too(self):
        for icon_id, src in MANIFEST.items():
            if 'custom' in src:
                raw = (ROOT / 'icons/custom' / src['custom']).read_text()
                want = {round(float(w) * SCALE, 2) for w in SW.findall(raw)}
                got = {round(float(w), 2) for w in SW.findall(symbol(icon_id))}
                self.assertEqual(got, want, icon_id)

    def test_every_icon_has_a_license_trail(self):
        self.assertIn('CC BY-SA 4.0', (ROOT / 'icons/LICENSE-OpenMoji.md').read_text())


if __name__ == '__main__':
    unittest.main()
