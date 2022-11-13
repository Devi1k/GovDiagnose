import json
import numbers
import re
import time

import gensim
# import jieba.analyse
import numpy as np

setattr(time, "clock", time.perf_counter)
import thulac

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


def lev(first, second):
    sentence1_len, sentence2_len = len(first), len(second)
    maxlen = max(sentence1_len, sentence2_len)
    if sentence1_len > sentence2_len:
        first, second = second, first

    distances = range(len(first) + 1)
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
    levenshtein = distances[-1]
    d = float((maxlen - levenshtein) / maxlen)
    # smoothing
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
        for i, _u in enumerate(u):
            to_check.append(u[i][0])
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


if __name__ == '__main__':
    # jieba.initialize()
    load_start = time.time()
    model = gensim.models.Word2Vec.load('../data/wb.text.model')
    stopwords = [i.strip() for i in open('../data/baidu_stopwords.txt').readlines()]
    word_dict = load_dict('../data/new_dict.txt')
    thu = thulac.thulac(user_dict='../data/new_dict.txt', seg_only=True)
    for c in thu.cut('符合户外广告设置规划，并与周围建筑、街景环境相协调 符合户外广告设置规范 采用新技术、新材料'):
        print(c[0], end=' ')
    with open('../data/similar.json', 'r') as f:
        similarity_dict = json.load(f)
    load_end = time.time()
    print("load:", load_end - load_start)
    question = "我想挂个牌匾需要办理什么业务？"

    while True:
        start = time.time()
        find_synonym(question, model, similarity_dict)
        end = time.time()
        print("find:", end - start)
        question = input()

    # question = input()
