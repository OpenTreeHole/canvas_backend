from models import Pixel
from utils.orm import pqc, pmc

PixelList = pqc(Pixel, include=('id', 'x', 'y', 'color'))
Pixel = pmc(Pixel)
