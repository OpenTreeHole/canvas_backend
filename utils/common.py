import numpy as np
from PIL import Image

from config import config
from models import Pixel


def to_rgb(s: str) -> list[int]:
    assert len(s) >= 6
    return np.array([
        int(s[:2], base=16),
        int(s[2:4], base=16),
        int(s[4:6], base=16),
    ], dtype='uint8')


async def generate_image() -> Image:
    pixels = await Pixel.all().values_list('color', flat=True)
    size = config.canvas_size
    li = np.array(list(map(to_rgb, pixels))).reshape(size, size, 3)
    img = Image.fromarray(li)
    return img
