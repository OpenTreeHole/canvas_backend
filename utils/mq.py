import asyncio
from typing import Optional, Callable

import orjson
from aio_pika import DeliveryMode, ExchangeType, Message, connect, Connection
from aio_pika.abc import AbstractIncomingMessage, AbstractConnection
from starlette.websockets import WebSocket

from config import config

exchange_name = 'canvas'


class Mq:
    def __init__(self):
        self.connection: Optional[Connection] = None

    async def connect(self) -> AbstractConnection:
        self.connection = await connect(config.mq_url)
        return self.connection

    async def produce(self, data: dict) -> None:
        # Creating a channel
        async with self.connection.channel() as channel:
            exchange = await channel.declare_exchange(
                exchange_name, ExchangeType.FANOUT,
            )

            message = Message(
                orjson.dumps(data),
                delivery_mode=DeliveryMode.PERSISTENT,
            )

            await exchange.publish(message, routing_key='')

    async def consume(self, callback: Callable, *args, **kwargs) -> None:
        async with self.connection.channel() as channel:
            # bind channel to websocket
            websocket: WebSocket = kwargs.get('websocket')
            setattr(websocket, 'channel', channel)

            exchange = await channel.declare_exchange(
                exchange_name, ExchangeType.FANOUT,
            )
            queue = await channel.declare_queue(exclusive=True, auto_delete=True)
            await queue.bind(exchange)
            async with queue.iterator() as q:
                async for message in q:
                    message: AbstractIncomingMessage
                    await callback(message.body.decode('utf-8'), *args, **kwargs)


async def main():
    mq = Mq()
    # await mq.consume()


if __name__ == '__main__':
    asyncio.run(main())
