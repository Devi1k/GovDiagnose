# -*- coding:utf-8 -*-

import argparse
import pickle
import sys, os
import json

from agent_rule import AgentRule
from running_steward import RunningSteward
from conf.config import get_config

config_file = './conf/settings.yaml'
parameter = get_config(config_file)
print(json.dumps(parameter, indent=2))


def run():
    steward = RunningSteward(parameter=parameter)

    warm_start = parameter.get("warm_start")
    warm_start_epoch_number = parameter.get("warm_start_epoch_number")
    train_mode = parameter.get("train_mode")

    # Warm start.
    if warm_start == 1 and train_mode == 1:
        print("warm starting...")
        agent = AgentRule(parameter=parameter)
        steward.warm_start(agent=agent, epoch_number=warm_start_epoch_number)


if __name__ == "__main__":
    run()
