import asyncio
from multiprocessing import Pipe, Process

import gensim
import websockets
from thulac import thulac
from websockets import ConnectionClosed

from conf.config import get_config
from gov.agent_rule import AgentRule
from gov.running_steward import simulation_epoch
from utils.ai_wrapper import *
from utils.logger import *
from utils.message_sender import messageSender
from utils.word_match import is_multi_round, lev, longestCommonSubsequence, sigmoid, load_dict, replace_list

log = Logger().getLogger()
count = 0

heart = {"type": 10000, "msg": "heart_beat"}


async def main_logic(para, link, similarity_dict):
    global first_utterance, service_name, conv_id, end_flag, \
        start_time, end_time, pipes_dict, positive_list, stop_words, \
        thu, word_dict, model, blur_service
    address = 'wss://asueeer.com/ws?mock_login=123'
    async for websocket in websockets.connect(address, ping_interval=12000):
        try:
            # log.info('wait message')
            response = await websocket.recv()
            # log.info(response)
            try:
                user_json = json.loads(response)
            except JSONDecodeError:
                continue
            # log.info(user_json)
            msg = user_json['msg']
            conv_id = msg['conv_id']
            if 'content' in msg.keys():
                log.info("user message:" + msg['content']['text']) if 'text' in msg['content'].keys() else log.info(
                    "user choice:" + msg['content']['service_name'])
            try:
                if msg['content']['service_name'] is not None:
                    service_name = msg['content']['service_name']
                    if service_name != '以上都不是' and pipes_dict[conv_id][9] != 0:
                        pipes_dict[conv_id][7] = service_name
                        pipes_dict[conv_id][8] = return_answer(pipes_dict=pipes_dict, conv_id=conv_id,
                                                               service_name=service_name,
                                                               log=log,
                                                               link=link)

                        continue
                    elif service_name == '以上都不是' and pipes_dict[conv_id][9] > 1:
                        pipes_dict[conv_id][4] = True
                        pipes_dict[conv_id][8] = "抱歉，未能找到您所需的事项。请问还有其他问题吗，如果有请继续提问。"
                        pipes_dict[conv_id][7] = ""
                        messageSender(conv_id=conv_id, msg=pipes_dict[conv_id][8], log=log,
                                      end=pipes_dict[conv_id][4])
                        pipes_dict[conv_id][6] = True
                        pipes_dict[conv_id][2] = ""
                        pipes_dict[conv_id][3].terminate()
                        log.info('process kill')
                        pipes_dict[conv_id][3].join()
                        continue
                    elif service_name != '以上都不是' and pipes_dict[conv_id][9] == 0:
                        pipes_dict[conv_id][2] = service_name
                        pipes_dict[conv_id][10].append(pipes_dict[conv_id][2])
                        pipes_dict[conv_id][4] = True
                        pipes_dict[conv_id][6] = True
                        similarity, answer, service_name = get_faq_from_service(first_utterance=pipes_dict[conv_id][2],
                                                                                service=pipes_dict[conv_id][7])
                        pipes_dict[conv_id][7] = service_name
                        messageSender(conv_id=conv_id, msg=answer, log=log, end=pipes_dict[conv_id][4])
                        recommend = get_recommend(service_name=pipes_dict[conv_id][7],
                                                  history=pipes_dict[conv_id][10])
                        if len(recommend) < 1:
                            recommend = "请问还有其他问题吗，如果有请继续提问"
                        pipes_dict[conv_id][8] = recommend
                        if isinstance(recommend, list):
                            messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
                                          service_name=service_name, options=recommend)
                        else:
                            messageSender(conv_id=conv_id, msg=recommend, log=log, end=pipes_dict[conv_id][4])
                        pipes_dict[conv_id][2] = ""
                        pipes_dict[conv_id][9] = 0
                        continue
            except KeyError:
                pass
            try:
                # Initialize the conversation
                if conv_id not in pipes_dict:
                    clean_log()
                    user_pipe, response_pipe = Pipe(), Pipe()
                    p = Process(target=simulation_epoch,
                                args=(
                                    (user_pipe[1], response_pipe[0]), agent, para, log, similarity_dict, conv_id))
                    p.start()
                    # send_pipe, receive_pipe, first_utterance, process, single_finish, all_finish,  first_utt,
                    # service_name, last_msg, dialogue_retrieval_turn
                    log.info("new conv")
                    pipes_dict[conv_id] = [user_pipe, response_pipe, "", p, False, False, True,
                                           "", "", 0, []]
                # Handle multiple rounds of dialogues  Continue to speak
                elif conv_id in pipes_dict and pipes_dict[conv_id][5] is False and pipes_dict[conv_id][4] is True:
                    log.info("continue to ask")
                    user_pipe, response_pipe = Pipe(), Pipe()
                    if 'content' not in msg.keys():
                        messageSender(conv_id=conv_id, msg=pipes_dict[conv_id][8], log=log)
                        continue
                    multi = True
                    if pipes_dict[conv_id][2] == "":
                        try:
                            pipes_dict[conv_id][2] = msg['content']['text']
                        except KeyError:
                            pipes_dict[conv_id][2] = msg['content']['service_name']
                        pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+",
                                                        "",
                                                        pipes_dict[conv_id][2])
                        if pipes_dict[conv_id][6] is True:
                            similar_score, answer, service_name = get_faq_from_service(
                                first_utterance=pipes_dict[conv_id][2],
                                service=pipes_dict[conv_id][7])
                            pipes_dict[conv_id][6] = False
                        if float(similar_score) > 0.4211:
                            pipes_dict[conv_id][10].append(pipes_dict[conv_id][2])
                            pipes_dict[conv_id][8] = faq_diagnose(user_pipe, response_pipe, answer, pipes_dict, conv_id,
                                                                  log)
                            pipes_dict[conv_id][6] = True

                            continue
                        # Determine whether it is a multi-round conversation
                        multi, similarity = is_multi_round(pipes_dict[conv_id][2], pipes_dict[conv_id][7])
                    if multi:
                        log.info("Same matter.")
                        user_pipe[0].close()
                        response_pipe[1].close()
                        user_pipe[1].close()
                        response_pipe[0].close()
                        pipes_dict[conv_id][4] = True
                        pipes_dict[conv_id][6] = True
                        if pipes_dict[conv_id][7] not in blur_service.keys():
                            answer = get_multi_res(pipes_dict[conv_id][2], pipes_dict[conv_id][7])
                            messageSender(conv_id=conv_id, msg=answer, log=log, end=pipes_dict[conv_id][4])
                            recommend = get_recommend(service_name=pipes_dict[conv_id][7],
                                                      history=pipes_dict[conv_id][10])
                            if len(recommend) < 1:
                                recommend = "请问还有其他问题吗，如果有请继续提问"
                            pipes_dict[conv_id][8] = recommend
                            if isinstance(recommend, list):
                                messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
                                              service_name=service_name, options=recommend)
                            else:
                                messageSender(conv_id=conv_id, msg=recommend, log=log, end=pipes_dict[conv_id][4])
                            pipes_dict[conv_id][2] = ""
                            pipes_dict[conv_id][9] = 0
                        else:
                            options = get_related_title(pipes_dict[conv_id][7])
                            pipes_dict[conv_id][9] += 2
                            messageSender(conv_id=conv_id, msg="请选择与您相符的事项", log=log, options=options,
                                          end=False)
                    else:
                        log.info("Different matter")
                        # Rediagnosis
                        p = Process(target=simulation_epoch,
                                    args=(
                                        (user_pipe[1], response_pipe[0]), agent, para, log, similarity_dict,
                                        conv_id))
                        p.start()
                        # send_pipe, receive_pipe, first_utterance, process, single_finish, all_finish, first_utt,
                        # service_name, last_msg
                        pipes_dict[conv_id] = [user_pipe, response_pipe, pipes_dict[conv_id][2], p, False, False, True,
                                               "", "", 0, []]
                        pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+",
                                                        "",
                                                        pipes_dict[conv_id][2])
                        similar_score, answer = 0, ""
                        if pipes_dict[conv_id][6] is True:
                            similar_score, answer, service_name = get_faq(pipes_dict[conv_id][2])
                        user_text = {'text': pipes_dict[conv_id][2]}
                        log.info(user_text)
                        if float(similar_score) > 0.9230:
                            pipes_dict[conv_id][10].append(pipes_dict[conv_id][2])
                            pipes_dict[conv_id][8] = faq_diagnose(user_pipe, response_pipe, answer, pipes_dict, conv_id,
                                                                  log)
                            # pipes_dict[conv_id][6] = True
                        else:
                            # After initializing the session, send judgments and descriptions to the model (including
                            # subsequent judgments and supplementary descriptions).

                            # IR
                            options = get_related_title(pipes_dict[conv_id][2])
                            # todo: 待调 当前最低
                            business_threshold = 0.9102
                            candidate_service = ""
                            max_score = 0
                            for o in options:
                                lcs = longestCommonSubsequence(pipes_dict[conv_id][2], o)
                                if lcs <= 2:
                                    continue
                                distance = lev(pipes_dict[conv_id][2], o, True, True)
                                final_distance = sigmoid(lcs / len(o) + distance)
                                if max_score < final_distance:
                                    max_score = final_distance
                                    candidate_service = o
                            if max_score > business_threshold:
                                pipes_dict[conv_id][4] = True
                                pipes_dict[conv_id][6] = True
                                user_pipe[0].close()
                                response_pipe[1].close()
                                # service_name = recv['service']
                                pipes_dict[conv_id][7] = candidate_service
                                log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                                log.info("service_name: {}".format(candidate_service))
                                pipes_dict[conv_id][8] = return_answer(pipes_dict=pipes_dict, conv_id=conv_id,
                                                                       service_name=candidate_service,
                                                                       log=log,
                                                                       link=link)
                            else:
                                if pipes_dict[conv_id][6] and len(options) > 0:
                                    pipes_dict[conv_id][6] = False
                                    pipes_dict[conv_id][9] += 1
                                    messageSender(conv_id=conv_id, log=log, options=options, end=False)
                                else:
                                    if pipes_dict[conv_id][6]:
                                        pipes_dict[conv_id][6] = False
                                        pipes_dict[conv_id][9] += 1
                                    try:
                                        sentence = user_text['text']
                                        seg = thu.cut(sentence)
                                        seg_list = []
                                        for s in seg:
                                            seg_list.append(s[0])
                                        for i in range(len(seg_list) - 1, -1, -1):
                                            if seg_list[i] in stop_words:
                                                del seg_list[i]
                                        inform_slots = replace_list(seg_list, word_dict, model=model,
                                                                    similarity_dict=similarity_dict)
                                        for i in range(len(inform_slots) - 1, -1, -1):
                                            if inform_slots[i] in stop_words:
                                                del inform_slots[i]
                                        user_pipe[0].send(inform_slots)
                                    except OSError:
                                        # messageSender(conv_id=conv_id, msg="会话结束", log=log, end=True)
                                        continue
                                    if user_text['text'] != pipes_dict[conv_id][2]:
                                        pipes_dict[conv_id][2] += user_text['text']
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
                                        msg = "您询问的业务是否涉及" + recv['service'] + "，如若不涉及，请补充相关细节"
                                        pipes_dict[conv_id][8] = msg
                                        messageSender(conv_id=conv_id, msg=msg, log=log)
                                    else:
                                        pipes_dict[conv_id][4] = True
                                        pipes_dict[conv_id][6] = True
                                        user_pipe[0].close()
                                        response_pipe[1].close()
                                        service_name = recv['service']
                                        pipes_dict[conv_id][7] = service_name
                                        log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                                        log.info("service_name: {}".format(service_name))
                                        answer = get_answer(pipes_dict[conv_id][2], service_name, log)
                                        business = get_business(first_utterance=pipes_dict[conv_id][2])
                                        answer = answer + '\n' + '(' + pipes_dict[conv_id][
                                            7] + '——' + business + ')'
                                        try:
                                            service_link = str(link[service_name])
                                        except KeyError:
                                            service_link = ""
                                        messageSender(conv_id=conv_id, msg=answer, log=log, link=service_link,
                                                      end=pipes_dict[conv_id][4])
                                        pipes_dict[conv_id][2] = ""
                                        pipes_dict[conv_id][3].terminate()
                                        # log.info('process kill')
                                        pipes_dict[conv_id][3].join()
                                        pipes_dict[conv_id][10].append(pipes_dict[conv_id][2])
                                        recommend = get_recommend(service_name=pipes_dict[conv_id][7],
                                                                  history=pipes_dict[conv_id][10])
                                        if len(recommend) < 1:
                                            recommend = "请问还有其他问题吗，如果有请继续提问"
                                        pipes_dict[conv_id][8] = recommend
                                        if isinstance(recommend, list):
                                            messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
                                                          service_name=service_name, options=recommend)
                                        else:
                                            messageSender(conv_id=conv_id, msg=recommend, log=log,
                                                          end=pipes_dict[conv_id][4])
                                        pipes_dict[conv_id][2] = ""
                                        pipes_dict[conv_id][9] = 0
                #
                else:
                    user_pipe, response_pipe, *_ = pipes_dict[conv_id]
                    # 为刷新页面准备
                    if 'content' not in msg.keys():
                        messageSender(conv_id=conv_id, msg=pipes_dict[conv_id][8], log=log)
                        continue
                    if pipes_dict[conv_id][2] == "":
                        pipes_dict[conv_id][2] = msg['content']['text']
                    similar_score, answer = 0, ""
                    if pipes_dict[conv_id][6] is True:
                        pipes_dict[conv_id][2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "",
                                                        pipes_dict[conv_id][2])
                        similar_score, answer, service_name = get_faq(pipes_dict[conv_id][2])
                    if float(similar_score) > 0.9230:
                        pipes_dict[conv_id][7] = service_name
                        pipes_dict[conv_id][10].append(pipes_dict[conv_id][2])
                        pipes_dict[conv_id][8] = faq_diagnose(user_pipe, response_pipe, answer, pipes_dict, conv_id,
                                                              log)
                        # pipes_dict[conv_id][6] = True
                    else:
                        user_text = msg['content']
                        if 'text' in user_text.keys() and pipes_dict[conv_id][9] != 1:
                            # IR
                            options = get_related_title(pipes_dict[conv_id][2])
                            # todo:待调 目前最低
                            # 若对话内容包含的事项足够明确
                            business_threshold = 0.9102
                            candidate_service = ""
                            max_score = 0
                            for o in options:
                                lcs = longestCommonSubsequence(pipes_dict[conv_id][2], o)
                                if lcs <= 2:
                                    continue
                                distance = lev(pipes_dict[conv_id][2], o, True, True)
                                distance = sigmoid(distance + lcs / len(o))
                                if max_score < distance:
                                    max_score = distance
                                    candidate_service = o
                            if max_score > business_threshold:
                                pipes_dict[conv_id][4] = True
                                pipes_dict[conv_id][6] = True
                                user_pipe[0].close()
                                response_pipe[1].close()
                                pipes_dict[conv_id][7] = candidate_service
                                log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                                log.info("service_name: {}".format(candidate_service))
                                pipes_dict[conv_id][8] = return_answer(pipes_dict=pipes_dict, conv_id=conv_id,
                                                                       service_name=candidate_service,
                                                                       log=log,
                                                                       link=link)
                                continue
                        if pipes_dict[conv_id][6] and len(options) > 0:
                            pipes_dict[conv_id][6] = False
                            pipes_dict[conv_id][9] += 1
                            messageSender(conv_id=conv_id, log=log, options=options, end=False)
                        else:
                            if pipes_dict[conv_id][6]:
                                pipes_dict[conv_id][6] = False
                                pipes_dict[conv_id][9] += 1
                            if 'text' not in user_text.keys():
                                user_text = {'text': pipes_dict[conv_id][2]}
                            try:
                                # 做分词归一化
                                sentence = user_text['text']
                                if sentence not in positive_list:
                                    seg = thu.cut(sentence)
                                    seg_list = []
                                    for s in seg:
                                        seg_list.append(s[0])
                                    for i in range(len(seg_list) - 1, -1, -1):
                                        if seg_list[i] in stop_words:
                                            del seg_list[i]
                                    inform_slots = replace_list(seg_list, word_dict, model=model,
                                                                similarity_dict=similarity_dict)
                                    for i in range(len(inform_slots) - 1, -1, -1):
                                        if inform_slots[i] in stop_words:
                                            del inform_slots[i]
                                else:
                                    inform_slots = sentence

                                # 发给子进程诊断
                                user_pipe[0].send(inform_slots)
                            except OSError:
                                pass
                                # messageSender(conv_id=conv_id, msg="会话结束", log=log)
                                # continue
                            if user_text['text'] != pipes_dict[conv_id][2]:
                                pipes_dict[conv_id][2] += user_text['text']
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
                                msg = "您询问的业务是否涉及" + recv['service'] + "，如若不涉及，请补充相关细节"
                                pipes_dict[conv_id][8] = msg
                                messageSender(conv_id=conv_id, msg=msg, log=log)
                            elif pipes_dict[conv_id][4] is True and recv['action'] == 'request' and user_text[
                                'text'] not in positive_list:
                                options = get_related_title(pipes_dict[conv_id][2])
                                # pipes_dict[conv_id][4] = True
                                pipes_dict[conv_id][9] += 1
                                if len(options) > 0:
                                    messageSender(conv_id=conv_id, log=log, options=options, end=False)
                                else:
                                    answer = "抱歉，无法回答当前问题"
                                    pipes_dict[conv_id][6] = True
                                    pipes_dict[conv_id][3].terminate()
                                    # log.info('process kill')
                                    pipes_dict[conv_id][3].join()
                                    pipes_dict[conv_id][2] = ""
                                    pipes_dict[conv_id][9] = 0
                                    messageSender(conv_id=conv_id, log=log, msg=answer, end=False)
                                    pipes_dict[conv_id][8] = "请问还有其他问题吗，如果有请继续提问"
                                    messageSender(conv_id=conv_id, msg="请问还有其他问题吗，如果有请继续提问", log=log,
                                                  end=True)
                            else:
                                pipes_dict[conv_id][4] = True
                                pipes_dict[conv_id][6] = True
                                user_pipe[0].close()
                                response_pipe[1].close()
                                service_name = recv['service']
                                pipes_dict[conv_id][7] = service_name
                                pipes_dict[conv_id][10].append(pipes_dict[conv_id][2])
                                log.info("first_utterance: {}".format(pipes_dict[conv_id][2]))
                                log.info("service_name: {}".format(service_name))
                                pipes_dict[conv_id][8] = return_answer(pipes_dict=pipes_dict, conv_id=conv_id,
                                                                       service_name=service_name,
                                                                       log=log,
                                                                       link=link)
            except Exception as e:
                log.error(e, exc_info=True)

        except ConnectionClosed:
            continue


if __name__ == '__main__':
    start_time = time.time()
    end_time = time.time()
    end_flag = False
    pipes_dict = {}
    first_utterance, service_name = "", ""
    # last_msg = ""
    thu = thulac(user_dict='./data/new_dict.txt', seg_only=True)
    stop_words = [i.strip() for i in open('./data/baidu_stopwords.txt').readlines()]
    with open('data/blur_service.json', 'r') as f:
        blur_service = json.load(f)
    log.info('load model')
    model = gensim.models.Word2Vec.load('./data/wb.text.model')
    word_dict = load_dict('./data/new_dict.txt')
    config_file = './conf/settings.yaml'
    parameter = get_config(config_file)
    positive_list = ['是的', '是', '没错', '对', '对的,', '嗯']
    link_file = 'data/link.json'
    with open(link_file, 'r') as f:
        link = json.load(f)
    # agent = AgentDQN(parameter=parameter)
    agent = AgentRule(parameter=parameter)
    with open('data/similar.json', 'r') as f:
        similarity_dict = json.load(f)
    asyncio.get_event_loop().run_until_complete(main_logic(parameter, link, similarity_dict))
