from gov.slot_config import requirement_weight

requirement_all = []
for i in range(len(requirement_weight)):
    requirement_all.append([])
for i in range(len(requirement_weight)):
    requirement_all[i] = list(requirement_weight[i].keys())
dict_list = []


def make_dict(requirement):
    requirement.remove(requirement[0])
    for _r in requirement:
        dict_list.append(_r + '\n')


for i in range(len(requirement_all)):
    make_dict(requirement_all[i])

with open('../data/new_dict.txt', 'w') as f:
    f.writelines(dict_list)
