import asyncio
import json
from json import JSONDecodeError
from multiprocessing import Pipe, Process

import gensim
import websockets

from conf.config import get_config
from gov.agent_rule import AgentRule
from gov.running_steward import simulation_epoch
from utils.ai_wrapper import get_answer, get_faq
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
    global end_flag
    global last_msg
    while True:
        async with websockets.connect('ws://asueeer.com:1988/ws?mock_login=123') as websocket:
            log.info('wait message')
            response = await websocket.recv()
            user_json = json.loads(response)
            msg_type = user_json['type']
            msg = user_json['msg']
            conv_id = msg['conv_id']
            # First inquiry and initialize the conversation
            if conv_id not in pipes_dict:
                log.info("new conv")
                clean_log(log)
                user_pipe, response_pipe = Pipe(), Pipe()
                p = Process(target=simulation_epoch,
                            args=((user_pipe[1], response_pipe[0]), agent, para, mod, log, similarity_dict, conv_id))
                p.start()
                pipes_dict[conv_id] = [user_pipe, response_pipe, "", p, end_flag]

                # Process(target=messageSender, args=(conv_id, end_flag, response_pipe[1], user_pipe[0])).start()
            # Handle multiple rounds of dialogues  Continue to speak
            elif conv_id in pipes_dict and pipes_dict[conv_id][4] is True:
                log.info("continue to ask")
                user_pipe, response_pipe = Pipe(), Pipe()
                # todo: Determine whether the label in msg is the previous business, then directly bind the business
                #  name send to retrieval, otherwise a new process will be opened.
                #  And decide whether to end the conversation according to the flag in msg to delete the goal set.
                p = Process(target=simulation_epoch,
                            args=((user_pipe[1], response_pipe[0]), agent, para, mod, log, similarity_dict, conv_id))
                p.start()
                pipes_dict[conv_id] = [user_pipe, response_pipe, "", p, False]
                pipes_dict[conv_id][4] = False
                if 'content' not in msg.keys():
                    first_utterance = ""
                    messageSender(conv_id, last_msg, log)
                    continue
                if first_utterance == "":
                    first_utterance = msg['content']['text']
                user_text = msg['content']
                log.info(user_text)
                pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "",
                                                first_utterance)
                similar_score, answer = get_faq(pipes_dict[conv_id][2])
                if float(similar_score) > 0.6:
                    user_pipe[0].close()
                    response_pipe[1].close()
                    user_pipe[1].close()
                    response_pipe[0].close()
                    pipes_dict[conv_id][4] = True
                    messageSender(conv_id, answer, log, end=pipes_dict[conv_id][4])
                    first_utterance = ""
                    pipes_dict[conv_id][3].terminate()
                    log.info('process kill')
                    pipes_dict[conv_id][3].join()
                    # del pipes_dict[conv_id]
                    last_msg = "请问还有其他问题吗"
                    messageSender(conv_id, "请问还有其他问题吗", log, "", end=pipes_dict[conv_id][4])
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
                        msg = "抱歉，无法确定您想要办理的业务"
                        messageSender(conv_id, msg, log, end=False)
                        p_del.terminate()

                        log.info('process kill')
                        p_del.join()
                        del pipes_dict[conv_id]
                        last_msg = "请问还有其他问题吗"
                        messageSender(conv_id, "请问还有其他问题吗", log, "", end=pipes_dict[conv_id][4])
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
                        first_utterance = ""
                        p_del.terminate()

                        log.info('process kill')
                        p_del.join()
                        last_msg = "请问还有其他问题吗"
                        messageSender(conv_id, "请问还有其他问题吗", log, "", end=True)
            # First conversation
            else:
                user_pipe, response_pipe, first_utterance, p_del, end_flag = pipes_dict[conv_id]
                if 'content' not in msg.keys():
                    first_utterance = ""
                    messageSender(conv_id, last_msg, log)
                    continue
                if first_utterance == "":
                    first_utterance = msg['content']['text']
                pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "",
                                                first_utterance)
                similar_score, answer = get_faq(pipes_dict[conv_id][2])
                if float(similar_score) > 0.6:
                    # pass
                    user_pipe[0].close()
                    response_pipe[1].close()
                    pipes_dict[conv_id][4] = True
                    messageSender(conv_id, answer, log, end=pipes_dict[conv_id][4])
                    first_utterance = ""
                    pipes_dict[conv_id][3].terminate()
                    log.info('process kill')
                    pipes_dict[conv_id][3].join()
                    # del pipes_dict[conv_id]
                    last_msg = "请问还有其他问题吗"
                    messageSender(conv_id, "请问还有其他问题吗", log, "", end=pipes_dict[conv_id][4])
                else:
                    user_text = msg['content']
                    log.info(user_text)
                    try:
                        user_pipe[0].send(user_text)
                    except OSError:
                        messageSender(conv_id, "会话结束", log)
                        continue
                    recv = response_pipe[1].recv()
                    # end_flag = recv['end_flag']
                    if pipes_dict[conv_id][4] is not True and recv['action'] == 'request':
                        msg = "您办理的业务是否涉及" + recv['service'] + "业务，如果是，请输入是；如果不涉及，请进一步详细说明"
                        last_msg = msg
                        messageSender(conv_id, msg, log)
                    elif pipes_dict[conv_id][4] is True and recv['action'] == 'request':
                        msg = "抱歉，无法确定您想要办理的业务"
                        messageSender(conv_id, msg, log, end=False)
                        pipes_dict[conv_id][3].terminate()
                        log.info('process kill')
                        pipes_dict[conv_id][3].join()
                        # del pipes_dict[conv_id]
                        last_msg = "请问还有其他问题吗"
                        messageSender(conv_id, "请问还有其他问题吗", log, "", end=pipes_dict[conv_id][4])
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
                            answer = "无法回答当前问题"
                        service_link = str(link[service_name])
                        messageSender(conv_id, answer, log, service_link, end=pipes_dict[conv_id][4])
                        first_utterance = ""
                        pipes_dict[conv_id][3].terminate()
                        # try:
                        #     os.remove(os.path.join('data','goal_set_{}.json'.format(conv_id)))
                        #     log.info('delete goal set')
                        # except FileNotFoundError:
                        #     pass
                        log.info('process kill')
                        pipes_dict[conv_id][3].join()
                        # del pipes_dict[conv_id]
                        last_msg = "请问还有其他问题吗"
                        messageSender(conv_id, "请问还有其他问题吗", log, "", end=pipes_dict[conv_id][4])


if __name__ == '__main__':
    Process(target=call_heart_beat, args=(log,)).start()
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
