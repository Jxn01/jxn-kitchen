"""Print the recipe pages in server/tests/fixtures/sites as JSON recipe bodies, for screenshot seeding.
Uses the importer's own extraction, offline. usage: python scripts/demo-recipes.py > recipes.json"""
import gzip
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'server'))
from kitchen import importer  # noqa: E402

SITES = pathlib.Path(__file__).resolve().parents[1] / 'server' / 'tests' / 'fixtures' / 'sites'
out = []
for f in sorted(SITES.glob('*.html.gz')):
    url = f.with_name(f.name.removesuffix('.html.gz') + '.url').read_text().strip()
    d = importer.extract(gzip.open(f, 'rt', encoding='utf-8').read(), url)
    out.append({'title': d['title'], 'servings': d['servings'] or 4, 'total_min': d['total_min'], 'source_url': url,
                'ingredients': d['ingredients'], 'steps': d['steps'], 'tags': [d['site'].split('.')[0]]})
json.dump(out, sys.stdout, ensure_ascii=False)
