"""The web renders the spice panel from fixtures; they must be what the server answers today (refresh them with
scripts/engine-fixture.sh)."""
import json
import pathlib

from engine_fixtures import REPO, build


def test_the_web_fixtures_are_what_the_engine_answers():
    for name, data in build().items():
        path = REPO / f'web/tests/fixtures/engine-{name}.json'
        assert path.exists(), f'{path.name} missing — run scripts/engine-fixture.sh'
        assert json.loads(path.read_text()) == json.loads(json.dumps(data, ensure_ascii=False)), \
            f'{path.name} drifted from the engine — run scripts/engine-fixture.sh'
