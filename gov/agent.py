# -*- coding: utf-8 -*-
"""
Basic agent class that other complicated agent, e.g., rule-based agent, DQN-based agent.
"""
import copy

import numpy as np

import dialogue_configuration
from slot_config import slot_max_weight, service, slot_set, action_set


# from other.gen_goalset import service,slot_set,action_set  #用这种方法的时候注释掉48.49行
class Agent(object):
    """
    Basic class of agent.
    """

    def __init__(self, parameter):
        self.slot_set = slot_set
        self.action_set = action_set
        self.parameter = parameter
        self.action_space = self._build_action_space()
        self.agent_action = {
            "turn": 1,
            "speaker": "agent",
            "action": None,
            "request_slots": {},
            "inform_slots": {}
        }

    def initialize(self):
        """
        Initializing an dialogue session.
        :return: nothing to return.
        """
        self.agent_action = {
            "turn": None,
            "speaker": "agent",
            "action": None,
            "request_slots": {},
            "inform_slots": {}
        }

    def _build_action_space(self):
        feasible_actions = [
            {'speaker': 'agent', 'action': dialogue_configuration.CLOSE_DIALOGUE, 'inform_slots': {},
             'request_slots': {}},
            {'speaker': 'agent', 'action': dialogue_configuration.THANKS, 'inform_slots': {}, 'request_slots': {}}
        ]
        #   Adding the inform actions and request actions.
        for slot in sorted(slot_max_weight.keys()):
            feasible_actions.append({'speaker': 'agent', 'action': 'request', 'inform_slots': {},
                                     'request_slots': {slot: dialogue_configuration.VALUE_UNKNOWN}})
        # Services as actions.
        for slot in service:
            feasible_actions.append(
                {'speaker': 'agent', 'action': 'inform', 'inform_slots': {"service": slot}, 'request_slots': {}})

        return feasible_actions

    def next(self, state, turn, greedy_strategy):
        """
        Taking action based on different methods, e.g., DQN-based AgentDQN, rule-based AgentRule.
        Detail codes will be implemented in different sub-class of this class.
        :param state: a vector, the representation of current dialogue state.
        :param turn: int, the time step of current dialogue session.
        :param train_mode: int, 1:for training, 0:for evaluation
        :return: a tuple consists of the selected agent action and action index.
        """
        return self.agent_action

    def train(self, batch):
        """
        Training the agent.
        Detail codes will be implemented in different sub-class of this class.
        :param batch: the sample used to training.
        :return:
        """
        pass

    def state_to_representation_last(self, state):
        current_slots = copy.deepcopy(state["current_slots"]["inform_slots"])
        current_slots_rep = np.zeros(len(slot_set.keys()))
        for slot in current_slots.keys():
            # 用权重
            # current_slots_rep[self.slot_set[slot]] =current_slots[slot]
            if current_slots[slot] == True:
                current_slots_rep[self.slot_set[slot]] = 1.0
            elif current_slots[slot] == False:
                current_slots_rep[self.slot_set[slot]] = -1.0
        turn_rep = np.zeros(self.parameter["max_turn"])
        turn_rep[state["turn"]] = 1.0
        user_action_rep = np.zeros(len(self.action_set))
        user_action_rep[self.action_set[state["user_action"]["action"]]] = 1.0
        user_inform_slots = copy.deepcopy(state["user_action"]["inform_slots"])
        user_inform_slots.update(state["user_action"]["explicit_inform_slots"])
        user_inform_slots.update(state["user_action"]["implicit_inform_slots"])
        if "service" in user_inform_slots: user_inform_slots.pop("service")
        user_inform_slots_rep = np.zeros(len(self.slot_set.keys()))
        for slot in user_inform_slots.keys():
            # user_inform_slots_rep[self.slot_set[slot]] = user_inform_slots[slot]
            if user_inform_slots[slot] == True:
                user_inform_slots_rep[self.slot_set[slot]] = 1.0
            elif user_inform_slots[slot] == False:
                user_inform_slots_rep[self.slot_set[slot]] = -1.0
        user_request_slots = copy.deepcopy(state["user_action"]["request_slots"])
        user_request_slots_rep = np.zeros(len(self.slot_set.keys()))
        for slot in user_request_slots.keys():
            user_request_slots_rep[self.slot_set[slot]] = 1.0
        agent_action_rep = np.zeros(len(self.action_set))
        try:
            agent_action_rep[self.action_set[state["agent_action"]["action"]]] = 1.0
        except:
            pass
        agent_inform_slots_rep = np.zeros(len(self.slot_set.keys()))
        try:
            agent_inform_slots = copy.deepcopy(state["agent_action"]["inform_slots"])
            for slot in agent_inform_slots.keys():
                agent_inform_slots_rep[self.slot_set[slot]] = 1.0
        except:
            pass
        agent_request_slots_rep = np.zeros(len(self.slot_set.keys()))
        try:
            agent_request_slots = copy.deepcopy(state["agent_action"]["request_slots"])
            for slot in agent_request_slots.keys():
                agent_request_slots_rep[self.slot_set[slot]] = 1.0
        except:
            pass
        state_rep = np.hstack((current_slots_rep, user_action_rep, user_inform_slots_rep,
                               user_request_slots_rep, agent_action_rep, agent_inform_slots_rep,
                               agent_request_slots_rep, turn_rep))
        return state_rep
