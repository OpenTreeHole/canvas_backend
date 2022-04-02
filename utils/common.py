import base64
import io

import numpy as np
from PIL import Image
from aiocache import cached

from config import config
from models import Pixel


def to_rgb(s: str) -> list[int]:
    assert len(s) >= 6
    return np.array([
        int(s[:2], base=16),
        int(s[2:4], base=16),
        int(s[4:6], base=16),
    ], dtype='uint8')


@cached(ttl=10, alias='default')
async def generate_image() -> str:
    pixels = await Pixel.all().values_list('color', flat=True)
    size = config.canvas_size
    li = np.array(list(map(to_rgb, pixels))).reshape(size, size, 3)
    img = Image.fromarray(li)
    bytes_io = io.BytesIO()
    img.save(bytes_io, 'png')
    return base64.b64encode(bytes_io.getvalue()).decode()
