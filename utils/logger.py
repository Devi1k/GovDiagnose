import logging
import os
import re
from logging.handlers import TimedRotatingFileHandler
from time import strftime, gmtime


class Logger:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_path = os.getcwd() + '/log/diagnose'
        self.log_fmt = '%(asctime)s - File \"%(filename)s\" - line %(lineno)s - %(levelname)s - %(message)s'
        self.formatter = logging.Formatter(self.log_fmt)
        self.logger = logging.getLogger()

    def getLogger(self):
        self.logger.suffix = "%Y-%m-%d_%H-%M.log"
        self.logger.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}.log$")
        self.logger.setLevel(logging.INFO)
        log_file_handler = TimedRotatingFileHandler(filename=self.log_path, when="D", interval=1, backupCount=7)
        log_file_handler.setFormatter(self.formatter)
        log_file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(log_file_handler)
        return self.logger


def clean_log(logger):
    path = 'log/'
    timestamp = strftime("%Y%m%d%H%M%S", gmtime())
    today_m = int(timestamp[4:6])  # 今天的月份
    today_y = int(timestamp[0:4])  # 今天的年份
    logger.info('clean log')
    for i in os.listdir(path):
        if len(i) < 9:
            continue
        file_path = path + i  # 生成日志文件的路径
        file_m = int(i[14:16])  # 日志的月份
        file_y = int(i[9:13])  # 日志的年份
        # 对上个月的日志进行清理，即删除。
        # print(file_path)
        if file_m < today_m:
            if os.path.exists(file_path):  # 判断生成的路径对不对，防止报错
                os.remove(file_path)  # 删除文件
        elif file_y < today_y:
            if os.path.exists(file_path):
                os.remove(file_path)
