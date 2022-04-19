import json
import os
import re
import time

import thulac

setattr(time, "clock", time.perf_counter)
thu = thulac.thulac(user_dict='./data/new_dict.txt', seg_only=True)
path = os.path.join(os.getcwd(), 'data', 'business')
print(path)
stopwords = [i.strip() for i in open('data/baidu_stopwords.txt').readlines()]


def remove_eng(TEXT):
    TEXT = re.sub('[a-zA-Z’!"#$%&\'()*+,-./:;<=>?@，。?★、…【】（）《》？“”‘’！[\\]^_`{|}~]+', "", TEXT)
    return TEXT


split = dict()
res = []
# for i in os.listdir(path):
#     with open(os.path.join(path, i), 'r') as f:
#         content_list = f.readlines()
#         for j in range(len(content_list)):
#             content_list[j] = remove_eng(content_list[j]).replace(' ', '')
#             pattern = r'申请条件依据'
#             content_list[j] = re.sub('[a-zA-Z’!"#$%&\'()*+,-./:;<=>?@，。?★、…【】：；（）《》？“”‘’！[\\]^_`{|}~]+', "",
#                                      content_list[j])
#             result = re.findall(pattern=pattern, string=content_list[j])
#             if result:
#                 print(result)
#                 print(i)
#                 content_list[j] = content_list[j].replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')
#     with open(os.path.join(path, i), 'w') as f:
#         f.writelines(content_list)

for i in os.listdir(path):
    with open(os.path.join(path, i), 'r') as f:
        content_list = f.readlines()
        seg_list = set()
        for c in content_list:
            # seg_list = set()
            # c = remove_eng(c.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', ''))
            c = c.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')
            pattern = r'(^申请条件依据|^申请条件包括|一|二|三|四|五|六|七|八|九|十)'
            if re.findall(pattern, c):
                c = c.replace(c, "")
                continue
            if re.findall(r'^[0-9]', c):
                c = re.sub(r'^[0-9]', "", c)
            seg = thu.cut(c)
            for s in seg:
                seg_list.add(s[0])
        seg_list = list(seg_list)
        for j in range(len(seg_list) - 1, -1, -1):
            if seg_list[j] in stopwords:
                del seg_list[j]
    # res.append(str(i[:-4]) + ":" + ' '.join(seg_list) + "\n")
    split[i[:-4]] = ' '.join(seg_list)

with open('split.json', 'w') as fp:
    json.dump(split, fp, ensure_ascii=False, indent=4)

# with open('bus_split.txt', 'w') as fp:
#     fp.writelines(res)
