import io

from starlette.responses import StreamingResponse

import __init__

print(__init__.__name__)
from json import JSONDecodeError

from fastapi import FastAPI
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

app = FastAPI()  # app 实例化位于所有导入之前
from config import config
from models import Pixel
from utils.common import generate_image


# app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event('startup')
async def init_db():
    if await Pixel.all().count() > 0:
        return

    def pixels():
        for i in range(config.canvas_size):
            for j in range(config.canvas_size):
                yield Pixel(x=j + 1, y=i + 1)

    print('init data')
    await Pixel.bulk_create(pixels())
    print('init finished')


@app.get('/')
async def home():
    return {'message': 'hello world'}


@app.get('/picture')
async def get_picture():
    bytes_io = io.BytesIO()
    img = await generate_image()
    img.save(bytes_io, 'png')
    bytes_io.seek(0)
    return StreamingResponse(bytes_io, media_type='image/png')


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    async def on_connect():
        await websocket.accept()

    async def on_receive(data):
        await websocket.send_json(data)

    async def on_disconnect():
        pass

    try:
        await on_connect()
        async for data in websocket.iter_json():
            await on_receive(data)
    except WebSocketDisconnect:
        await on_disconnect()
    except JSONDecodeError:
        await websocket.send_json({'message': 'data must be in json format'})
        await websocket.close()
