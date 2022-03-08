import asyncio
import json
from multiprocessing import Pipe, Process

import gensim
import websockets

from conf.config import get_config
from gov.running_steward import simulation_epoch
from message_sender import messageSender

pipes_dict = {}
end_flag = "END"


async def main_logic(para, mod):
    response_json = '''
        {"type":101,"msg":{"conv_id":"1475055770457346048"}}
        '''
    user_json = json.loads(response_json)

    while True:
        async with websockets.connect('wss://asueeer.com/ws?mock_login=123') as websocket:
            # await websocket.send('{"type":0, "msg": "123"}')  # 测试接口
            response = await websocket.recv()

            # for res in test_text:
            # response = res
            user_json = json.loads(response)
            msg_type = user_json['type']
            msg = user_json['msg']
            conv_id = msg['conv_id']
            print(user_json)
            # 首次询问
            if conv_id not in pipes_dict:
                print("new conv")
                user_pipe, response_pipe = Pipe(), Pipe()
                pipes_dict[conv_id] = [user_pipe, response_pipe]
                Process(target=simulation_epoch, args=((user_pipe[1], response_pipe[0]), para, mod)).start()
                # Process(target=messageSender, args=(conv_id, end_flag, response_pipe[1], user_pipe[0])).start()
            else:
                user_pipe, response_pipe = pipes_dict[conv_id]
                user_text = msg['content']
                # 初始化会话后 向模型发送判断以及描述（包括此后的判断以及补充描述
                user_pipe[0].send(user_text)
                recv = response_pipe[1].recv()
                # 从模型接收模型的消息 消息格式为
                """
                {
                    "service": agent_action["inform_slots"]["service"] or ,   service为业务名
                    "end_flag": episode_over  会话是否结束
                }
                """
                # 没结束 继续输入
                if recv['end_flag'] is not True:
                    msg = recv['service']
                    messageSender(conv_id, msg)
                # 结束关闭管道
                else:
                    user_pipe[0].close()
                    response_pipe[1].close()
                    # todo: service_name
                    service_name = recv['service']
                    print(service_name)
                    break


if __name__ == '__main__':
    model = gensim.models.Word2Vec.load('data/wb.text.model')
    config_file = './conf/settings.yaml'
    parameter = get_config(config_file)
    asyncio.get_event_loop().run_until_complete(main_logic(parameter, model))
