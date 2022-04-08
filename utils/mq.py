import asyncio
from typing import Optional, Callable

import orjson
from aio_pika import DeliveryMode, ExchangeType, Message, connect, Connection, Channel
from aio_pika.abc import AbstractIncomingMessage

from config import config

exchange_name = 'canvas'


async def on_message(message: AbstractIncomingMessage, **kwargs) -> None:
    print(kwargs)
    async with message.process():
        print(f"[x] {message.body!r}")


class Mq:
    def __init__(self):
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None

    @property
    async def connection(self) -> Connection:
        if not self._connection:
            self._connection = await connect(config.mq_url)
        return self._connection

    async def get_channel(self) -> Channel:
        if not self._channel:
            self._channel = await (await self.connection).channel()
        return self._channel

    async def produce(self, data: dict) -> None:
        # Creating a channel
        channel = await self.get_channel()

        exchange = await channel.declare_exchange(
            exchange_name, ExchangeType.FANOUT,
        )

        message = Message(
            orjson.dumps(data),
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        # Sending the message
        await exchange.publish(message, routing_key='')

    async def consume(self, callback: Callable, *args, **kwargs) -> None:
        # Creating a channel
        channel = await self.get_channel()

        exchange = await channel.declare_exchange(
            exchange_name, ExchangeType.FANOUT,
        )

        # Declaring queue
        queue = await channel.declare_queue(exclusive=True)

        # Binding the queue to the exchange
        await queue.bind(exchange)
        # Start listening the queue
        async with queue.iterator() as q:
            async for message in q:
                message: AbstractIncomingMessage
                await callback(message.body.decode('utf-8'), *args, **kwargs)


async def main():
    mq = Mq()
    # await mq.consume()


if __name__ == '__main__':
    asyncio.run(main())
