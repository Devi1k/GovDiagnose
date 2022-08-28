import asyncio
import json
import time
from json import JSONDecodeError
from multiprocessing import Pipe, Process

import gensim
import websockets
from websockets import ConnectionClosed

from conf.config import get_config
from gov.agent_rule import AgentRule
from gov.running_steward import simulation_epoch
from utils.ai_wrapper import get_answer, get_faq
from utils.logger import *
from utils.message_sender import messageSender

log = Logger().getLogger()
count = 0

heart = {"type": 10000, "msg": "heart_beat"}


async def main_logic(para, mod, link, similarity_dict):
    global first_utterance, service_name, conv_id, end_flag, last_msg, start_time, end_time, pipes_dict
    address = 'wss://asueeer.com/ws?mock_login=123'
    async for websocket in websockets.connect(address, ping_interval=6000):
        try:
            log.info('wait message')
            response = await websocket.recv()
            log.info(response)
            try:
                user_json = json.loads(response)
            except JSONDecodeError:
                continue
            log.info(user_json)
            msg_type = user_json['type']
            msg = user_json['msg']
            conv_id = msg['conv_id']

            # First inquiry and initialize the conversation
            if conv_id not in pipes_dict:
                log.info("new conv")
                clean_log(log)
                user_pipe, response_pipe = Pipe(), Pipe()
                p = Process(target=simulation_epoch,
                            args=(
                                (user_pipe[1], response_pipe[0]), agent, para, mod, log, similarity_dict, conv_id))
                p.start()
                # send_pipe, receive_pipe, first_utterance, process, single_finish, all_finish
                pipes_dict[conv_id] = [user_pipe, response_pipe, "", p, False, False]

            # Handle multiple rounds of dialogues  Continue to speak
            elif conv_id in pipes_dict and pipes_dict[conv_id][5] is False and pipes_dict[conv_id][4] is True:
                log.info("continue to ask")
                user_pipe, response_pipe = Pipe(), Pipe()
                if 'content' not in msg.keys():
                    pipes_dict[conv_id][2] = ""
                    messageSender(conv_id, last_msg, log)
                    continue
                if pipes_dict[conv_id][2] == "":
                    pipes_dict[conv_id][2] = msg['content']['text']
                    # pipes_dict[conv_id][2] = first_utterance
                    messageSender(conv_id, "请问您询问的问题是否与上述业务相关", log)
                    continue
                if msg['content']['text'] == '是':
                    # 直接调用检索 传递上一个service_name和first_utterance
                    user_pipe[0].close()
                    response_pipe[1].close()
                    user_pipe[1].close()
                    response_pipe[0].close()
                    pipes_dict[conv_id][4] = True

                    messageSender(conv_id, "暂未支持", log, end=pipes_dict[conv_id][4])
                    pass
                else:
                    # 重新诊断
                    p = Process(target=simulation_epoch,
                                args=(
                                    (user_pipe[1], response_pipe[0]), agent, para, mod, log, similarity_dict, conv_id))
                    p.start()
                    # send_pipe, receive_pipe, first_utterance, process, single_finish, all_finish
                    pipes_dict[conv_id] = [user_pipe, response_pipe, pipes_dict[conv_id][2], p, False, False]
                    pipes_dict[conv_id][4] = False
                    pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "",
                                                    pipes_dict[conv_id][2])

                    user_text = {'text': pipes_dict[conv_id][2]}
                    log.info(user_text)
                    similar_score, answer = get_faq(pipes_dict[conv_id][2])
                    if float(similar_score) > 0.6:
                        user_pipe[0].close()
                        response_pipe[1].close()
                        user_pipe[1].close()
                        response_pipe[0].close()
                        pipes_dict[conv_id][4] = True
                        messageSender(conv_id, answer, log, end=pipes_dict[conv_id][4])
                        pipes_dict[conv_id][2] = ""
                        pipes_dict[conv_id][3].terminate()
                        # await websocket.close(code=1000, reason='finish')

                        log.info('process kill')
                        pipes_dict[conv_id][3].join()
                        # del pipes_dict[conv_id]
                        last_msg = "请问还有其他问题吗，如果有请继续提问"
                        messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=pipes_dict[conv_id][4])
                    else:
                        # After initializing the session, send judgments and descriptions to the model (including
                        # subsequent judgments and supplementary descriptions).
                        try:
                            user_pipe[0].send(user_text)
                        except OSError:
                            messageSender(conv_id, "会话结束", log, end=True)
                            continue
                        recv = response_pipe[1].recv()
                        # The message format of the model received from the model is
                        """
                        {
                            "service": agent_action["inform_slots"]["service"] or ,   service为业务名
                            "end_flag": episode_over  会话是否结束
                        }
                        """
                        pipes_dict[conv_id][4] = recv['end_flag']
                        # Continue to input without ending
                        if pipes_dict[conv_id][4] is not True and recv['action'] == 'request':
                            msg = "您办理的业务是否涉及" + recv['service'] + "业务，如果是，请输入是；如果不涉及，请进一步详细说明"
                            last_msg = msg
                            messageSender(conv_id, msg, log)
                        elif pipes_dict[conv_id][4] is True and recv['action'] == 'request':
                            # todo: Add call retrieval lookup items
                            msg = "抱歉，无法确定您想要办理的业务"
                            messageSender(conv_id, msg, log, end=False)
                            pipes_dict[conv_id][3].terminate()

                            log.info('process kill')
                            pipes_dict[conv_id][3].join()
                            del pipes_dict[conv_id]
                            last_msg = "请问还有其他问题吗，如果有请继续提问"
                            messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=pipes_dict[conv_id][4])
                        # Diagnostic results
                        else:
                            pipes_dict[conv_id][4] = True
                            user_pipe[0].close()
                            response_pipe[1].close()
                            service_name = recv['service']
                            log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                            log.info("service_name: {}".format(service_name))
                            try:
                                answer = get_answer(pipes_dict[conv_id][2], service_name, log)
                            except JSONDecodeError:
                                answer = "无法回答当前问题"
                            service_link = str(link[service_name])
                            messageSender(conv_id, answer, log, service_link, end=True)
                            pipes_dict[conv_id][2] = ""
                            pipes_dict[conv_id][3].terminate()

                            log.info('process kill')
                            pipes_dict[conv_id][3].join()
                            last_msg = "请问还有其他问题吗，如果有请继续提问"
                            messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=True, service_name=service_name)
            # First conversation
            else:
                user_pipe, response_pipe, first_utterance, p_del, single_finish_flag, all_finish_flag = pipes_dict[
                    conv_id]
                if 'content' not in msg.keys():
                    pipes_dict[conv_id][2] = ""
                    messageSender(conv_id, last_msg, log)
                    continue
                if pipes_dict[conv_id][2] == "":
                    pipes_dict[conv_id][2] = msg['content']['text']
                    # pipes_dict[conv_id][2] = first_utterance
                pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "",
                                                pipes_dict[conv_id][2])
                similar_score, answer = get_faq(pipes_dict[conv_id][2])
                if float(similar_score) > 0.6:
                    # pass
                    user_pipe[0].close()
                    response_pipe[1].close()
                    pipes_dict[conv_id][4] = True
                    messageSender(conv_id, answer, log, end=pipes_dict[conv_id][4])
                    pipes_dict[conv_id][2] = ""
                    pipes_dict[conv_id][3].terminate()
                    # await websocket.close(code=1000, reason='finish')

                    log.info('process kill')
                    pipes_dict[conv_id][3].join()
                    # del pipes_dict[conv_id]
                    last_msg = "请问还有其他问题吗，如果有请继续提问"
                    messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=pipes_dict[conv_id][4])
                else:
                    user_text = msg['content']
                    log.info(user_text)
                    try:
                        user_pipe[0].send(user_text)
                    except OSError:
                        messageSender(conv_id, "会话结束", log)
                        continue
                    recv = response_pipe[1].recv()
                    pipes_dict[conv_id][4] = recv['end_flag']
                    if pipes_dict[conv_id][4] is not True and recv['action'] == 'request':
                        msg = "您办理的业务是否涉及" + recv['service'] + "业务，如果是，请输入是；如果不涉及，请进一步详细说明"
                        last_msg = msg
                        messageSender(conv_id, msg, log)
                    elif pipes_dict[conv_id][4] is True and recv['action'] == 'request':
                        # todo: Add call retrieval lookup items
                        msg = "抱歉，无法确定您想要办理的业务"
                        pipes_dict[conv_id][4] = True
                        messageSender(conv_id, msg, log, end=False)
                        pipes_dict[conv_id][3].terminate()
                        # await websocket.close(code=1000, reason='finish')
                        log.info('process kill')
                        pipes_dict[conv_id][3].join()
                        # del pipes_dict[conv_id]
                        last_msg = "请问还有其他问题吗，如果有请继续提问"
                        messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=pipes_dict[conv_id][4])
                    else:
                        user_pipe[0].close()
                        response_pipe[1].close()
                        service_name = recv['service']
                        pipes_dict[conv_id][4] = True
                        log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                        log.info("service_name: {}".format(service_name))
                        try:
                            answer = get_answer(pipes_dict[conv_id][2], service_name, log)
                        except JSONDecodeError:
                            answer = "抱歉，无法回答当前问题"
                        service_link = str(link[service_name])
                        messageSender(conv_id, answer, log, service_link, end=pipes_dict[conv_id][4])
                        pipes_dict[conv_id][2] = ""
                        pipes_dict[conv_id][3].terminate()
                        # await websocket.close(code=1000, reason='finish')

                        # try:
                        #     os.remove(os.path.join('data','goal_set_{}.json'.format(conv_id)))
                        #     log.info('delete goal set')
                        # except FileNotFoundError:
                        #     pass
                        log.info('process kill')
                        pipes_dict[conv_id][3].join()
                        # del pipes_dict[conv_id]
                        last_msg = "请问还有其他问题吗，如果有请继续提问"
                        messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=True,
                                      service_name=service_name)
        except ConnectionClosed as e:
            log.info(e)
            continue


if __name__ == '__main__':
    start_time = time.time()
    end_time = time.time()
    end_flag = False
    pipes_dict = {}
    first_utterance, service_name = "", ""
    last_msg = ""
    log.info('load model')
    model = gensim.models.Word2Vec.load('data/wb.text.model')

    config_file = './conf/settings.yaml'
    parameter = get_config(config_file)

    link_file = 'data/link.json'
    with open(link_file, 'r') as f:
        link = json.load(f)
    # agent = AgentDQN(parameter=parameter)
    agent = AgentRule(parameter=parameter)
    with open('data/similar.json', 'r') as f:
        similarity_dict = json.load(f)
    asyncio.get_event_loop().run_until_complete(main_logic(parameter, model, link, similarity_dict))
