from pydantic import BaseModel, Field

from config import config
from models import Pixel
from utils.orm import pqc, pmc

PixelList = pqc(Pixel, include=('id', 'x', 'y', 'color'))
PixelModel = pmc(Pixel)


class Coordinate(BaseModel):
    x: int = Field(ge=1, le=config.canvas_size, default=1)
    y: int = Field(ge=1, le=config.canvas_size, default=1)


class ModifyPixel(BaseModel):
    color: str = Field(regex=r'^[0-9,a-f]{6}$')
