#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time    : 2022/4/24 2:44 PM
# @Author  : jiefei.liu
# @Software: PyCharm
# @Description：
"""
import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from utils.logger import clean_log


def run_diagnose():
    print("清除多余进程")
    os.system("ps -ef | grep gov_service_test.py | grep -v grep | awk \'{print \"kill -9 \"$2}\' | sh")
    print("执行诊断")
    os.system("nohup python3 gov_service_test.py > /dev/null 2>&1 &")


def run_regression():
    # 程序启动时先跑一次
    print("定时任务已经启动...The time is: %s" % datetime.now())
    run_diagnose()
    # 设置每天定时启动的时间，当前每天3：00自动重启
    task_hour = 3
    task_minute = 00
    scheduler = BlockingScheduler()
    scheduler.add_job(clean_log, 'cron', hour=task_hour, minute=task_minute, args=[])
    scheduler.add_job(run_diagnose, 'cron', hour=task_hour, minute=task_minute, args=[])
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    run_regression()
