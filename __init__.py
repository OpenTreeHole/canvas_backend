import json

from json import dumps as old_dumps


def dumps(*args, **kwargs):
    kwargs['ensure_ascii'] = False
    return old_dumps(*args, **kwargs)


json.dumps = dumps
