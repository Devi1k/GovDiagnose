# GovDiagnose

```shell
nohup python3 run_service.py > service.out 2>&1 &
```

1. 将wb.text.model开头的三个文件放到data文件夹下

pipe_dict中的参数

0. send_pipe 主进程端
1. receive_pipe 子进程端
2. first_utterance 首句话
3. process 对应子进程
4. single_finish 单一对话结束状态
5. all_finish 整体对话结束状态
6. is_first 是否是第一句话
7. service_name 当前对话事项名称