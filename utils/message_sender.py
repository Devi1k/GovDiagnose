import json
import time

import requests


def messageSender(conv_id, log, msg="", options=None, link="", service_name="", end=False):
    # while True:
    # recv = out_pipe.recv()
    # 从模型接收模型的消息 消息格式为
    # print("messageSender getting", recv)
    # if recv['end_flag'] is True:
    #     break
    if options is None:
        options = []
    now_time = round(time.time() * 1000)
    # msg = recv['service']
    response = {"conv_id": conv_id,
                "content": {
                    "text": msg, "link": link, "service_name": service_name, "end": end, "options": options
                    # "text": msg, "link": link, "service_name": service_name, "end": end,
                },
                "type": "text",
                "role": "sys_helper",
                "timestamp": now_time}
    response_json = json.dumps(response)
    headers = {'Content-Type': 'application/json'}
    try:
        r = requests.post("https://asueeer.com/api/im/send_message?mock_login=123", data=response_json,
                          headers=headers)
    except ConnectionError:
        r = requests.post("https://asueeer.com/api/im/send_message?mock_login=123", data=response_json,
                          headers=headers)
    log.info(response['content'])
    # except EOFError:
    #     break
