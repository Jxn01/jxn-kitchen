"""Recipe photos: decoded with Pillow (so only real images are stored), EXIF-rotated, shrunk to ≤ 1024 px, saved as
JPEG under <data>/images/<recipe>-<stamp>.jpg — small enough for the kiosk's 2 GB."""
from __future__ import annotations

import io
import pathlib
import re
import time

from PIL import Image, ImageOps, UnidentifiedImageError

SAFE_NAME = re.compile(r'\d+-\d+\.jpg')
MAX_SIDE = 1024
MAX_PIXELS = 40_000_000                 # ~ a 7700x5200 photo; anything bigger is refused before decoding
FORMATS = ('JPEG', 'PNG', 'WEBP', 'GIF')  # only the common photo formats: a smaller parser surface
Image.MAX_IMAGE_PIXELS = MAX_PIXELS     # Pillow's own decompression-bomb guard raises above this


SCAN_FORMATS = FORMATS + ('TIFF', 'BMP')   # scanners also write these


class BadImage(ValueError):
    pass


def open_image(data: bytes, formats: tuple[str, ...] = FORMATS, draft: int | None = None,
               load: bool = True) -> Image.Image:
    """THE way untrusted image bytes are opened (photos, scans, OCR): only the listed formats, and the pixel count
    checked from the header BEFORE anything is decoded (decompression bombs); `draft` decodes a JPEG at reduced size.
    Raises BadImage."""
    try:
        img = Image.open(io.BytesIO(data), formats=formats)     # reads the header only
        if img.width * img.height > MAX_PIXELS:
            raise BadImage('image too large')
        if draft:
            img.draft('RGB', (draft, draft))
        if load:
            img.load()
        return img
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as e:
        raise BadImage(f'not a usable image: {type(e).__name__}') from e


def store(directory: pathlib.Path, rid: int, data: bytes, formats: tuple[str, ...] = FORMATS) -> str:
    img = open_image(data, formats, draft=MAX_SIDE)
    img = ImageOps.exif_transpose(img).convert('RGB')
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    directory.mkdir(parents=True, exist_ok=True)
    name = f'{rid}-{int(time.time() * 1000)}.jpg'
    img.save(directory / name, 'JPEG', quality=82, optimize=True, progressive=True)
    return name
