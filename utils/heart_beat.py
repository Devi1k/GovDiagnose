import asyncio
import json
import time

import websockets


async def heart_beat(log):
    while True:
        async with websockets.connect('ws://asueeer.com:1988/ws?mock_login=123') as websocket:
            data = {"type": 0, "msg": "ping"}
            s = json.dumps(data, ensure_ascii=False)
            await websocket.send(s)
            response_str = await websocket.recv()
            log.info(response_str)
            # print(response_str)
            time.sleep(5)


def call_heart_beat(log):
    asyncio.get_event_loop().run_until_complete(heart_beat(log))
