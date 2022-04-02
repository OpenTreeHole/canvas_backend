import json

from orjson import dumps as old_dumps


def dumps(*args, **kwargs):
    return old_dumps(*args, **kwargs).decode('utf-8')


json.dumps = dumps

from fastapi import FastAPI

app = FastAPI()  # app 实例化位于所有导入之前
