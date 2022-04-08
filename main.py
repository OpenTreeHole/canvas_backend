import base64
import io
from json import JSONDecodeError
from typing import Optional

from aio_pika import Channel
from aiocache import caches
from aiocache.base import BaseCache
from fastapi import FastAPI, Depends
from fastapi import WebSocket, WebSocketDisconnect
from starlette.concurrency import run_until_first_complete
from starlette.responses import StreamingResponse

app = FastAPI()  # app 实例化位于所有导入之前
from config import config
from schemas import Coordinate, PixelModel, ModifyPixel
from models import Pixel
from utils.common import generate_image
from utils.orm import serialize, get_object_or_404
from utils.mq import Mq

mq = Mq()
cache: BaseCache = caches.get('default')


@app.on_event('startup')
async def start_up():
    await mq.connect()
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
    pass


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
    await mq.produce({
        'type': 'pixel',
        'data': data
    })
    return data


async def on_receive(websocket: WebSocket):
    async for data in websocket.iter_json():
        await mq.produce(data)


async def on_publish(text: str, websocket: WebSocket):
    await websocket.send_text(text)


async def update_online_users(patch: int = 1, websocket: Optional[WebSocket] = None):
    data = {
        'type': 'meta',
        'data': {
            'online': await cache.increment('canvas_online_users', patch),
            'canvas_size': config.canvas_size
        }
    }
    if websocket:
        await websocket.send_json(data)
    await mq.produce(data)


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    async def on_connect():
        await websocket.accept()
        await update_online_users(1, websocket)

    async def on_disconnect():
        await update_online_users(-1)
        if hasattr(websocket, 'channel'):
            channel: Channel = websocket.channel
            if not channel.is_closed:
                await channel.close()

    try:
        await on_connect()
        await run_until_first_complete(
            (on_receive, {'websocket': websocket}),
            (mq.consume, {'callback': on_publish, 'websocket': websocket}),
        )
        await on_disconnect()
    except JSONDecodeError:
        await websocket.send_json({'message': 'data must be in json format'})
        await on_disconnect()
        await websocket.close()
    except WebSocketDisconnect:
        print('exception')
        await on_disconnect()
