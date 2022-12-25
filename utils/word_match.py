import numbers
import re
import time

# import jieba.analyse
import numpy as np

from utils.ai_wrapper import get_related_title

setattr(time, "clock", time.perf_counter)

_similarity_smooth = lambda x, y, z, u: (x * y) + z - u


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def is_digit(obj):
    '''
    Check if an object is Number
    '''
    return isinstance(obj, (numbers.Integral, numbers.Complex, numbers.Real))


def load_dict(file_path):
    word_dictionary = []
    with open(file_path, 'r') as fp:
        content = fp.readlines()
        for word in content:
            word_dictionary.append(word.strip())
    return word_dictionary


def lev(first, second, utterance=False, service=False):
    """

    :param first: utterance / candidate service
    :param second: service name
    :param utterance:是否计算utterance与事项
    :param service:是否诊断前的阈值计算
    :return:
    """
    sentence1_len, sentence2_len = len(first), len(second)
    maxlen = max(sentence1_len, sentence2_len)
    if not service:
        if sentence1_len > sentence2_len:
            first, second = second, first

    distances = range(len(first) + 1)
    count = 0
    for index2, char2 in enumerate(second):
        new_distances = [index2 + 1]
        for index1, char1 in enumerate(first):
            if char1 == char2:
                new_distances.append(distances[index1])
            else:
                new_distances.append(1 + min((distances[index1],
                                              distances[index1 + 1],
                                              new_distances[-1])))
        distances = new_distances
    if utterance:
        for c2 in second:
            if c2 in first: count += 1

    levenshtein = distances[-1]
    d = float((maxlen - levenshtein) / maxlen)
    s = d + count / len(second)
    # smoothing
    if not utterance and not service:
        s = (sigmoid(d * 6) - 0.5) * 2
    # print("smoothing[%s| %s]: %s -> %s" % (sentence1, sentence2, d, s))
    return s


def compare(s1, s2, model):
    g = 0
    try:
        g_ = model.wv.similarity(s1, s2)
        if is_digit(g_): g = g_
    except:
        pass
    u = lev(s1, s2)
    if u >= 0.99:
        r = 1.0
    elif u > 0.9:
        r = _similarity_smooth(g, 0.05, u, 0.05)
    elif u > 0.8:
        r = _similarity_smooth(g, 0.1, u, 0.2)
    elif u > 0.4:
        r = _similarity_smooth(g, 0.2, u, 0.15)
    elif u > 0.2:
        r = _similarity_smooth(g, 0.3, u, 0.1)
    else:
        r = _similarity_smooth(g, 0.4, u, 0)

    if r < 0: r = abs(r)
    r = min(r, 1.0)
    return float("%.3f" % r)


def replace_list(seg_list, word_dict, similarity_dict, model):
    new_list = set()
    for x in seg_list:
        replace_word = x
        max_score = 0
        to_check = []
        u = x
        # seek_start = time.time()
        try:
            u = similarity_dict[x]
            # u = model.wv.most_similar(x, topn=5)
        except KeyError:
            pass
        to_check.append(x)
        # seek_end = time.time()
        # print("seek:", seek_end - seek_start)
        for _u in u:
            to_check.append(_u)
        to_check = list(reversed(to_check))
        # com_start = time.time()
        for k in to_check:
            score = [compare(k, y, model) for y in word_dict]
            choice = max(score)
            if choice >= max_score:
                max_score = choice
                choice_index = int(score.index(choice))
                replace_word = list(word_dict)[choice_index]
                # if check_score > 0.1:
                #     replace_word = check_word
        # com_end = time.time()
        # print("compare:", com_end - com_start)
        new_list.add(replace_word)
    return list(new_list)


def find_synonym(question, model, similarity_dict):
    question = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "", question)
    seg = thu.cut(question)
    seg_list = []
    for s in seg:
        seg_list.append(s[0])
    print(seg_list)
    for i in range(len(seg_list) - 1, -1, -1):
        if seg_list[i] in stopwords:
            del seg_list[i]
    new_seg_list = replace_list(seg_list, word_dict, model=model, similarity_dict=similarity_dict)
    print("new seg: " + "/ ".join(new_seg_list))


def is_multi_round(utterance, service_name):
    # 当前最低阈值
    utter_threshold = 0.3332
    service_threshold = 0.8
    options = get_related_title(utterance)
    candidate_service = ""
    max_score = 0
    for o in options:
        distance = lev(utterance, o, True, True)
        if max_score < distance:
            max_score = distance
            candidate_service = o
    # 每句话和候选事项名称之间的相似度想给护照加注应该怎么办理

    # 候选事项和对话内容有关
    if max_score < utter_threshold:
        return True, max_score
    else:
        # todo：候选事项和上一轮事项几乎无关分两种情况：
        #  1、用户事项变换
        #  2、用户对话实际上是与上一轮有关 却检索出其他事项，同时事项与上一轮无关（解决不了）
        service_distance = lev(candidate_service, service_name)
        if service_distance > service_threshold:
            return True, service_distance
        else:
            return False, service_distance


if __name__ == '__main__':
    # log = Logger().getLogger()
    # load_start = time.time()
    # model = gensim.models.Word2Vec.load('../data/wb.text.model')
    # stopwords = [i.strip() for i in open('../data/baidu_stopwords.txt').readlines()]
    # word_dict = load_dict('../data/new_dict.txt')
    # thu = thulac.thulac(user_dict='../data/new_dict.txt', seg_only=True)
    # with open('../data/similar.json', 'r') as f:
    #     similarity_dict = json.load(f)
    # load_end = time.time()
    # print("load:", load_end - load_start)
    # question = "我想挂个牌匾需要办理什么业务？"
    # find_synonym(question, model, similarity_dict)

    print(is_multi_round("16岁以上护照有效期多长", "教师资格的认定"))

    l = ["我需要怎么办理",
         "我在双街镇经营",
         "我应该满足什么条件才能办理",
         "申请条件是什么",
         "有什么要求",
         "我需要提交什么材料",
         "我需要准备什么材料",
         "需要填写什么呢",
         "需要准备什么呢",
         "申请书有什么要求",
         "申请书怎么填写",
         "现状彩色照片有什么要求",
         "效果图有什么要求",
         "产权证明有什么要求",
         "与产权人签订的同意设置户外广告设施的书面协议",
         "相邻人同意设置的书面协议怎么填",
         "座落位置示意图有什么要求",
         "规划预留户外广告设施（牌匾除外）的设计图纸有什么要求",
         "这有什么收费的项目吗",
         "办理这个事收费吗",
         "我去大厅办理，能给我邮寄到家吗"]
    for _l in l:
        test_res, score = is_multi_round(_l, "户外广告及临时悬挂、设置标语或者宣传品许可--户外广告设施许可（不含公交候车亭附属广告及公交车体广告设施）（市级权限委托市内六区实施）")
        if not test_res:
            print(score, test_res, _l)
