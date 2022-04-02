from tortoise import Model, fields

from config import config


class Pixel(Model):
    x = fields.IntField()
    y = fields.IntField()
    color = fields.CharField(max_length=16, default=config.default_color)
    modify_times = fields.IntField(default=0)
    last_modify = fields.DatetimeField(auto_now=True)
