import asyncio
import json
import time

from websockets import ConnectionClosedOK


async def heart_beat(log, websocket):
    while True:
        # async with websockets.connect('ws://asueeer.com:1988/ws?mock_login=123') as websocket:
        data = {"type": 0, "msg": "ping"}
        s = json.dumps(data, ensure_ascii=False)
        try:
            await websocket.send(s)
        except ConnectionClosedOK:
            pass
        # response_str = await websocket.recv()
        # log.info(response_str)
        # print(response_str)
        time.sleep(20)


def call_heart_beat(log, ws):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    asyncio.get_event_loop().run_until_complete(heart_beat(log, ws))
