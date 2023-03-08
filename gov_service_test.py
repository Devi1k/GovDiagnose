import asyncio
import multiprocessing as mp
from multiprocessing import Pipe, Process

import gensim
import websockets
from websockets import ConnectionClosed

from conf.config import get_config
from gov.agent_rule import AgentRule
from gov.running_steward import simulation_epoch
from utils.ai_wrapper import *
from utils.logger import *
from utils.message_sender import messageSender
from utils.word_match import is_multi_round, lev, longestCommonSubsequence, sigmoid, load_dict, replace_list, \
    cut_sentence_remove_stopwords

log = Logger().getLogger()
warnings.filterwarnings("ignore")


# pipes_dict = {}


async def main_logic(q):
    global parameter, agent, link, similarity_dict, positive_list, \
        stop_words, word_dict, model, blur_service

    address = 'wss://asueeer.com/ws?mock_login=123'
    async for websocket in websockets.connect(address, ping_interval=12000):
        try:
            log.info('wait message')
            responses = await websocket.recv()
            q.put(responses)

        except ConnectionClosed:
            continue


def process_msg(queue, pipes_dict, agent, parameter, link, similarity_dict, positive_list, stop_words, word_dict, model,
                blur_service):
    log.info('exec process_msg.child process id : %s, parent process id : %s' % (os.getpid(), os.getppid()))
    while True:

        response = queue.get()
        try:
            user_json = json.loads(response)
        except JSONDecodeError:
            continue
        msg = user_json['msg']
        conv_id = msg['conv_id']
        if 'content' in msg.keys():
            log.info("user message:" + msg['content']['text']) if 'text' in msg['content'].keys() else log.info(
                "user choice:" + msg['content']['service_name'])
        try:
            if msg['content']['service_name'] is not None:
                service_name = msg['content']['service_name']
                dialogue_content = pipes_dict[conv_id]
                if service_name != '以上都不是' and dialogue_content[9] != 0:
                    dialogue_content[7] = service_name
                    dialogue_content = return_answer(dialogue_content=dialogue_content, conv_id=conv_id,
                                                     service_name=service_name,
                                                     log=log,
                                                     link=link)
                    pipes_dict[conv_id] = dialogue_content
                    continue
                elif service_name == '以上都不是' and dialogue_content[9] > 1:
                    dialogue_content[4] = True
                    dialogue_content[8] = "抱歉，未能找到您所需的事项。请问还有其他问题吗，如果有请继续提问。"
                    dialogue_content[7] = ""
                    messageSender(conv_id=conv_id, msg=dialogue_content[8], log=log,
                                  end=dialogue_content[4])
                    dialogue_content[6] = True
                    dialogue_content[2] = ""
                    # pipes_dict[conv_id][3].kill()
                    os.kill(dialogue_content[3], signal.SIGKILL)
                    log.info('process kill')
                    pipes_dict[conv_id] = dialogue_content
                    continue
                elif service_name != '以上都不是' and dialogue_content[9] == 0:
                    dialogue_content[2] = service_name.replace("--", "-")
                    dialogue_content[10].append(dialogue_content[2])
                    dialogue_content[4] = True
                    dialogue_content[6] = True

                    similarity_score, answer, service_name = get_faq_from_service(
                        first_utterance=dialogue_content[2],
                        service=dialogue_content[7], history=dialogue_content[10])
                    dialogue_content[7] = service_name
                    messageSender(conv_id=conv_id, msg=answer, log=log, end=dialogue_content[4])
                    recommend = get_recommend(service_name=dialogue_content[7],
                                              history=dialogue_content[10])
                    if len(recommend) < 1:
                        recommend = "请问还有其他问题吗，如果有请继续提问"
                    dialogue_content[8] = recommend
                    if isinstance(recommend, list):
                        messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
                                      service_name=service_name, options=recommend)
                    else:
                        messageSender(conv_id=conv_id, msg=recommend, log=log, end=dialogue_content[4])
                    dialogue_content[2] = ""
                    dialogue_content[9] = 0
                    pipes_dict[conv_id] = dialogue_content
                    continue
        except KeyError:
            pass
        try:
            # Initialize the conversation
            if conv_id not in pipes_dict:
                # todo:改定时
                clean_log()
                user_pipe, response_pipe = Pipe(), Pipe()

                start_time = time.time()

                log.info("new conv")
                pipes_dict[conv_id] = [user_pipe, response_pipe, "", 0, False, False, True,
                                       "", "", 0, []]
                log.info("Initial Dialogue " + str(time.time() - start_time))
            # Handle multiple rounds of dialogues  Continue to speak
            elif conv_id in pipes_dict and pipes_dict[conv_id][5] is False and pipes_dict[conv_id][4] is True:
                log.info("continue to ask")
                user_pipe, response_pipe = Pipe(), Pipe()
                dialogue_content = pipes_dict[conv_id]
                if 'content' not in msg.keys():
                    messageSender(conv_id=conv_id, msg=dialogue_content[8], log=log)
                    continue
                multi = True
                if dialogue_content[2] == "":
                    try:
                        dialogue_content[2] = msg['content']['text'].replace("--", "-")
                    except KeyError:
                        dialogue_content[2] = msg['content']['service_name'].replace("--", "-")
                    dialogue_content[2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*]+",
                                                 "",
                                                 dialogue_content[2])
                    if dialogue_content[6] is True:
                        similarity_score, answer, service_name = get_faq_from_service(
                            first_utterance=dialogue_content[2],
                            service=dialogue_content[7],
                            history=dialogue_content[10]
                        )
                        dialogue_content[6] = False
                    if float(similarity_score) > 0.32:
                        dialogue_content[10].append(dialogue_content[2])
                        dialogue_content = faq_diagnose(user_pipe, response_pipe, answer, dialogue_content, conv_id,
                                                        log)
                        dialogue_content[6] = True
                        pipes_dict[conv_id] = dialogue_content
                        continue
                    # Determine whether it is a multi-round conversation
                    multi, similarity = is_multi_round(dialogue_content[2], dialogue_content[7])
                if multi:
                    log.info("Same matter.")
                    user_pipe[0].close()
                    response_pipe[1].close()
                    user_pipe[1].close()
                    response_pipe[0].close()
                    dialogue_content[4] = True
                    dialogue_content[6] = True
                    if dialogue_content[7] not in blur_service.keys():
                        answer = get_multi_res(dialogue_content[2], dialogue_content[7])
                        messageSender(conv_id=conv_id, msg=answer, log=log, end=dialogue_content[4])
                        recommend = get_recommend(service_name=dialogue_content[7],
                                                  history=dialogue_content[10])
                        if len(recommend) < 1:
                            recommend = "请问还有其他问题吗，如果有请继续提问"
                        dialogue_content[8] = recommend
                        if isinstance(recommend, list):
                            messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
                                          service_name=service_name, options=recommend)
                        else:
                            messageSender(conv_id=conv_id, msg=recommend, log=log, end=dialogue_content[4])
                        dialogue_content[2] = ""
                        dialogue_content[9] = 0
                        pipes_dict[conv_id] = dialogue_content
                    else:
                        options = get_related_title(dialogue_content[7])
                        dialogue_content[9] += 2
                        messageSender(conv_id=conv_id, msg="请选择与您相符的事项", log=log, options=options,
                                      end=False)
                else:
                    log.info("Different matter")
                    # Rediagnosis
                    p = Process(target=simulation_epoch,
                                args=(
                                    (user_pipe[1], response_pipe[0]), agent, parameter, log, similarity_dict,
                                    conv_id))
                    # send_pipe, receive_pipe, first_utterance, process, single_finish, all_finish, first_utt,
                    # service_name, last_msg
                    pipes_dict[conv_id] = [user_pipe, response_pipe, pipes_dict[conv_id][2], 0, False, False,
                                           True,
                                           "", "", 0, []]
                    dialogue_content = pipes_dict[conv_id]
                    dialogue_content[2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*]+",
                                                 "",
                                                 dialogue_content[2].replace("--", "-"))
                    similar_score, answer = 0, ""
                    if pipes_dict[conv_id][6] is True:
                        similar_score, answer, service_name = get_faq(dialogue_content[2])
                    user_text = {'text': dialogue_content[2]}
                    log.info(user_text)
                    if float(similar_score) > 0.9230:
                        dialogue_content[10].append(dialogue_content[2])
                        dialogue_content = faq_diagnose(user_pipe, response_pipe, answer, dialogue_content, conv_id,
                                                        log)
                        pipes_dict[conv_id] = dialogue_content
                        # pipes_dict[conv_id][6] = True
                    else:
                        # After initializing the session, send judgments and descriptions to the model (including
                        # subsequent judgments and supplementary descriptions).

                        # IR
                        options = get_related_title(dialogue_content[2])
                        business_threshold = 0.9102
                        candidate_service = ""
                        max_score = 0
                        for o in options:
                            lcs = longestCommonSubsequence(dialogue_content[2], o)
                            if lcs <= 2:
                                continue
                            distance = lev(dialogue_content[2], o, True, True)
                            final_distance = sigmoid(lcs / len(o) + distance)
                            if max_score < final_distance:
                                max_score = final_distance
                                candidate_service = o
                        if max_score > business_threshold:
                            dialogue_content[4] = True
                            dialogue_content[6] = True
                            user_pipe[0].close()
                            response_pipe[1].close()
                            # service_name = recv['service']
                            dialogue_content[7] = candidate_service
                            log.info("first_utterance: {}".format(dialogue_content[2]))
                            log.info("service_name: {}".format(candidate_service))
                            dialogue_content = return_answer(dialogue_content=dialogue_content, conv_id=conv_id,
                                                             service_name=candidate_service,
                                                             log=log,
                                                             link=link)
                            pipes_dict[conv_id] = dialogue_content
                        else:
                            if dialogue_content[6] and len(options) > 0:
                                dialogue_content[6] = False
                                dialogue_content[9] += 1
                                messageSender(conv_id=conv_id, log=log, options=options, end=False)
                                pipes_dict[conv_id] = dialogue_content
                            else:
                                if dialogue_content[6]:
                                    dialogue_content[6] = False
                                    dialogue_content[9] += 1
                                try:
                                    sentence = user_text['text']
                                    seg_list = cut_sentence_remove_stopwords(sentence)
                                    inform_slots = replace_list(seg_list, word_dict, model=model,
                                                                similarity_dict=similarity_dict)
                                    for i in range(len(inform_slots) - 1, -1, -1):
                                        if inform_slots[i] in stop_words:
                                            del inform_slots[i]
                                    p.start()

                                    user_pipe[0].send(inform_slots)
                                except OSError:
                                    # messageSender(conv_id=conv_id, msg="会话结束", log=log, end=True)
                                    continue
                                if user_text['text'] != dialogue_content[2]:
                                    dialogue_content[2] += user_text['text']
                                recv = response_pipe[1].recv()
                                # The message format of the model received from the model is
                                """
                                {
                                    "service": agent_action["inform_slots"]["service"] or ,   service为业务名
                                    "end_flag": episode_over  会话是否结束
                                }
                                """
                                dialogue_content[4] = recv['end_flag']
                                # Continue to input without ending
                                if dialogue_content[4] is not True and recv['action'] == 'request':
                                    msg = "您询问的业务是否涉及" + recv['service'] + "，如若不涉及，请补充相关细节"
                                    dialogue_content[8] = msg
                                    messageSender(conv_id=conv_id, msg=msg, log=log)
                                    pipes_dict[conv_id] = dialogue_content
                                else:
                                    dialogue_content[4] = True
                                    dialogue_content[6] = True
                                    user_pipe[0].close()
                                    response_pipe[1].close()
                                    service_name = recv['service']
                                    dialogue_content[7] = service_name
                                    log.info("first_utterance: {}".format(dialogue_content[2]))
                                    log.info("service_name: {}".format(service_name))
                                    answer = get_answer(dialogue_content[2], service_name, log)
                                    business = get_business(first_utterance=dialogue_content[2])
                                    answer = answer + '\n' + '(' + dialogue_content[
                                        7] + '——' + business + ')'
                                    try:
                                        service_link = str(link[service_name])
                                    except KeyError:
                                        service_link = ""
                                    messageSender(conv_id=conv_id, msg=answer, log=log, link=service_link,
                                                  end=dialogue_content[4])
                                    dialogue_content[2] = ""
                                    os.kill(dialogue_content[3], signal.SIGKILL)
                                    log.info('process kill')
                                    dialogue_content[10].append(dialogue_content[2])
                                    recommend = get_recommend(service_name=dialogue_content[7],
                                                              history=dialogue_content[10])
                                    if len(recommend) < 1:
                                        recommend = "请问还有其他问题吗，如果有请继续提问"
                                    dialogue_content[8] = recommend
                                    if isinstance(recommend, list):
                                        messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
                                                      service_name=service_name, options=recommend)
                                    else:
                                        messageSender(conv_id=conv_id, msg=recommend, log=log,
                                                      end=dialogue_content[4])
                                    dialogue_content[2] = ""
                                    dialogue_content[9] = 0
                                    pipes_dict[conv_id] = dialogue_content

            #
            else:
                # print(pipes_dict[conv_id])
                dialogue_content = pipes_dict[conv_id]
                user_pipe, response_pipe = dialogue_content[0], dialogue_content[1]
                if 'content' not in msg.keys():
                    messageSender(conv_id=conv_id, msg=dialogue_content[8], log=log)
                    continue
                if dialogue_content[2] == "":
                    dialogue_content[2] = msg['content']['text']
                # print(dialogue_content)

                log.info(dialogue_content[2])
                similar_score, answer = 0, ""
                if dialogue_content[6] is True:
                    dialogue_content[2] = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*]+", "",
                                                 dialogue_content[2])
                    similar_score, answer, service_name = get_faq(dialogue_content[2])
                if float(similar_score) > 0.9230:
                    dialogue_content[7] = service_name
                    dialogue_content[10].append(dialogue_content[2])
                    dialogue_content = faq_diagnose(user_pipe, response_pipe, answer, dialogue_content, conv_id,
                                                    log)
                    pipes_dict[conv_id] = dialogue_content
                else:
                    user_text = msg['content']
                    if 'text' in user_text.keys() and dialogue_content[9] != 1:
                        # IR
                        options = get_related_title(dialogue_content[2])
                        # 若对话内容包含的事项足够明确
                        business_threshold = 0.9102
                        candidate_service = ""
                        max_score = 0
                        for o in options:
                            lcs = longestCommonSubsequence(dialogue_content[2], o)
                            if lcs <= 2:
                                continue
                            distance = lev(dialogue_content[2], o, True, True)
                            distance = sigmoid(distance + lcs / len(o))
                            if max_score < distance:
                                max_score = distance
                                candidate_service = o
                        if max_score > business_threshold:
                            dialogue_content[4] = True
                            dialogue_content[6] = True
                            user_pipe[0].close()
                            response_pipe[1].close()
                            dialogue_content[7] = candidate_service
                            log.info("first_utterance: {}".format(dialogue_content[2]))
                            log.info("service_name: {}".format(candidate_service))
                            dialogue_content = return_answer(dialogue_content=dialogue_content, conv_id=conv_id,
                                                             service_name=candidate_service,
                                                             log=log,
                                                             link=link)
                            pipes_dict[conv_id] = dialogue_content
                            continue
                    if dialogue_content[6] and len(options) > 0:
                        dialogue_content[6] = False
                        dialogue_content[9] += 1
                        pipes_dict[conv_id] = dialogue_content
                        messageSender(conv_id=conv_id, log=log, options=options, end=False)
                    else:
                        if dialogue_content[6]:
                            dialogue_content[6] = False
                            dialogue_content[9] += 1
                        if 'text' not in user_text.keys():
                            user_text = {'text': dialogue_content[2]}
                        try:
                            # 做分词归一化
                            sentence = user_text['text']
                            if sentence not in positive_list:
                                seg_list = cut_sentence_remove_stopwords(sentence)
                                inform_slots = replace_list(seg_list, word_dict, model=model,
                                                            similarity_dict=similarity_dict)
                                for i in range(len(inform_slots) - 1, -1, -1):
                                    if inform_slots[i] in stop_words:
                                        del inform_slots[i]
                            else:
                                inform_slots = sentence
                            p = Process(target=simulation_epoch,
                                        args=(
                                            (user_pipe[1], response_pipe[0]), agent, parameter, log, similarity_dict,
                                            conv_id))
                            p.start()
                            dialogue_content[3] = p.ident
                            # 发给子进程诊断
                            user_pipe[0].send(inform_slots)
                        except OSError:
                            pass
                            # messageSender(conv_id=conv_id, msg="会话结束", log=log)
                            # continue
                        if user_text['text'] != dialogue_content[2]:
                            dialogue_content[2] += user_text['text']
                        recv = response_pipe[1].recv()
                        # The message format of the model received from the model is
                        """
                        {
                            "service": agent_action["inform_slots"]["service"] or ,   service为业务名
                            "end_flag": episode_over  会话是否结束
                        }
                        """
                        dialogue_content[4] = recv['end_flag']
                        # Continue to input without ending
                        if dialogue_content[4] is not True and recv['action'] == 'request':
                            msg = "您询问的业务是否涉及" + recv['service'] + "，如若不涉及，请补充相关细节"
                            dialogue_content[8] = msg
                            pipes_dict[conv_id] = dialogue_content
                            messageSender(conv_id=conv_id, msg=msg, log=log)
                        elif dialogue_content[4] is True and recv['action'] == 'request' and user_text[
                            'text'] not in positive_list:
                            options = get_related_title(dialogue_content[2])
                            # pipes_dict[conv_id][4] = True
                            dialogue_content[9] += 1
                            if len(options) > 0:
                                pipes_dict[conv_id] = dialogue_content
                                messageSender(conv_id=conv_id, log=log, options=options, end=False)
                            else:
                                answer = "抱歉，无法回答当前问题"
                                dialogue_content[6] = True
                                # pipes_dict[conv_id][3].kill()
                                os.kill(dialogue_content[3], signal.SIGKILL)
                                # log.info('process kill')
                                dialogue_content[2] = ""
                                dialogue_content[9] = 0
                                messageSender(conv_id=conv_id, log=log, msg=answer, end=False)
                                dialogue_content[8] = "请问还有其他问题吗，如果有请继续提问"
                                messageSender(conv_id=conv_id, msg="请问还有其他问题吗，如果有请继续提问", log=log,
                                              end=True)
                                pipes_dict[conv_id] = dialogue_content
                        else:
                            dialogue_content[4] = True
                            dialogue_content[6] = True
                            user_pipe[0].close()
                            response_pipe[1].close()
                            service_name = recv['service']
                            dialogue_content[7] = service_name
                            dialogue_content[10].append(dialogue_content[2])
                            log.info("first_utterance: {}".format(dialogue_content[2]))
                            log.info("service_name: {}".format(service_name))
                            dialogue_content = return_answer(dialogue_content=dialogue_content, conv_id=conv_id,
                                                             service_name=service_name,
                                                             log=log,
                                                             link=link)
                            pipes_dict[conv_id] = dialogue_content
        except Exception as e:
            log.error(e, exc_info=True)


