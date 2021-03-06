import requests


def get_faq(first_utterance, service=""):
    faq_path = "https://miner.picp.net/FAQ?First_utterance={}&Service_name={}"
    faq_res = requests.get(faq_path.format(first_utterance, service)).json()
    similar_score, answer = faq_res['Similarity_score'], faq_res['answer']
    return similar_score, answer


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
            nli_path = "https://burninghell.xicp.net/zmytest?Service_name={}&First_utterance={}"
            nli_res = requests.get(nli_path.format(service_name, first_utterance)).text
            log.info("NLI:{} ".format(nli_res))
            return nli_res

        elif intent_class == "IR":  # --IR
            ir_path = "https://burninghell.xicp.net/IR?serviceName={}&firstUtterance={}"
            ir_res = requests.get(ir_path.format(service_name, first_utterance)).json()['abs']
            log.info("IR: {}".format(ir_res))
            return ir_res

        else:  # --diagnose
            log.info("diagnosis: {}".format(service_name))
            return "您要办理的业务属于:" + service_name

# if __name__ == '__main__':
#     service_name = "外国人居留停留一-外国人停留证件的签发、换发、补发"
#     first_utterance = "外国人来华签证关于贸易签证的签发、延期、换发、补发的相关申请材料和办理流程是什么"
#     log.info(get_answer(first_utterance, service_name))
