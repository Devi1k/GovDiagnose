import json
import time

import requests


def messageSender(conv_id, msg):
    while True:
        try:
            # recv = out_pipe.recv()
            # 从模型接收模型的消息 消息格式为
            # print("messageSender getting", recv)
            # if recv['end_flag'] is True:
            #     break
            now_time = round(time.time() * 1000)
            # msg = recv['service']
            response = {"conv_id": conv_id, "content": {"text": msg}, "type": "text", "timestamp": now_time}
            response_json = json.dumps(response)
            # print("sending msg", response_json)
            headers = {'Content-Type': 'application/json'}
            r = requests.post("https://asueeer.com/api/im/send_message?mock_login=123", data=response_json,
                              headers=headers)
            print(r.status_code)
        except EOFError:
            break
