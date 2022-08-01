import asyncio
import json


async def heart_beat(log, ws):
    # while True:
    # async with websockets.connect('wss://asueeer.com/ws?mock_login=123') as websocket:
    data = {"msg": {"type": 0, "text": "ping"}}
    s = json.dumps(data, ensure_ascii=False)
    await ws.send(s)
    response_str = await ws.recv()
    log.info(response_str)
    # print(response_str)
    await asyncio.sleep(10)


def call_heart_beat(log, websocket):
    asyncio.get_event_loop().run_until_complete(heart_beat(log, ws=websocket))
    asyncio.get_event_loop().run_forever()