def task_start(queue):
    log.info('exec task_start.child process id : %s, parent process id : %s' % (os.getpid(), os.getppid()))
    loop = asyncio.new_event_loop()
    task = main_logic(queue)
    loop.run_until_complete(task)


if __name__ == '__main__':
    # q = Queue(maxsize=300)
    # last_msg = ""
    # manager = Manager()
    # pipes_dict = manager.dict()
    with open('data/blur_service.json', 'r') as f:
        blur_service = json.load(f)
    model = gensim.models.Word2Vec.load('./data/wb.text.model')
    word_dict = load_dict('./data/new_dict.txt')
    stop_words = [i.strip() for i in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                       'data/baidu_stopwords.txt')).readlines()]
    positive_list = ['是的', '是', '没错', '对', '对的,', '嗯']
    link_file = 'data/link.json'
    with open(link_file, 'r') as f:
        link = json.load(f)
    with open('data/similar.json', 'r') as f:
        similarity_dict = json.load(f)
    config_file = './conf/settings.yaml'

    parameter = get_config(config_file)
    # agent = AgentDQN(parameter=parameter)

    agent = AgentRule(parameter=parameter)
    pipes_dict = mp.Manager().dict()
    q = mp.Manager().Queue(300)
    process_count = mp.cpu_count() // 2
    consumer_list = [Process(target=process_msg, args=(
        q, pipes_dict, agent, parameter, link, similarity_dict, positive_list, stop_words, word_dict, model,
        blur_service,)) for i in range(process_count)]
    producer = Process(target=task_start, args=(q,))
    producer.start()
    [c.start() for c in consumer_list]
    [c.join() for c in consumer_list]
    # asyncio.get_event_loop().run_until_complete(main_logic(q))
