from json import JSONDecodeError

import requests

from utils.message_sender import messageSender


def get_faq(first_utterance, service=""):
    faq_path = "https://miner.picp.net/FAQ?First_utterance={}&Service_name={}"
    faq_res = requests.get(faq_path.format(first_utterance, service)).json()
    similar_score, answer = faq_res['Similarity_score'], faq_res['answer']
    return similar_score, answer

def get_business(first_utterance):
    # todo: Determine interface
    # business_path = "http://10.13.56.38:5700/yewu?text=%E6%88%91%E6%83%B3%E8%A6%81%E6%94%B6%E8%97%8F"
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


def get_answer(first_utterance, service_name, log):
    # --FAQ
    similar_score, answer = get_faq(first_utterance, service_name)
    # faq_path = "https://miner.picp.net/FAQ?First_utterance={}&Service_name={}"
    # faq_res = requests.get(faq_path.format(first_utterance, service_name)).json()
    # faq_res['Similarity_score'], faq_res['answer']
    log.info("FAQ:{}".format(similar_score, answer))

    # similar_score = 0

    if float(similar_score) > 0.6:
        # pass
        return answer
    else:
        # --intention detection
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


def rl_diagnose(user_pipe, response_pipe, pipes_dict, conv_id, log, link):
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
        # msg = get_retrieval(pipes_dict[conv_id][2])
        pipes_dict[conv_id][4] = True
        messageSender(conv_id, msg, log, end=False)
        pipes_dict[conv_id][3].terminate()
        log.info('process kill')
        pipes_dict[conv_id][3].join()
        del pipes_dict[conv_id]
        # last_msg = "请问还有其他问题吗，如果有请继续提问"
        # messageSender(conv_id, "请问还有其他问题吗，如果有请继续提问", log, "", end=pipes_dict[conv_id][4])
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

# if __name__ == '__main__':
#     service_name = "外国人居留停留一-外国人停留证件的签发、换发、补发"
#     first_utterance = "外国人来华签证关于贸易签证的签发、延期、换发、补发的相关申请材料和办理流程是什么"
#     log.info(get_answer(first_utterance, service_name))
