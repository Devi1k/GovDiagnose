import re
import time

import jieba.analyse
import numpy as np
import gensim
import numbers

_similarity_smooth = lambda x, y, z, u: (x * y) + z - u


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def is_digit(obj):
    '''
    Check if an object is Number
    '''
    return isinstance(obj, (numbers.Integral, numbers.Complex, numbers.Real))


stopwords = [i.strip() for i in open('../data/baidu_stopwords.txt').readlines()]


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


def replace_list(seg_list, word_dict, model):
    new_list = []
    for x in seg_list:
        replace_word = x
        max_score = 0
        to_check = []
        u = x
        try:
            u = model.wv.most_similar(x, topn=5)
        except KeyError:
            pass
        for i, _u in enumerate(u):
            to_check.append(u[i][0])
        to_check.append(x)
        for k in to_check:
            score = [compare(k, y, model) for y in word_dict]
            choice = max(score)
            if choice > max_score:
                max_score = choice
                choice_index = int(score.index(choice))
                replace_word = list(word_dict)[choice_index]
        new_list.append(replace_word)
    return new_list


if __name__ == '__main__':
    jieba.initialize()

    word_dict = load_dict('../data/new_dict.txt')

    # with open('data/question.txt', 'r') as fp:
    #     question = fp.readline()
    question = "我想办理护照"
    # while question:
    question = re.sub("[\s++\.\!\/_,$%^*(+\"\')]+|[+——()?【】“”！，。？、~@#￥%……&*（）]+", "", question)
    model = gensim.models.Word2Vec.load('../data/wb.text.model')
    # print(question)
    start = time.time()
    with open('../data/new_dict.txt', 'r') as fp:
        content = fp.readlines()
        for word in content:
            jieba.add_word(word)
    end = time.time()
    print(end - start)
    seg_list = list(jieba.cut(question))
    for i in range(len(seg_list) - 1, -1, -1):
        if seg_list[i] in stopwords:
            del seg_list[i]
    print("old seg: " + "/ ".join(seg_list))
    new_seg_list = replace_list(seg_list, word_dict, model=model)
    print("new seg: " + "/ ".join(new_seg_list))
    # question = input()
