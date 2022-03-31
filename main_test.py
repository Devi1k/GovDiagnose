import asyncio
import json
from multiprocessing import Pipe, Process

import gensim
import websockets

from conf.config import get_config
from gov.running_steward import simulation_epoch
from utils.ai_wrapper import get_answer
from utils.heart_beat import call_heart_beat
from utils.logger import *
from utils.message_sender import messageSender

log = Logger().getLogger()


async def main_logic(para, mod, link, similarity_dict):
    response_json = '''
        {"type":101,"msg":{"conv_id":"1475055770457346048"}}
        '''
    user_json = json.loads(response_json)

    global first_utterance
    global service_name
    global conv_id
    while True:
        async with websockets.connect('wss://asueeer.com/ws?mock_login=123') as websocket:
            # data = {"type": 101, "msg": {"conv_id": "1475055770457346048", "content": {"judge": True, "text": '护照丢了怎么办'}}}
            # s = json.dumps(data, ensure_ascii=False)
            # await websocket.send(s)  # 测试接口
            log.info('wait message')
            response = await websocket.recv()
            user_json = json.loads(response)
            msg_type = user_json['type']
            msg = user_json['msg']
            conv_id = msg['conv_id']
            # 首次询问
            if conv_id not in pipes_dict:
                log.info("new conv")
                clean_log(log)
                user_pipe, response_pipe = Pipe(), Pipe()
                p = Process(target=simulation_epoch,
                            args=((user_pipe[1], response_pipe[0]), para, mod, log, similarity_dict))
                p.start()
                pipes_dict[conv_id] = [user_pipe, response_pipe, "", p]

                # Process(target=messageSender, args=(conv_id, end_flag, response_pipe[1], user_pipe[0])).start()
            else:
                user_pipe, response_pipe, first_utterance, p_del = pipes_dict[conv_id]
                if 'content' not in msg.keys():
                    first_utterance = ""
                    messageSender(conv_id, last_msg, log)
                    continue
                if first_utterance == "":
                    first_utterance = msg['content']['text']
                pipes_dict[conv_id][2] = first_utterance
                user_text = msg['content']
                log.info(user_text)
                # 初始化会话后 向模型发送判断以及描述（包括此后的判断以及补充描述
                try:
                    user_pipe[0].send(user_text)
                except OSError:
                    messageSender(conv_id, "会话结束", log)
                    continue
                recv = response_pipe[1].recv()
                # 从模型接收模型的消息 消息格式为
                """
                {
                    "service": agent_action["inform_slots"]["service"] or ,   service为业务名
                    "end_flag": episode_over  会话是否结束
                }
                """
                # 没结束 继续输入
                if recv['end_flag'] is not True and recv['action'] == 'request':
                    msg = "您办理的业务是否涉及" + recv['service']
                    last_msg = msg
                    messageSender(conv_id, msg, log)
                # todo:未诊断出结果
                elif recv['end_flag'] is True and recv['action'] == 'request':
                    messageSender(conv_id, msg, log, end=recv['end_flag'])
                    pass
                # 诊断出结果
                else:
                    user_pipe[0].close()
                    response_pipe[1].close()
                    service_name = recv['service']
                    log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                    log.info("service_name: {}".format(service_name))
                    answer = get_answer(pipes_dict[conv_id][2], service_name, log)
                    service_link = str(link[service_name])
                    print(service_link)
                    messageSender(conv_id, answer, log, service_link, end=True)
                    first_utterance = ""
                    p_del.terminate()
                    log.info('process kill')
                    p_del.join()
                    del pipes_dict[conv_id]
                    # break


if __name__ == '__main__':
    Process(target=call_heart_beat).start()

    end_flag = "END"
    pipes_dict = {}
    first_utterance, service_name = "", ""

    log.info('load model')
    model = gensim.models.Word2Vec.load('data/wb.text.model')

    config_file = './conf/settings.yaml'
    parameter = get_config(config_file)

    link_file = 'data/link.json'
    with open(link_file, 'r') as f:
        link = json.load(f)

    with open('data/similar.json', 'r') as f:
        similarity_dict = json.load(f)
    asyncio.get_event_loop().run_until_complete(main_logic(parameter, model, link, similarity_dict))
