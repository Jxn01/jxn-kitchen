"""The self-hosted fonts must really carry the Hungarian letters (a unicode-range only promises, the cmap proves)."""
import pathlib
import unittest

from fontTools.ttLib import TTFont

FONTS = pathlib.Path(__file__).resolve().parents[1] / 'web/public/fonts'
HU = 'őűŐŰáéíóöúüÁÉÍÓÖÚÜ'


def cmap(path):
    return set(chr(c) for c in TTFont(path).getBestCmap())


class Fonts(unittest.TestCase):
    def test_every_family_covers_hungarian_across_its_subsets(self):
        for family in ('alfa-slab-one', 'archivo'):
            chars = set()
            for f in FONTS.glob(f'{family}-*.woff2'):
                chars |= cmap(f)
            self.assertTrue(chars, family)
            missing = [c for c in HU + 'AZaz09' if c not in chars]
            self.assertEqual(missing, [], family)

    def test_licenses_shipped(self):
        for family in ('alfa-slab-one', 'archivo'):
            self.assertIn('SIL Open Font License', (FONTS / f'OFL-{family}.txt').read_text())


if __name__ == '__main__':
    unittest.main()
