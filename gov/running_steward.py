# -*-coding: utf-8 -*-
import json

from gov.user import User
from gov.agent_rule import AgentRule
from gov.dialogue_manager import DialogueManager


def simulation_epoch(pipe, parameter, model, train_mode=1):
    in_pipe, out_pipe = pipe
    user = User(parameter=parameter)
    agent = AgentRule(parameter=parameter)
    dialogue_manager = DialogueManager(user=user, agent=agent, parameter=parameter)
    dialogue_manager.set_agent(agent=agent)

    episode_over = False
    receive = in_pipe.recv()
    # todo:
    explicit = receive['text']

    agent_action = dialogue_manager.initialize(explicit, model, train_mode=parameter.get("train_mode"),
                                               greedy_strategy=1)

    if agent_action['action'] == 'inform':
        msg = {"service": agent_action["inform_slots"]["service"],
               "end_flag": episode_over}
        out_pipe.send(msg)
    elif agent_action['action'] == 'request':
        send_list = list(agent_action["request_slots"].keys())
        service = ''.join(send_list)
        msg = {"service": service, "end_flag": episode_over}
        out_pipe.send(msg)

    while episode_over is False:
        try:
            receive = in_pipe.recv()
        except EOFError:
            break
        # todo:
        judge = receive['judge']
        implicit = receive['text']

        if agent_action['action'] == 'inform' and judge is True:
            # out_pipe.send("请问还有别的问题吗")
            episode_over = True
            msg = {"service": agent_action["inform_slots"]["service"],
                   "end_flag": episode_over}
            out_pipe.send(msg)
            break
        if judge is True:
            with open('./data/goal_set.json', 'r') as f:
                goal_set = json.load(f)
                goal_set['user_action']['user_judge'] = True
            with open('./data/goal_set.json', 'w') as f:
                json.dump(goal_set, f)
        else:
            with open('./data/goal_set.json', 'r') as f:
                goal_set = json.load(f)
                goal_set['user_action']['user_judge'] = False
            with open('./data/goal_set.json', 'w') as f:
                json.dump(goal_set, f)

        reward, episode_over, dialogue_status, _agent_action = dialogue_manager.next(implicit, model,
                                                                                     save_record=True,
                                                                                     train_mode=train_mode,
                                                                                     greedy_strategy=1,
                                                                                     agent_action=agent_action)

        if agent_action['action'] == 'inform':
            msg = {"service": agent_action["inform_slots"]["service"],
                   "end_flag": episode_over}
            out_pipe.send(msg)
        elif agent_action['action'] == 'request':
            send_list = list(agent_action["request_slots"].keys())
            service = ''.join(send_list)
            msg = {"service": service,  "end_flag": episode_over}
            out_pipe.send(msg)

        agent_action = _agent_action
    in_pipe.close()
    out_pipe.close()
