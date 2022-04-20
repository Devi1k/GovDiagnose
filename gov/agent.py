# -*- coding: utf-8 -*-
import copy

import gov.dialogue_configuration as dialogue_configuration
from gov.slot_config import requirement_weight, service, slot_max
from gov.slot_config import slot_max_weight


class Agent(object):
    def __init__(self, parameter):
        self.slot_max_weight = slot_max_weight
        self.service = service
        self.parameter = parameter
        self.action_space = self._build_action_space()
        self.agent_action = {
            "turn": 1,
            "action": None,
            "speaker": "agent",
            "request_slots": {},
            "inform_slots": {}
        }

    def initialize(self):
        self.agent_action = {
            "turn": None,
            "action": None,
            "speaker": "agent",
            "request_slots": {},
            "inform_slots": {}
        }
        self.requirement_weight = copy.deepcopy(requirement_weight)
        self.service = copy.deepcopy(service)
        self.slot_max = copy.deepcopy(slot_max)

    def _build_action_space(self):  # warm_start没用到，dqn部分用
        feasible_actions = [
            {'action': dialogue_configuration.CLOSE_DIALOGUE, 'inform_slots': {}, 'request_slots': {}},
            {'action': dialogue_configuration.THANKS, 'inform_slots': {}, 'request_slots': {}}
        ]
        #   Adding the inform actions and request actions.
        for slot in sorted(self.slot_max_weight.keys()):
            feasible_actions.append({'action': 'request', 'inform_slots': {},
                                     'request_slots': {slot: dialogue_configuration.VALUE_UNKNOWN}})
        # Services as actions.
        for slot in self.service:
            feasible_actions.append({'action': 'inform', 'inform_slots': {"service": slot}, 'request_slots': {}})

        return feasible_actions
