import json

from orjson import dumps as old_dumps


def dumps(*args, **kwargs):
    return old_dumps(args[0]).decode('utf-8')


json.dumps = dumps
