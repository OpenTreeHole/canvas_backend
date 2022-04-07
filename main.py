import base64
from typing import Optional

from aiocache import caches
from aiocache.base import BaseCache

import __init__

print(__init__.__name__)
import io

from broadcaster import Broadcast
from starlette.concurrency import run_until_first_complete
from starlette.responses import StreamingResponse

from json import JSONDecodeError

from fastapi import FastAPI, Depends
from fastapi import WebSocket, WebSocketDisconnect

app = FastAPI()  # app 实例化位于所有导入之前
from config import config
from schemas import Coordinate, PixelModel, ModifyPixel
from utils.orm import serialize, get_object_or_404
from models import Pixel
from utils.common import generate_image

broadcast = Broadcast(config.broadcast_url)
cache: BaseCache = caches.get('default')


@app.on_event('startup')
async def start_up():
    await broadcast.connect()
    if await Pixel.all().count() > 0:
        return

    def pixels():
        for i in range(config.canvas_size):
            for j in range(config.canvas_size):
                yield Pixel(x=j + 1, y=i + 1)

    print('init data')
    await Pixel.bulk_create(pixels())
    print('init finished')


@app.on_event('shutdown')
async def shut_down():
    await broadcast.disconnect()


@app.get('/')
async def home():
    return {'message': 'hello world'}


@app.get('/picture', responses={
    200: {
        'content': {'image/png': {}},
        'description': 'Return PNG of the canvas.',
    }
})
async def get_picture():
    bytes_io = io.BytesIO(base64.b64decode(await generate_image()))
    return StreamingResponse(bytes_io, media_type='image/png')


@app.get('/pixels', response_model=PixelModel)
async def get_pixel(c: Coordinate = Depends()):
    pixel = await Pixel.filter(x=c.x, y=c.y).first()
    return await serialize(pixel, PixelModel)


@app.put('/pixels/{id}', response_model=PixelModel)
async def modify_pixel(id: int, body: ModifyPixel):
    pixel = await get_object_or_404(Pixel, id=id)
    pixel.color = body.color
    pixel.modify_times += 1
    await pixel.save()
    data = await serialize(pixel, PixelModel)
    ws_data = {
        'type': 'pixel',
        'data': data
    }
    await broadcast.publish(channel='canvas', message=ws_data)
    return data


async def on_receive(websocket: WebSocket):
    async for data in websocket.iter_json():
        await broadcast.publish(channel='canvas', message=data)


async def on_publish(websocket: WebSocket):
    async with broadcast.subscribe(channel='canvas') as subscriber:
        async for event in subscriber:
            await websocket.send_json(event.message)


async def send_meta_data(online_users: Optional[int] = None, websocket: Optional[WebSocket] = None):
    ws_data = {
        'type': 'meta',
        'data': {
            'online': online_users or await cache.get('canvas_online_users', 0),
            'canvas_size': config.canvas_size
        }
    }
    if websocket:
        await websocket.send_json(ws_data)
    await broadcast.publish(channel='canvas', message=ws_data)


async def update_online_users(patch: int = 1, websocket: Optional[WebSocket] = None):
    online_users = (await cache.get('canvas_online_users', 0)) + patch
    await cache.set('canvas_online_users', online_users)
    await send_meta_data(online_users, websocket)
    return online_users


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    async def on_connect():
        await websocket.accept()
        await update_online_users(1, websocket)

    async def on_disconnect():
        await update_online_users(-1)

    try:
        await on_connect()
        await run_until_first_complete(
            (on_receive, {'websocket': websocket}),
            (on_publish, {'websocket': websocket}),
        )
        await on_disconnect()
    except WebSocketDisconnect:
        await on_disconnect()
    except JSONDecodeError:
        await websocket.send_json({'message': 'data must be in json format'})
        await websocket.close()
