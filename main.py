import __init__

print(__init__.__name__)
import io

from broadcaster import Broadcast
from starlette.concurrency import run_until_first_complete
from starlette.responses import StreamingResponse

from json import JSONDecodeError

from fastapi import FastAPI, Depends
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

app = FastAPI()  # app 实例化位于所有导入之前
from config import config
from schemas import Coordinate, PixelModel, ModifyPixel
from utils.orm import serialize, get_object_or_404
from models import Pixel
from utils.common import generate_image


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
    bytes_io = io.BytesIO()
    img = await generate_image()
    img.save(bytes_io, 'png')
    bytes_io.seek(0)
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
    await broadcast.publish(channel='place', message=data)
    return data


broadcast = Broadcast(config.broadcast_url)


async def on_receive(websocket: WebSocket):
    async for data in websocket.iter_json():
        await broadcast.publish(channel='place', message=data)


async def on_publish(websocket: WebSocket):
    async with broadcast.subscribe(channel='place') as subscriber:
        async for event in subscriber:
            await websocket.send_json(event.message)


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    async def on_connect():
        await websocket.accept()

    async def on_disconnect():
        pass

    try:
        await on_connect()
        await run_until_first_complete(
            (on_receive, {'websocket': websocket}),
            (on_publish, {'websocket': websocket}),
        )
    except WebSocketDisconnect:
        await on_disconnect()
    except JSONDecodeError:
        await websocket.send_json({'message': 'data must be in json format'})
        await websocket.close()
