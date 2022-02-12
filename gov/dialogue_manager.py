# -*- coding:utf-8 -*-
import json
import os

import jieba
import gov.dialogue_configuration as dialogue_configuration
from gov.state_tracker import StateTracker
from normal.word_match import replace_list, load_dict


class DialogueManager(object):
    def __init__(self, user, agent, parameter):
        jieba.initialize()
        self.state_tracker = StateTracker(user=user, agent=agent, parameter=parameter)
        self.parameter = parameter
        self.inform_wrong_service_count = 0
        self.stop_words = [i.strip() for i in open('data/baidu_stopwords.txt').readlines()]

    def initialize(self, sentence, model, greedy_strategy, train_mode=1, epoch_index=None):

        self.state_tracker.initialize()
        self.inform_wrong_service_count = 0
        with open('data/new_dict.txt', 'r') as fp:
            content = fp.readlines()
            for word in content:
                jieba.add_word(word)
        word_dict = load_dict('./data/new_dict.txt')
        # 取出问题
        # print(sentence)
        seg_list = list(jieba.cut(sentence))
        print(' '.join(seg_list))
        explicit_inform_slots = replace_list(seg_list, word_dict, model=model)
        for i in range(len(explicit_inform_slots) - 1, -1, -1):
            if explicit_inform_slots[i] in self.stop_words:
                del explicit_inform_slots[i]
        print(' '.join(explicit_inform_slots))

        user_action = self.state_tracker.user.initialize(explicit_inform_slots)
        # print("**************user_action•••••••••••")
        # print(user_action)
        self.state_tracker.state_updater(user_action=user_action)
        self.state_tracker.agent.initialize()
        state = self.state_tracker.get_state()

        agent_action, action_index = self.state_tracker.agent.next(state=state, turn=self.state_tracker.turn,
                                                                   greedy_strategy=greedy_strategy)
        self.state_tracker.state_updater(agent_action=agent_action)
        # state = self.state_tracker.get_state()
        # print(state["current_slots"]["agent_request_slots"].keys())  #测试是否为空，证明不是
        return agent_action

    def set_agent(self, agent):
        self.state_tracker.set_agent(agent=agent)

    def next(self, implicit, model, save_record, train_mode, agent_action, greedy_strategy):
        # state = self.state_tracker.get_state()
        with open('data/new_dict.txt', 'r') as fp:
            content = fp.readlines()
            for word in content:
                jieba.add_word(word)
        implicit_inform_slots = ''
        if implicit != '':
            word_dict = load_dict('./data/new_dict.txt')
            # 取出问题
            # print(implicit)
            seg_list = list(jieba.cut(implicit))
            print(' '.join(seg_list))
            implicit_inform_slots = replace_list(seg_list, word_dict, model)
            for i in range(len(implicit_inform_slots) - 1, -1, -1):
                if implicit_inform_slots[i] in self.stop_words:
                    del implicit_inform_slots[i]
            print(' '.join(implicit_inform_slots))
        user_action, reward, episode_over, dialogue_status = self.state_tracker.user.next(implicit_inform_slots,
                                                                                          agent_action=agent_action,
                                                                                          turn=self.state_tracker.turn)
        # print("**************user_action•••••••••••")
        # print(user_action)
        self.state_tracker.state_updater(user_action=user_action)

        if dialogue_status == dialogue_configuration.DIALOGUE_STATUS_INFORM_WRONG_SERVICE:
            self.inform_wrong_service_count += 1

        state = self.state_tracker.get_state()
        # print(state["current_slots"]["agent_request_slots"].keys())  # 测试是否为空
        agent_action, action_index = self.state_tracker.agent.next(state=state, turn=self.state_tracker.turn,
                                                                   greedy_strategy=greedy_strategy)
        # print("**************agent_action•••••••••••")
        # print(agent_action)
        with open('./data/goal_set.json', 'r') as f:
            goal_set = json.load(f)
            goal_set['agent_aciton'] = agent_action
        with open('./data/goal_set.json', 'w') as f:
            json.dump(goal_set, f, indent=4, ensure_ascii=False)
        # todo: 何时发出去、怎么发出去
        self.state_tracker.state_updater(agent_action=agent_action)

        return reward, episode_over, dialogue_status, agent_action
