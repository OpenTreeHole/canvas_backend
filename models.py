from tortoise import Model, fields

from config import config


class Pixel(Model):
    x = fields.IntField(index=True)
    y = fields.IntField(index=True)
    color = fields.CharField(max_length=16, default=config.default_color)
    modify_times = fields.IntField(default=0)
    modify_time = fields.DatetimeField(auto_now=True)
