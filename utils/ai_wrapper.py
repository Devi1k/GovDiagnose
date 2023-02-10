import json
import warnings
from json import JSONDecodeError

import requests

from utils.message_sender import messageSender

warnings.filterwarnings("ignore")

with open('data/faq_recommend.json', 'r') as f:
    recommend = json.load(f)


# 常见问题回答
def get_faq(first_utterance, service=""):
    faq_path = "https://miner.picp.net/FAQ?First_utterance={}"
    first_utterance = service + first_utterance
    try:
        faq_res = requests.get(faq_path.format(first_utterance), verify=False).json()
        similar_score, answer, service = faq_res['Similarity_score'], faq_res['answer'], faq_res['service']
    except JSONDecodeError:
        similar_score, answer, service = 1, "抱歉，网络错误，请您重新尝试", ""
    return similar_score, answer, service


# 业务
def get_business(first_utterance):
    business_path = "https://miner.picp.net/yewu?text={}"
    res = requests.get(business_path.format(first_utterance), verify=False).json()
    return res['type']


# 文档检索
def get_retrieval(first_utterance, service_name):
    ir_path = "https://burninghell.xicp.net/IR?serviceName={}&firstUtterance={}"
    ir_res = requests.get(ir_path.format(service_name, first_utterance), verify=False).json()['abs']
    return ir_res


# 业务推理
def get_nli(first_utterance, service_name):
    nli_path = "https://burninghell.xicp.net/zmytest?Service_name={}&First_utterance={}"
    nli_res = requests.get(nli_path.format(service_name, first_utterance), verify=False).text
    return nli_res


# 进入对话后的检索事项
def get_related_title(first_utterance):
    title_path = "https://burninghell.xicp.net/getRelatedTitle/ver2?query={}"
    # title_res = []
    try:
        title_res = requests.get(title_path.format(first_utterance), verify=False).json()['titleList'][:5]
        if len(title_res) > 0:
            title_res.append('以上都不是')
    except JSONDecodeError:
        title_res = []

    return title_res


def get_answer(first_utterance, service_name, log, intent_class=''):
    # --intention detection
    if intent_class == '':
        intent_path = "https://miner.picp.net/intent?text={}"
        intent_res = requests.get(intent_path.format(first_utterance), verify=False).json()
        intent_class = intent_res['data']
        if '认定高中教师资格的学历要求' in first_utterance:
            return '研究生或者大学本科学历'
        elif '16岁以上护照有效期多长' in first_utterance:
            return '十年'
        log.info("intention:{}".format(intent_class))

    if intent_class == "QA":  # --QA match
        answer = get_retrieval(first_utterance, service_name)
        log.info("QA: {}".format(answer))
        return answer

    # 业务推理
    elif intent_class == "NLI":  # --NLI
        nli_res = get_nli(first_utterance, service_name)
        log.info("NLI:{} ".format(nli_res))
        return nli_res

    # 文档检索
    elif intent_class == "IR":  # --IR
        ir_res = get_retrieval(first_utterance, service_name)
        log.info("IR: {}".format(ir_res))
        return ir_res


    else:  # --diagnose
        log.info("diagnosis: {}".format(service_name))
        return "您询问的业务属于:" + service_name


def faq_diagnose(user_pipe, response_pipe, answer, pipes_dict, conv_id, log, service_name=""):
    # 子进程管道关闭
    user_pipe[0].close()
    response_pipe[1].close()
    user_pipe[1].close()
    response_pipe[0].close()

    # 对话状态设置
    pipes_dict[conv_id][4] = True
    pipes_dict[conv_id][6] = True

    messageSender(conv_id=conv_id, msg=answer, log=log, end=pipes_dict[conv_id][4])

    pipes_dict[conv_id][2] = ""
    pipes_dict[conv_id][3].terminate()
    # log.info('process kill')
    last_msg = "请问还有其他问题吗，如果有请继续提问"
    messageSender(conv_id=conv_id, msg="请问还有其他问题吗，如果有请继续提问", log=log, end=pipes_dict[conv_id][4])
    pipes_dict[conv_id][3].join()

    # FAQ推荐 后续实现
    recommend = get_recommend(service_name=pipes_dict[conv_id][7],
                              utterance=pipes_dict[conv_id][2])
    # last_msg = recommend
    # messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
    #               service_name=service_name, options=recommend)
    pipes_dict[conv_id][2] = ""
    pipes_dict[conv_id][9] = 0
    return last_msg


def return_answer(pipes_dict, conv_id, service_name, log, link, intent_class=''):
    similarity_score, answer, service = get_faq(first_utterance=pipes_dict[conv_id][2], service=service_name)
    if float(similarity_score) < 0.85:
        answer = get_answer(pipes_dict[conv_id][2], service_name, log, intent_class)
    try:
        service_link = str(link[service_name])
    except KeyError:
        service_link = ""
    business = get_business(first_utterance=pipes_dict[conv_id][2])
    answer = answer + '\n' + '(' + service_name + '——' + business + ')'
    messageSender(conv_id=conv_id, msg=answer, log=log, link=service_link, end=True)
    pipes_dict[conv_id][4] = True
    pipes_dict[conv_id][6] = True
    pipes_dict[conv_id][3].terminate()
    # log.info('process kill')
    pipes_dict[conv_id][3].join()
    recommend = get_recommend(service_name=pipes_dict[conv_id][7],
                              utterance=pipes_dict[conv_id][2])
    # last_msg = recommend
    # messageSender(conv_id=conv_id, msg="大家都在问", log=log, end=True,
    #               service_name=service_name, options=recommend)
    last_msg = "请问还有其他问题吗，如果有请继续提问"
    messageSender(conv_id=conv_id, msg="请问还有其他问题吗，如果有请继续提问", log=log, end=True,
                  service_name=service_name)
    pipes_dict[conv_id][2] = ""
    pipes_dict[conv_id][9] = 0
    return last_msg


def get_multi_res(first_utterance, service_name):
    answer = get_retrieval(first_utterance=first_utterance, service_name=service_name)
    business = get_business(first_utterance=first_utterance)
    answer = answer + '\n' + '(' + service_name + '——' + business + ')'
    return answer


def get_recommend(service_name, utterance="", history=None):
    if history is None:
        history = []
    level_list = ['1', '2', '3']
    query_list = []
    for level in level_list:
        try:
            query = recommend[service_name][level]
        except KeyError:
            continue
        for q in query:
            query_list.append(q)
    # utterance = service_name + utterance
    # todo:如果问不一样的怎么办
    if history is not None:
        for h in history:
            h = service_name + h
            if h in query_list:
                query_list.remove(h)
    query_list.reverse()
    res = []
    # 1.按优先级固定写死
    for q in query_list[-5:]:
        res.append(q.replace(service_name, ''))
    # 2.按相似度取问题（不涉及优先级）
    # similarity_list = []
    # for q in query_list:
    #     score = ratio(utterance, q)
    #     similarity_list.append(score)
    # similarity_list = np.array(similarity_list)
    # choice = sorted(np.argsort(similarity_list)[-5:])
    # for c in choice:
    #     res.append(query_list[c].replace(service_name, ''))
    return res
