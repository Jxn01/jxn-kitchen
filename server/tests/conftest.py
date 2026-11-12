import os
import pathlib

import pytest
from fastapi.testclient import TestClient

# OCR tests use the models scripts/get-tessdata.sh puts in the scratch cache (nothing system-wide)
_TESSDATA = pathlib.Path(os.environ.get('KITCHEN_SCRATCH', pathlib.Path.home() / '.cache/jxn-kitchen')) / 'tessdata'
if (_TESSDATA / 'hun.traineddata').exists() and 'TESSDATA_PREFIX' not in os.environ:
    os.environ['TESSDATA_PREFIX'] = str(_TESSDATA)

from kitchen.app import create_app
from kitchen.config import Config


@pytest.fixture
def cfg(tmp_path):
    return Config(data_dir=tmp_path, static_dir=None, ha_url=None, ha_token=None)


@pytest.fixture
def client(cfg):
    with TestClient(create_app(cfg)) as c:
        yield c
