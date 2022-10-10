from json import JSONDecodeError

import requests

from utils.message_sender import messageSender


def get_faq(first_utterance, service=""):
    faq_path = "https://miner.picp.net/FAQ?First_utterance={}&Service_name={}"
    faq_res = requests.get(faq_path.format(first_utterance, service)).json()
    similar_score, answer = faq_res['Similarity_score'], faq_res['answer']
    return similar_score, answer


def get_business(first_utterance):
    business_path = "http://10.13.56.38:5700/yewu?text={}"
    faq_res = requests.get(business_path.format(first_utterance)).json()
    return faq_res


def get_retrieval(first_utterance, service_name):
    ir_path = "https://burninghell.xicp.net/IR?serviceName={}&firstUtterance={}"
    ir_res = requests.get(ir_path.format(service_name, first_utterance)).json()['abs']
    return ir_res


def get_nli(first_utterance, service_name):
    nli_path = "https://burninghell.xicp.net/zmytest?Service_name={}&First_utterance={}"
    nli_res = requests.get(nli_path.format(service_name, first_utterance)).text
    return nli_res


def get_answer(first_utterance, service_name, log, intent_class=''):
    # --intention detection
    if intent_class == '':
        intent_path = "https://miner.picp.net/intent?text={}"
        intent_res = requests.get(intent_path.format(first_utterance)).json()
        intent_class = intent_res['data']
        if first_utterance == '认定高中教师资格的学历要求':
            return '研究生或者大学本科学历'
        elif first_utterance == '16岁以上护照有效期多长':
            return '十年'
        log.info("intention:{}".format(intent_class))

    if intent_class == "QA":  # --QA match
        qamatch_path = "https://burninghell.xicp.net/QAMatch?serviceName={}&question={}"
        context = requests.get(qamatch_path.format(service_name, first_utterance)).text
        log.info("QA match: {}".format(context))
        # --QA
        qa_path = "https://miner.picp.net/qa?context={}&question={}"
        res = requests.get(qa_path.format(context, first_utterance)).json()
        score, answer = res['score'], res['answer']
        log.info("QA: {},{}".format(score, answer))
        return answer

    elif intent_class == "NLI":  # --NLI
        nli_res = get_nli(first_utterance, service_name)
        log.info("NLI:{} ".format(nli_res))
        return nli_res

    elif intent_class == "IR":  # --IR
        ir_res = get_retrieval(first_utterance, service_name)
        log.info("IR: {}".format(ir_res))
        return ir_res

    else:  # --diagnose
        log.info("diagnosis: {}".format(service_name))
        return "您要办理的业务属于:" + service_name


def faq_diagnose(user_pipe, response_pipe, answer, pipes_dict, conv_id, log):
    user_pipe[0].close()
    response_pipe[1].close()
    user_pipe[1].close()
    response_pipe[0].close()
    pipes_dict[conv_id][4] = True
    messageSender(conv_id, answer, log, end=pipes_dict[conv_id][4])
    pipes_dict[conv_id][2] = ""
    pipes_dict[conv_id][3].terminate()
    log.info('process kill')
    pipes_dict[conv_id][3].join()
    last_msg = "请问还有其他问题吗，如果有请继续提问"
    messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=pipes_dict[conv_id][4])
    return last_msg


def return_answer(pipes_dict, conv_id, service_name, log, link, intent_class=''):
    try:
        answer = get_answer(pipes_dict[conv_id][2], service_name, log, intent_class)
    except JSONDecodeError:
        answer = "抱歉，无法回答当前问题"
    service_link = str(link[service_name])
    messageSender(conv_id, answer, log, service_link, end=pipes_dict[conv_id][4])
    pipes_dict[conv_id][2] = ""
    pipes_dict[conv_id][3].terminate()
    log.info('process kill')
    pipes_dict[conv_id][3].join()
    last_msg = "请问还有其他问题吗，如果有请继续提问"
    messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=True,
                  service_name=service_name)
    return last_msg
