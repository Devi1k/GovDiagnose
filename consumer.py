import json

from multiprocessing import Process, Pipe
from gov.running_steward import simulation_epoch
from conf.config import get_config
import gensim

if __name__ == '__main__':
    model = gensim.models.Word2Vec.load('data/wb.text.model')
    config_file = './conf/settings.yaml'
    parameter = get_config(config_file)
    # print(json.dumps(parameter, indent=2))
    out_pipe, in_pipe = Pipe()  # 建立管道，拿到管道的两端，双工通信方式，两端都可以收发消息
    p = Process(target=simulation_epoch, args=(out_pipe, in_pipe, parameter, model,))  # 将管道的一端给子进程
    p.start()  # 开启子进程
    out_pipe.close()
    while True:
        try:
            label = input("判断是否正确：正确t错误f")  # 若第一次输入 直接回车
            more = input("请输入描述：")  # 若正确不需要补充描述 直接回车
            in_pipe.send([label, more])  # 主进程给子进程发送消息
            recv_list = in_pipe.recv()
            recv = ''.join(recv_list)
            print("来自agent的消息:", recv)
        except EOFError:
            break

    in_pipe.close()
